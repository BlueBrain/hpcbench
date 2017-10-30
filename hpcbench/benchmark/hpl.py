"""the High-Performance Linpack Benchmark for Distributed-Memory Computers
    http://www.netlib.org/benchmark/hpl/
"""
import os.path as osp
import re
import shutil

from cached_property import cached_property

from hpcbench.api import (
    Benchmark,
    Metric,
    Metrics,
    MetricsExtractor,
)
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
        precision=get_precision_regex()
    )

    METRICS = dict(
        size_n=Metrics.Cardinal,
        size_nb=Metrics.Cardinal,
        size_p=Metrics.Cardinal,
        size_q=Metrics.Cardinal,
        time=Metrics.Second,
        flops=Metrics.Flops,
        validity=Metrics.Bool,
        precision=Metric(unit='', type=float)
    )

    METRICS_NAMES = set(METRICS)

    REGEX_METRICS = dict(
        flops=dict(
            size_n=(int, 1),
            size_nb=(int, 2),
            size_p=(int, 3),
            size_q=(int, 4),
            time=(float, 5),
            flops=(float, 6, 1e+9),
        ),
        precision=dict(
            precision=(float, 1),
        )
    )

    @property
    def metrics(self):
        """ The metrics to be extracted.
            This property can not be replaced, but can be mutated as required
        """
        return HPLExtractor.METRICS

    def extract_metrics(self, outdir, metas):
        metrics = {}
        # parse stdout and extract desired metrics
        with open(self.stdout(outdir)) as istr:
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
            if len(data) == 3:
                mvalue *= data[2]
            metrics[metric] = mvalue
        if section == 'precision':
            metrics['validity'] = str(search.group(2)) == "PASSED"


class HPL(Benchmark):
    """Benchmark wrapper for the HPLbench utility
    """
    DEFAULT_THREADS = 1
    DEFAULT_DEVICE = 'cpu'
    DEFAULT_EXECUTABLE = 'xhpl'

    def __init__(self):
        # locate `stream_c` executable
        super(HPL, self).__init__(
            attributes=dict(
                threads=HPL.DEFAULT_THREADS,
                data="",
                executable=HPL.DEFAULT_EXECUTABLE,
                mpirun=[],
                srun_nodes=0,
            )
        )
    name = 'hpl'

    description = "Provides Intensive FLOPS benchmark."

    @cached_property
    def executable(self):
        """Path to HPL executable
        """
        return self.attributes['executable']

    def execution_matrix(self, context):
        del context  # unused
        cmd = dict(
            category=HPL.DEFAULT_DEVICE,
            command=self.mpirun + [
                './' + osp.basename(find_executable(self.executable)),
            ],
            environment=dict(
                OMP_NUM_THREADS=self.threads,
                KMP_AFFINITY='scatter'
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
        return self.attributes['data']

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

    def pre_execute(self, execution):
        with open('HPL.dat', 'w') as ostr:
            ostr.write(self.data)
        shutil.copy(self.executable, '.')
