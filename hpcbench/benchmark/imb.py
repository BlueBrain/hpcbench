"""The Intel MPI Benchmarks
    https://software.intel.com/en-us/articles/intel-mpi-benchmarks
"""
import os.path as osp
import re

from cached_property import cached_property

from hpcbench.api import (
    Benchmark,
    Metrics,
    MetricsExtractor,
)
from hpcbench.toolbox.process import find_executable

class IMBExtractor(MetricsExtractor):
    """Ignore stdout until this line"""
    STDOUT_IGNORE_PRIOR = (
        "# Benchmarking PingPong"
    )

    latency_bandwidth = re.compile(
        r'^\s*(\d)+\s+\d+\s+([0-9]*\.?[0-9]+)[\s]+([0-9]*\.?[0-9]+)'
    )

    METRICS = dict(
        latency=Metrics.Second,
        bandwidth=Metrics.Flops,
    )

    METRICS_NAMES = set(METRICS)

    @property
    def metrics(self):
        """ The metrics to be extracted.
            This property can not be replaced, but can be mutated as required
        """
        return IMBExtractor.METRICS

    def extract(self, outdir, metas):
        metrics = {}
        s_latency = set()
        s_bandwidth = set()
        # parse stdout and extract desired metrics
        with open(self.stdout(outdir)) as istr:
            for line in istr:
                if line.strip() == IMBExtractor.STDOUT_IGNORE_PRIOR:
                    break
            for line in istr:
                line = line.strip()
                print(repr(line))
                search = IMBExtractor.latency_bandwidth.search(line)
                if search:
                    byte = int(search.group(1))
                    if byte != 0:
                        s_latency.add(float(search.group(2)))
                        s_bandwidth.add(float(search.group(3)))

        metrics["latency"] = min(s_latency)
        metrics["bandwidth"] = max(s_bandwidth)
        # ensure all metrics have been extracted
        unset_attributes = IMBExtractor.METRICS_NAMES - set(metrics)
        if any(unset_attributes):
            error = \
                'Could not extract some metrics: %s\n' \
                'metrics setted are: %s'
            raise Exception(error % (' ,'.join(unset_attributes),
                                     ' ,'.join(set(metrics))))
        return metrics


class IMB(Benchmark):
    """Benchmark wrapper for the IMBbench utility
    """
    DEFAULT_THREADS = [1]
    DEFAULT_DEVICE = 'cpu'
    DEFAULT_EXECUTABLE = 'IMB-MPI1'

    def __init__(self):
        # locate `stream_c` executable
        super(IMB, self).__init__(
            attributes=dict(
                threads=IMB.DEFAULT_THREADS,
                data="",
                device=IMB.DEFAULT_DEVICE,
                executable=IMB.DEFAULT_EXECUTABLE
            )
        )
    name = 'imb'

    description = "Provides latency/bandwidth of the newtork."

    @cached_property
    def executable(self):
        """Get absolute path to executable
        """
        return find_executable(self.attributes['executable'])

    @property
    def execution_matrix(self):
        yield dict(
            category=IMB.DEFAULT_DEVICE,
            command=[
                './' + osp.basename(self.executable),
            ],
        )

    @cached_property
    def metrics_extractors(self):
        return IMBExtractor()
