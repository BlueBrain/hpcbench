"""the High-Performance Linpack Benchmark for Distributed-Memory Computers
    http://www.netlib.org/benchmark/hpl/
"""
import math
import re
import shlex

from cached_property import cached_property
import six

from hpcbench.api import Benchmark, Metric, Metrics, MetricsExtractor
from hpcbench import jinja_environment
from hpcbench.toolbox.process import find_executable


PRECISION_FORMULA = "||Ax-b||_oo/(eps*(||A||_oo*||x||_oo+||b||_oo)*N)"


def get_precision_regex():
    """Build regular expression used to extract precision
    metric from command output"""
    expr = re.escape(PRECISION_FORMULA)
    expr += r'=\s*(\S*)\s.*\s([A-Z]*)'
    return re.compile(expr)


class HPLExtractor(MetricsExtractor):
    """Ignore stdout until this line"""

    STDOUT_IGNORE_PRIOR = (
        "T/V                N    NB"
        "     P     Q               Time                 Gflops"
    )

    REGEX = dict(
        flops=re.compile(
            r'^[\w]+[\s]+([\d]+)[\s]+([\d]+)[\s]+([\d]+)[\s]+'
            r'([\d]+)[\s]+([\d.]+)[\s]+([\d.]+e[+-][\d]+)'
        ),
        precision=get_precision_regex(),
    )

    METRICS = dict(
        size_n=Metrics.Cardinal,
        size_nb=Metrics.Cardinal,
        size_p=Metrics.Cardinal,
        size_q=Metrics.Cardinal,
        time=Metrics.Second,
        flops=Metrics.GFlops,
        validity=Metrics.Bool,
        precision=Metric(unit='', type=float),
    )

    METRICS_NAMES = set(METRICS)

    REGEX_METRICS = dict(
        flops=dict(
            size_n=(int, 1),
            size_nb=(int, 2),
            size_p=(int, 3),
            size_q=(int, 4),
            time=(float, 5),
            flops=(float, 6),
        ),
        precision=dict(precision=(float, 1)),
    )

    @property
    def metrics(self):
        """ The metrics to be extracted.
            This property can not be replaced, but can be mutated as required
        """
        return HPLExtractor.METRICS

    def extract_metrics(self, metas):
        metrics = {}
        # parse stdout and extract desired metrics
        with open(self.stdout) as istr:
            for line in istr:
                if line.strip() == HPLExtractor.STDOUT_IGNORE_PRIOR:
                    break
            for line in istr:
                line = line.strip()
                self._parse_line(line, metrics)

        return metrics

    @classmethod
    def _parse_line(cls, line, metrics):
        for section, regex in cls.REGEX.items():
            search = regex.search(line)
            if search:
                cls._extract_metric(section, search, metrics)
                return

    @classmethod
    def _extract_metric(cls, section, search, metrics):
        for metric, data in cls.REGEX_METRICS[section].items():
            mtype = data[0]
            mfield = data[1]
            mvalue = mtype(search.group(mfield))
            metrics[metric] = mvalue
        if section == 'precision':
            metrics['validity'] = str(search.group(2)) == "PASSED"


