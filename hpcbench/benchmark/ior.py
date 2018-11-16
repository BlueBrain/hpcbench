"""HPCBench benchmark driver for IOR

    https://github.com/LLNL/ior
"""
import itertools
import logging
import os
import os.path as osp
import re
import shlex
import shutil

from cached_property import cached_property
import six

from hpcbench.api import Benchmark, Metric, MetricsExtractor
from hpcbench.toolbox.functools_ext import listify
from hpcbench.toolbox.process import find_executable


LOGGER = logging.getLogger('ior')


class IORMetricsExtractor(MetricsExtractor):
    """Parser for IOR outputs
    """

    RE_MULTIPLE_SPACES = re.compile('\\s+')
    OPERATIONS = set(['write', 'read'])
    METAS = {
        '#Tasks': {'name': 'tasks', 'metric': Metric(unit='', type=int)},
        'Max(MiB)': {'name': 'max', 'metric': Metric(unit='Mib', type=float)},
        'Mean(MiB)': {'name': 'mean', 'metric': Metric(unit='MiB', type=float)},
        'Mean(s)': {'name': 'mean_time', 'metric': Metric(unit='s', type=float)},
        'Min(MiB)': {'name': 'min', 'metric': Metric(unit='MiB', type=float)},
        'Min(OPs)': {'name': 'min_ops', 'metric': Metric(unit='', type=float)},
        'Max(OPs)': {'name': 'max_ops', 'metric': Metric(unit='', type=float)},
        'Mean(OPs)': {'name': 'mean_ops', 'metric': Metric(unit='', type=float)},
        'StdDev': {'name': 'std_dev', 'metric': Metric(unit='', type=float)},
        'aggsize': {'name': 'agg_size', 'metric': Metric(unit='?', type=int)},
        'blksiz': {'name': 'block_size', 'metric': Metric(unit='B', type=int)},
        'fPP': {'name': 'file_per_proc', 'metric': Metric(unit='', type=int)},
        'reord': {'name': 'reorder_tasks', 'metric': Metric(unit='', type=bool)},
        'reordoff': {
            'name': 'task_per_node_offset',
            'metric': Metric(unit='', type=int),
        },
        'reordrand': {
            'name': 'reorder_tasks_random',
            'metric': Metric(unit='', type=bool),
        },
        'reps': {'name': 'repetitions', 'metric': Metric(unit='', type=int)},
        'seed': {
            'name': 'reorder_tasks_random_seed',
            'metric': Metric(unit='', type=int),
        },
        'segcnt': {'name': 'segments', 'metric': Metric(unit='', type=int)},
        'tPN': {'name': 'tasks_per_node', 'metric': Metric(unit='', type=int)},
        'xsize': {'name': 'transfer_size', 'metric': Metric(unit='B', type=int)},
    }

    METAS_IGNORED = set(['API', 'Operation', 'RefNum', 'Test#'])

    SUMMARY_HEADER = 'Summary of all tests:'
    RESULTS_HEADER_START = 'Operation'

    @property
    def check_metrics(self):
        return False

    @cached_property
    def metrics(self):
        metrics = {}
        for operation in IORMetricsExtractor.OPERATIONS:
            for meta, desc in IORMetricsExtractor.METAS.items():
                name = IORMetricsExtractor.get_meta_name(
                    operation, desc.get('name') or meta
                )
                metrics[name] = desc['metric']
        return metrics

    def extract_metrics(self, metas):
        columns = None
        metrics = {}
        with open(self.stdout) as istr:
            IORMetricsExtractor._skip_output_header(istr)
            for line in istr:
                line = line.strip()
                if line.startswith(IORMetricsExtractor.RESULTS_HEADER_START):
                    columns = IORMetricsExtractor.parse_results_header(line)
                elif line == '':
                    # end of results
                    break
                else:
                    IORMetricsExtractor.parse_result_line(columns, line, metrics)
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
        header = IORMetricsExtractor.RE_MULTIPLE_SPACES.sub(' ', header)
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
        line = IORMetricsExtractor.RE_MULTIPLE_SPACES.sub(' ', line)
        line = line.split(' ')
        operation = line[0]
        assert len(line) == len(columns)
        for i, col in enumerate(line):
            col = columns[i]
            if col in cls.METAS_IGNORED:
                continue
            desc = cls.METAS.get(col)
            if desc is None:
                LOGGER.warn('Unrecognized column: %s', col)
            meta = cls.get_meta_name(operation, desc.get('name') or col)
            value = desc['metric'].type(line[i])
            metrics[meta] = value


