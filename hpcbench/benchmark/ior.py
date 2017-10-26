"""HPCBench benchmark driver for IOR

    https://github.com/LLNL/ior
"""
import re
import shlex

from cached_property import cached_property
import six

from hpcbench.api import (
    Benchmark,
    Metric,
    MetricsExtractor,
)
from hpcbench.toolbox.functools_ext import listify
from hpcbench.toolbox.process import find_executable


class Extractor(MetricsExtractor):
    """Parser for IOR outputs
    """
    RE_MULTIPLE_SPACES = re.compile('\\s+')
    OPERATIONS = set(['write', 'read'])
    METAS = {
        '#Tasks': {
            'name': 'tasks',
            'metric': Metric(unit='', type=int)
        },
        'Max(MiB)': {
            'name': 'max',
            'metric': Metric(unit='Mib', type=float)
        },
        'Mean(MiB)': {
            'name': 'mean',
            'metric': Metric(unit='MiB', type=float)
        },
        'Mean(s)': {
            'name': 'mean_time',
            'metric': Metric(unit='s', type=float)
        },
        'Min(MiB)': {
            'name': 'min',
            'metric': Metric(unit='MiB', type=float)
        },
        'StdDev': {
            'name': 'std_dev',
            'metric': Metric(unit='', type=float)
        },
        'aggsize': {
            'name': 'agg_size',
            'metric': Metric(unit='?', type=int)
        },
        'blksiz': {
            'name': 'block_size',
            'metric': Metric(unit='B', type=int)
        },
        'fPP': {
            'name': 'file_per_proc',
            'metric': Metric(unit='', type=int)
        },
        'reord': {
            'name': 'reorder_tasks',
            'metric': Metric(unit='', type=bool)
        },
        'reordoff': {
            'name': 'task_per_node_offset',
            'metric': Metric(unit='', type=int)
        },
        'reordrand': {
            'name': 'reorder_tasks_random',
            'metric': Metric(unit='', type=bool)
        },
        'reps': {
            'name': 'repetitions',
            'metric': Metric(unit='', type=int)
        },
        'seed': {
            'name': 'reorder_tasks_random_seed',
            'metric': Metric(unit='', type=int)
        },
        'segcnt': {
            'name': 'segments',
            'metric': Metric(unit='', type=int)
        },
        'tPN': {
            'name': 'tasks_per_node',
            'metric': Metric(unit='', type=int)
        },
        'xsize': {
            'name': 'transfer_size',
            'metric': Metric(unit='B', type=int)}
    }

    METAS_IGNORED = set([
        'API', 'Operation', 'RefNum', 'Test#',
    ])

    SUMMARY_HEADER = 'Summary of all tests:'
    RESULTS_HEADER_START = 'Operation'

    @cached_property
    def metrics(self):
        metrics = {}
        for operation in Extractor.OPERATIONS:
            for meta, desc in Extractor.METAS.items():
                name = Extractor.get_meta_name(operation,
                                               desc.get('name') or meta)
                metrics[name] = desc['metric']
        return metrics

    def extract_metrics(self, outdir, metas):
        columns = None
        metrics = {}
        with open(self.stdout(outdir)) as istr:
            Extractor._skip_output_header(istr)
            for line in istr:
                line = line.strip()
                if line.startswith(Extractor.RESULTS_HEADER_START):
                    columns = Extractor.parse_results_header(line)
                elif line == '':
                    # end of results
                    break
                else:
                    Extractor.parse_result_line(columns, line, metrics)
        return metrics

    @classmethod
    def _skip_output_header(cls, istr):
        for line in istr:
            line = line.strip()
            if line == cls.SUMMARY_HEADER:
                return

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
            value = desc['metric'].type(line[i])
            metrics[meta] = value


class IOR(Benchmark):
    """Driver for IOR benchmark"""
    name = "ior"

    description = "Parallel filesystem I/O benchmark"

    APIS = ['POSIX', 'MPIIO', 'HDF5']
    DEFAULT_BLOCK_SIZE = "1G"
    DEFAULT_EXECUTABLE = 'ior'
    DEFAULT_SRUN_NODES = 1
    DEFAULT_OPTIONS = []

    def __init__(self):
        super(IOR, self).__init__(
            attributes=dict(
                apis=IOR.APIS,
                block_size=IOR.DEFAULT_BLOCK_SIZE,
                srun_nodes=IOR.DEFAULT_SRUN_NODES,
                executable=IOR.DEFAULT_EXECUTABLE,
                options=IOR.DEFAULT_OPTIONS,
            )
        )

    @cached_property
    def executable(self):
        """Get path to iperf executable
        """
        return self.attributes['executable']

    @property
    def apis(self):
        """List of API to test"""
        return self.attributes['apis']

    @listify
    def execution_matrix(self, context):
        del context  # unused
        # FIXME: Design the real set of commands to execute
        for api in set(self.attributes['apis']) & set(IOR.APIS):
            for command in self._execution_matrix(api):
                yield command

    def _execution_matrix(self, api):
        yield dict(
            category=api,
            command=[
                find_executable(self.executable),
                '-a', api,
                '-b', str(self.block_size),
            ] + self.options,
            metas=dict(
                api=api,
                block_size=self.block_size
            ),
            srun_nodes=self.srun_nodes
        )

    @property
    def options(self):
        """Additional options appended to the ior command
        type: either string or a list of string
        """
        options = self.attributes['options']
        if isinstance(options, six.string_types):
            options = shlex.split(options)
        options = [str(e) for e in options]
        return options

    @property
    def block_size(self):
        return self.attributes['block_size']

    @property
    def srun_nodes(self):
        """Number of nodes the command must be executed on
        """
        return self.attributes['srun_nodes']

    @cached_property
    def metrics_extractors(self):
        # Use same extractor for all categories of commands
        return Extractor()
