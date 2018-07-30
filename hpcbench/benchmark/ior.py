"""HPCBench benchmark driver for IOR

    https://github.com/LLNL/ior
"""
import itertools
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
                apis=IOR.APIS,
                block_size=IOR.DEFAULT_BLOCK_SIZE,
                executable=IOR.DEFAULT_EXECUTABLE,
                file_mode=IOR.DEFAULT_FILE_MODE,
                options=IOR.DEFAULT_OPTIONS,
                path=None,
                srun_nodes=0,
                transfer_size=IOR.DEFAULT_TRANSFER_SIZE,
                clean_path=IOR.DEFAULT_CLEAN_PATH,
                repetitions=IOR.DEFAULT_REPETITIONS,
                api_file_mode_options=IOR.DEFAULT_API_FILE_MODE_OPTIONS,
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
        return str(self.attributes['repetitions'])

    @cached_property
    def path(self):
        """Overwrite execution path
        """
        return self.attributes['path']

    @cached_property
    def _fspath(self):
        """Path on the filesystem, without prefix protocol if any"""
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
        del execution  # not used
        del context  # not used
        if self._fspath:
            if self.clean_path:
                shutil.rmtree(self._fspath, ignore_errors=True)
            if not osp.exists(self._fspath):
                os.makedirs(self._fspath)
            else:
                if not osp.isdir(osp.realpath(self._fspath)):
                    raise IOError

    @listify
    def execution_matrix(self, context):
        del context  # unused
        # FIXME: Design the real set of commands to execute
        for api in set(self.attributes['apis']) & set(IOR.APIS):
            for fm, bs, ts in itertools.product(
                self.file_mode, self.block_size, self.transfer_size
            ):
                for command in self._execution_matrix(api, fm, bs, ts):
                    yield command

    def _execution_matrix(self, api, file_mode, block_size, transfer_size):
        options = self.options
        cmd = dict(
            category=api,
            command=[
                find_executable(self.executable, required=False),
                '-a',
                api,
                file_mode,
                '-b',
                block_size,
                '-t',
                transfer_size,
                '-i',
                self.repetitions,
            ]
            + options
            + self._context_options(api, file_mode),
            metas=dict(api=api, block_size=block_size, transfer_size=transfer_size),
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
        bs = self.attributes['block_size']
        if isinstance(bs, six.string_types):
            bs = shlex.split(bs)
        bs = [str(e) for e in bs]
        return bs

    @property
    def transfer_size(self):
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

    def _context_options(self, api, file_mode):
        eax = []
        if self.path:
            eax += ['-o', osp.join(self.path, 'data')]
        api_opts = self.api_file_mode_options.get(api, {})
        eax += api_opts.get(file_mode, [])
        return eax
