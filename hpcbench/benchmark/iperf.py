"""Iperf benchmark
    https://github.com/esnet/iperf
"""
import re

from cached_property import cached_property

from hpcbench.api import (
    Benchmark,
    Metrics,
    MetricsExtractor,
)
from hpcbench.toolbox.process import find_executable

class IPERFExtractor(MetricsExtractor):
    """Ignore stdout until this line"""
    STDOUT_IGNORE_PRIOR = (
        "- - - - - - - - - - - - - - - - - - - - - - - - -"
    )

    METRICS = dict(
        bandwidth_receiver=Metrics.MegaBytesPerSecond,
    )

    METRICS_NAMES = set(METRICS)

    @property
    def metrics(self):
        """ The metrics to be extracted.
            This property can not be replaced, but can be mutated as required
        """
        return IPERFExtractor.METRICS

    def extract(self, outdir, metas):
        metrics = {}
        # parse stdout and extract desired metrics
        with open(self.stdout(outdir)) as istr:
            for line in istr:
                if line.strip() == IPERFExtractor.STDOUT_IGNORE_PRIOR:
                    break
            for line in istr:
                line = line.strip()
                if line.find("receiver") != -1:
                    split = line.split()
                    metrics["bandwidth_receiver"] = float(split[6])

        # ensure all metrics have been extracted
        unset_attributes = IPERFExtractor.METRICS_NAMES - set(metrics)
        if any(unset_attributes):
            error = \
                'Could not extract some metrics: %s\n' \
                'metrics setted are: %s'
            raise Exception(error % (' ,'.join(unset_attributes),
                                     ' ,'.join(set(metrics))))
        return metrics


class IPERF(Benchmark):
    """Benchmark wrapper for the HPLbench utility
    """
    DEFAULT_DEVICE = 'cpu'
    DEFAULT_EXECUTABLE = 'iperf3'
    DEFAULT_CLIENT = "todefine"

    def __init__(self):
        # locate `stream_c` executable
        super(IPERF, self).__init__(
            attributes=dict(
                device=IPERF.DEFAULT_DEVICE,
                executable=IPERF.DEFAULT_EXECUTABLE
            )
        )
    name = 'iperf3'

    description = "Provides TCB benchmark."

    @cached_property
    def executable(self):
        """Get absolute path to executable
        """
        return find_executable(self.attributes['executable'])

    @property
    def execution_matrix(self):
        yield dict(
            category=IPERF.DEFAULT_DEVICE,
            command=[
                self.executable,
                '-c',
                IPERF.DEFAULT_CLIENT,
                '-w',
                '1024k',
            ],
        )

    @cached_property
    def metrics_extractors(self):
        return IPERFExtractor()