class HPL(Benchmark):
    """Provides Intensive FLOPS benchmark.
    """

    DEFAULT_THREADS = 1
    DEFAULT_DEVICE = 'cpu'
    DEFAULT_EXECUTABLE = 'xhpl'
    DEFAULT_NODES = 1
    DEFAULT_CORE_PER_NODE = 36
    DEFAULT_MEMORY_PER_NODE = 128
    DEFAULT_BLOCK_SIZE = 192

    def __init__(self):
        # locate `stream_c` executable
        super(HPL, self).__init__(
            attributes=dict(
                threads=HPL.DEFAULT_THREADS,
                data="",
                executable=HPL.DEFAULT_EXECUTABLE,
                mpirun=[],
                srun_nodes=0,
                options=[],
                nodes=HPL.DEFAULT_NODES,
                cores_per_node=HPL.DEFAULT_CORE_PER_NODE,
                memory_per_node=HPL.DEFAULT_MEMORY_PER_NODE,
                block_size=HPL.DEFAULT_BLOCK_SIZE,
            )
        )

    name = 'hpl'

    @cached_property
    def executable(self):
        """Path to HPL executable
        """
        return self.attributes['executable']

    @property
    def options(self):
        """
        additional options passed to the hpl executable
        """
        options = self.attributes['options'] or []
        if isinstance(options, six.string_types):
            options = shlex.split(options)
        return options

    @property
    def command(self):
        return [find_executable(self.executable, required=False)] + self.options

    def execution_matrix(self, context):
        del context  # unused
        cmd = dict(
            category=HPL.DEFAULT_DEVICE,
            command=self.mpirun + self.command,
            environment=dict(
                OMP_NUM_THREADS=self.threads,
                MKL_NUM_THREADS=self.threads,
                KMP_AFFINITY='scatter',
            ),
        )
        if self.srun_nodes is not None:
            cmd.update(srun_nodes=self.srun_nodes)
        yield cmd

    @property
    def data(self):
        """HPL input file
        HPL.DATA Generator utility available here: https://goo.gl/RKGnrR
        Then the file can specified using the | YAML keyword, for instance:

        data: |
          HPLinpack benchmark input file
            Innovative Computing Laboratory, University of Tennessee
            HPL.out      output file name (if any)
            6            device out (6=stdout,7=stderr,file)
            1            # of problems sizes (N)
            ...
        """
        if self.attributes['data']:
            return self.attributes['data']
        else:
            return self._build_data()

    @property
    def nodes(self):
        """used to build HPL.dat"""
        return self.attributes['nodes']

    @property
    def cores_per_node(self):
        """used to build HPL.dat"""
        return self.attributes['cores_per_node']

    @property
    def memory_per_node(self):
        """used to build HPL.dat"""
        return self.attributes['memory_per_node']

    @property
    def block_size(self):
        """used to build HPL.dat"""
        return self.attributes['block_size']

    def _build_data(self):
        """Build HPL data from basic parameters"""

        def baseN(nodes, mpn):
            return int(math.sqrt(mpn * 0.80 * nodes * 1024 * 1024 / 8))

        def nFromNb(baseN, nb):
            factor = int(baseN / nb)
            if factor % 2 != 0:
                factor -= 1
            return nb * factor

        def get_grid(nodes, ppn):
            cores = nodes * ppn
            sqrt = math.sqrt(cores)
            factors = [
                num for num in range(2, int(math.floor(sqrt) + 1)) if cores % num == 0
            ]
            if len(factors) == 0:
                factors = [1]

            diff = 0
            keep = 0
            for factor in factors:
                if diff == 0:
                    diff = cores - factor
                if keep == 0:
                    keep = factor
                tmp_diff = cores - factor
                if tmp_diff < diff:
                    diff = tmp_diff
                    keep = factor
            return [keep, int(cores / keep)]

        properties = dict(
            realN=nFromNb(baseN(self.nodes, self.memory_per_node), self.block_size),
            nb=self.block_size,
            pQ=get_grid(self.nodes, self.cores_per_node),
        )
        return self._data_from_jinja(**properties)

    def _data_from_jinja(self, **properties):
        template = jinja_environment.get_template('HPL.dat.jinja')
        return template.render(**properties)

    @property
    def threads(self):
        """Number of threads per process"""
        return str(self.attributes['threads'])

    @cached_property
    def mpirun(self):
        """Additional options passed as a list to the ``mpirun`` command"""
        cmd = self.attributes['mpirun']
        if cmd and cmd[0] != 'mpirun':
            cmd = ['mpirun']
        return [str(e) for e in cmd]

    @cached_property
    def srun_nodes(self):
        """Number of nodes the command must be executed on.
        Default: all nodes of the tag.
        """
        return self.attributes['srun_nodes']

    @cached_property
    def metrics_extractors(self):
        return HPLExtractor()

    def pre_execute(self, execution, context):
        with open('HPL.dat', 'w') as ostr:
            ostr.write(self.data)