class IOR(Benchmark):
    """Parallel filesystem I/O benchmark"""

    name = "ior"

    APIS = ['POSIX', 'MPIIO', 'HDF5']
    DEFAULT_BLOCK_SIZE = "1G"
    DEFAULT_CLEAN_PATH = True
    DEFAULT_EXECUTABLE = 'ior'
    DEFAULT_FILE_MODE = 'fpp'
    DEFAULT_OPTIONS = []
    DEFAULT_REPETITIONS = 3
    DEFAULT_SRUN_NODES = 1
    DEFAULT_TRANSFER_SIZE = "32M"
    DEFAULT_API_FILE_MODE_OPTIONS = dict(
        MPIIO=dict(onefile=['-c'], fpp=['-F']),
        POSIX=dict(fpp=['-F']),
        HDF5=dict(fpp=['-F']),
    )

    def __init__(self):
        super(IOR, self).__init__(
            attributes=dict(
                api_file_mode_options=IOR.DEFAULT_API_FILE_MODE_OPTIONS,
                apis=IOR.APIS,
                block_size=IOR.DEFAULT_BLOCK_SIZE,
                clean_path=IOR.DEFAULT_CLEAN_PATH,
                executable=IOR.DEFAULT_EXECUTABLE,
                file_mode=IOR.DEFAULT_FILE_MODE,
                options=IOR.DEFAULT_OPTIONS,
                path=None,
                repetitions=IOR.DEFAULT_REPETITIONS,
                sizes=None,
                srun_nodes=0,
                transfer_size=IOR.DEFAULT_TRANSFER_SIZE,
            )
        )

    @cached_property
    def executable(self):
        """Get path to ior executable
        """
        return self.attributes['executable']

    @cached_property
    def clean_path(self):
        """Remove test directory if present before executing IOR
        """
        return self.attributes['clean_path']

    @cached_property
    def repetitions(self):
        """number of repetitions of test (-i)"""
        return str(self.attributes['repetitions'])

    @cached_property
    def path(self):
        """Overwrite execution path. Parameter expansion
        with Python formatting supports:
        api, file_mode, block_size, transfer_size, and
        benchmark (name in YAML)
        """
        return self.attributes['path']

    @cached_property
    def _fspath(self):
        """Path on the filesystem, without prefix protocol if any"""
        if self.path:
            return self.path.split('://', 1)[-1]

    @property
    def apis(self):
        """List of API to test"""
        value = self.attributes['apis']
        if isinstance(value, six.string_types):
            value = shlex.split(value)
        return value

    def pre_execute(self, execution, context):
        """Make sure the named directory is created if possible"""
        path = self._fspath
        if path:
            path = path.format(
                benchmark=context.benchmark,
                api=execution['category'],
                **execution.get('metas', {})
            )
            if self.clean_path:
                shutil.rmtree(path, ignore_errors=True)
            if execution['metas']['file_mode'] == 'onefile':
                path = osp.dirname(path)
            if not osp.exists(path):
                os.makedirs(path)

    @property
    def sizes(self):
        """Provides block_size and transfer_size through a list
        of dict, for instance: [{'transfer': '1M 4M', 'block': '8M'}]
        """
        if self.attributes.get('sizes'):
            for settings in self.attributes.get('sizes'):
                for pair in itertools.product(
                    shlex.split(settings['block']), shlex.split(settings['transfer'])
                ):
                    yield pair
        else:
            for pair in itertools.product(self.block_size, self.transfer_size):
                yield pair

    @listify
    def execution_matrix(self, context):
        # FIXME: Design the real set of commands to execute
        apis = self.attributes['apis']
        if not isinstance(apis, list):
            apis = apis.split()
        for api in set(apis) & set(IOR.APIS):
            for fm in self.file_mode:
                for bs, ts in self.sizes:
                    for cmd in self._execution_matrix(context, api, fm, bs, ts):
                        yield cmd

    def _expand_path(self, **kwargs):
        path = self.path.format(**kwargs)
        if kwargs['api'] == 'POSIX':
            if path and path.startswith('ime') and '/ime/' in path:
                path = path[path.find('/ime/') :]
        return path

    def _execution_matrix(self, context, api, file_mode, block_size, transfer_size):
        options = self.options
        cmd = dict(
            category=api,
            command=[
                find_executable(self.executable, required=False),
                '-a',
                api,
                '-b',
                block_size,
                '-t',
                transfer_size,
                '-i',
                self.repetitions,
            ]
            + options
            + self._context_options(context, api, file_mode, block_size, transfer_size),
            metas=dict(
                block_size=block_size, file_mode=file_mode, transfer_size=transfer_size
            ),
            srun_nodes=self.srun_nodes,
        )
        yield cmd

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
    def file_mode(self):
        """onefile, fpp, or both"""
        fms = self.attributes['file_mode']
        eax = set()
        if isinstance(fms, six.string_types):
            fms = shlex.split(fms)
        for fm in fms:
            if fm == 'both':
                eax.add('fpp')
                eax.add('onefile')
            elif fm in ['fpp', 'onefile']:
                eax.add(fm)
            else:
                raise Exception('Invalid IOR file mode: ' + fm)
        return eax

    @property
    def block_size(self):
        """Contiguous bytes to write per task (e.g.: 8, 4k, 2m, 1g)
        """
        bs = self.attributes['block_size']
        if isinstance(bs, six.string_types):
            bs = shlex.split(bs)
        bs = [str(e) for e in bs]
        return bs

    @property
    def transfer_size(self):
        """Size of transfer in bytes (e.g.: 8, 4k, 2m, 1g)"""
        ts = self.attributes['transfer_size']
        if isinstance(ts, six.string_types):
            ts = shlex.split(ts)
        ts = [str(e) for e in ts]
        return ts

    @property
    def srun_nodes(self):
        """Number of nodes the command must be executed on
        """
        return self.attributes['srun_nodes']

    @cached_property
    def metrics_extractors(self):
        # Use same extractor for all categories of commands
        return IORMetricsExtractor()

    @cached_property
    def api_file_mode_options(self):
        """Additional options according to
        API and file mode settings"""
        return self.attributes['api_file_mode_options']

    def _context_options(self, context, api, file_mode, block_size, transfer_size):
        eax = []
        if self.path:
            path = self._expand_path(
                api=api,
                file_mode=file_mode,
                block_size=block_size,
                transfer_size=transfer_size,
                benchmark=context.benchmark,
            )
            if file_mode == 'fpp':
                path = osp.join(path, 'data')
            eax += ['-o', path]
        api_opts = self.api_file_mode_options.get(api, {})
        eax += api_opts.get(file_mode, [])
        return eax
