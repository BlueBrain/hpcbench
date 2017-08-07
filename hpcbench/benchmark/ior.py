"""HPCBench benchmark driver for IOR

    https://github.com/LLNL/ior
"""
import re

from cached_property import cached_property

from hpcbench.api import (
    Benchmark,
    MetricsExtractor,
)
from hpcbench.toolbox.functools_ext import listify


class Extractor(MetricsExtractor):
    """Parser for IOR outputs
    """
    RE_MULTIPLE_SPACES = re.compile('\\s+')
    OPERATIONS = set(['write', 'read'])
    METAS = {
        'Max(MiB)': dict(
            name='max',
            type=float,
            unit='Mib',
        ),
        'Min(MiB)': dict(
            name='min',
            type=float,
            unit='MiB',
        ),
        'Mean(MiB)': dict(
            name='mean',
            type=float,
            unit='MiB',
        ),
        'StdDev': dict(
            name='std_dev',
            type=float,
        ),
        'Mean(s)': dict(
            name='mean_time',
            type=float,
            unit='s',
        ),
        '#Tasks': dict(
            name='tasks',
            type=int,
        ),
        'tPN': dict(
            name='tasks_per_node',
            type=int,
        ),
        'reps': dict(
            name='repetitions',
            type=int,
        ),
        'fPP': dict(
            name='file_per_proc',
            type=int,
        ),
        'reord': dict(
            name='reorder_tasks',
            type=bool,
        ),
        'reordoff': dict(
            name='task_per_node_offset',
            type=int,
        ),
        'reordrand': dict(
            name='reorder_tasks_random',
            type=bool,
        ),
        'seed': dict(
            name='reorder_tasks_random_seed',
            type=int,
        ),
        'segcnt': dict(
            name='segments',
            type=int,
        ),
        'blksiz': dict(
            name='block_size',
            type=int,
            unit='B',
        ),
        'xsize': dict(
            name='transfer_size',
            type=int,
            unit='B',
        ),
        'aggsize': dict(
            name='agg_size',
            type=int,
            unit='?',
        ),
    }

    METAS_IGNORED = set([
        'API', 'Operation', 'RefNum', 'Test#',
    ])

    SUMMARY_HEADER = 'Summary of all tests:'
    RESULTS_HEADER_START = 'Operation'

    def metrics(self):
        metrics = {}
        for operation in Extractor.OPERATIONS:
            for meta, desc in Extractor.METAS.items():
                name = Extractor.get_meta_name(operation,
                                               desc.get('name') or meta)
                metrics[name] = dict(
                    (k, v) for k, v in desc.items()
                    if k != 'name'
                )
        return metrics

    def extract(self, outdir, metas):
        columns = None
        metrics = {}
        with open(self.stdout(outdir)) as istr:
            awaits_summary = True
            for line in istr:
                line = line.strip()
                if awaits_summary:
                    if line == Extractor.SUMMARY_HEADER:
                        awaits_summary = False
                else:
                    if line.startswith(Extractor.RESULTS_HEADER_START):
                        columns = Extractor.parse_results_header(line)
                    elif line == '':
                        # end of results
                        break
                    else:
                        Extractor.parse_result_line(columns, line, metrics)
        return metrics

    @classmethod
    def get_meta_name(cls, operation, suffix):
        """Get metric name from an operation (write, read, ...) and a suffix
        (std_dev, block_size, ...)
        :return: meta name
        :rtype: string
        """
        return operation + '_' + suffix

    @classmethod
    def parse_results_header(cls, header):
        """Extract columns from the line under "Summary of all tests:"

        :param header: content of the results header line
        :return: list of string providing columns
        """
        header = Extractor.RE_MULTIPLE_SPACES.sub(' ', header)
        header = header.split(' ')
        return header

    @classmethod
    def parse_result_line(cls, columns, line, metrics):
        """Extract metrics from a result line
        :param columns: list of columns specified under line
        "Summary of all tests:"
        :param line: string of results below the columns line
        :param metrics: output dict where metrics are written
        """
        line = Extractor.RE_MULTIPLE_SPACES.sub(' ', line)
        line = line.split(' ')
        operation = line[0]
        assert len(line) == len(columns)
        for i, col in enumerate(line):
            col = columns[i]
            if col in cls.METAS_IGNORED:
                continue
            desc = cls.METAS.get(col)
            if desc is None:
                raise Exception('Unrecognized column: %s' % col)
            meta = cls.get_meta_name(operation, desc.get('name') or col)
            value = desc['type'](line[i])
            metrics[meta] = value


class IOR(Benchmark):
    """Driver for IOR benchmark"""
    name = "ior"

    description = "Parallel filesystem I/O benchmark"

    APIS = ['POSIX', 'MPIIO', 'HDF5']
    NODES = [1, 4, 8]
    PROCESSORS = [[1, 4], [4, 16], [8, 32]]
    BLOCK_SIZES = ['1M', '10M', '100M']

    def __init__(self):
        super(IOR, self).__init__(
            attributes=dict(
                apis=IOR.APIS,
                block_sizes=IOR.BLOCK_SIZES,
                nodes=IOR.NODES,
                processors=IOR.PROCESSORS,
            )
        )

    @cached_property
    @listify
    def execution_matrix(self):
        # FIXME: Design the real set of commands to execute
        for block_size in self.attributes['block_sizes']:
            for api in set(['POSIX', 'HDF5']) - set(self.attributes['apis']):
                yield dict(
                    category=api,
                    command=[
                        'ior',
                        '-a', api,
                        '-b', str(block_size),
                    ],
                    metas=dict(
                        api=api,
                        block_size=block_size
                    )
                )

            for i, nodes in enumerate(self.attributes['nodes']):
                for processors in self.attributes['processors'][i]:
                    yield dict(
                        category='MPIIO',
                        command=[
                            'srun',
                            '-n', str(nodes),
                            '-N', str(processors),
                            'ior',
                            '-a', 'MPIIO',
                            '-b', str(block_size),
                        ],
                        metas=dict(
                            api='MPIIO',
                            nodes=nodes,
                            processors=processors,
                            block_size=block_size
                        )
                    )

    @cached_property
    def metrics_extractors(self):
        # Use same extractor for all categories of commands
        return Extractor()
