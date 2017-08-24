"""the High-Performance Linpack Benchmark for Distributed-Memory Computers
    http://www.netlib.org/benchmark/hpl/
"""
import re
import shutil
import os
import os.path as osp

from cached_property import cached_property

from hpcbench.api import (
    Benchmark,
    Metrics,
    MetricsExtractor,
)
from hpcbench.toolbox.process import find_executable

class HPLExtractor(MetricsExtractor):
    """Ignore stdout until this line"""
    STDOUT_IGNORE_PRIOR = set([
        'T/V                N    NB     P     Q               Time                 Gflops',
    ])
    SECTIONS = ['flops', 'precision']

    def get_precision():
        FORMULA = "||Ax-b||_oo/(eps*(||A||_oo*||x||_oo+||b||_oo)*N)"
        expr = re.escape(FORMULA)
        expr += '=\s*(\S*)\s.*\s([A-Z]*)'
        return re.compile(expr)

    regex = dict(
        flops=re.compile('^[\\w]+[\s]+([\\d]+)[\s]+([\\d]+)[\s]+([\\d]+)[\s]+([\\d]+)[\s]+([\\d.]+)[\s]+([\\d.]+e[+-][\\d]+)'),
        precision=get_precision()
    )

    METRICS = dict(
        size_n=Metrics.Cardinal,
        size_nb=Metrics.Cardinal,
        size_p=Metrics.Cardinal,
        size_q=Metrics.Cardinal,
        time=Metrics.Second,
        flops=Metrics.Flops,
        validity=Metrics.Validity,
    )

    METRICS_NAMES = set(METRICS)

    @property
    def metrics(self):
        """ The metrics to be extracted.
            This property can not be replaced, but can be mutated as required
        """
        return HPLExtractor.METRICS

    def extract(self, outdir, metas):
        metrics = {}
        # parse stdout and extract desired metrics
        with open(self.stdout(outdir)) as istr:
            for line in istr:
                if line.strip() in self.STDOUT_IGNORE_PRIOR:
                    break
            for line in istr:
                line = line.strip()

                for sect in self.SECTIONS:
                    search = self.regex[sect].search(line)
                    if search:
                        if sect == 'flops':
                            metrics["size_n"]  = int(search.group(1))
                            metrics["size_nb"] = int(search.group(2))
                            metrics["size_p"]  = int(search.group(3))
                            metrics["size_q"]  = int(search.group(4))
                            metrics["time"]    = float(search.group(5))
                            metrics["flops"]   = float(search.group(6))
                        elif sect == 'precision':
                            metrics["precision"] = float(search.group(1))
                            metrics["validity"] = str(search.group(2))

        # ensure all metrics have been extracted
        unset_attributes = HPLExtractor.METRICS_NAMES - set(metrics)
        if any(unset_attributes):
            error = \
                'Could not extract some metrics: %s\n' \
                'metrics setted are: %s'
            raise Exception(error % (' ,'.join(unset_attributes),
                                     ' ,'.join(set(metrics))))
        return metrics


class HPL(Benchmark):
    """Benchmark wrapper for the HPLbench utility
    """
    DEFAULT_THREADS = [1]
    DEFAULT_DEVICE = 'cpu'
    DEFAULT_EXECUTABLE = 'xhpl'

    def __init__(self):
        # locate `stream_c` executable
        super(HPL, self).__init__(
            attributes=dict(
                threads=HPL.DEFAULT_THREADS,
                data="",
                device=HPL.DEFAULT_DEVICE,
                executable=HPL.DEFAULT_EXECUTABLE
            )
        )
    name = 'hpl'

    description = "Provides Intensive FLOPS benchmark."

    @property
    def execution_matrix(self):
        yield dict(
            category=HPL.DEFAULT_DEVICE,
            command=[
                './' + osp.basename(find_executable(self.attributes['executable'])),
            ],
            environment=dict(
                OMP_NUM_THREADS=str(self.attributes['threads'][0]),
                KMP_AFFINITY='scatter'
            ),
        )

    @cached_property
    def metrics_extractors(self):
        return HPLExtractor()

    def pre_execute(self):
      data = self.attributes['data']
      with open('HPL.dat', 'w') as ostr:
        ostr.write(data)
      shutil.copy(find_executable(self.attributes['executable']), '.')
