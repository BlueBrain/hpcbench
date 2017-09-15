"""Iperf benchmark
    https://github.com/esnet/iperf
"""
import json

from cached_property import cached_property

from hpcbench.api import (
    Benchmark,
    Metrics,
    MetricsExtractor,
)
from hpcbench.toolbox.process import find_executable


class IPERFExtractor(MetricsExtractor):
    """Parse JSON file written by stream to extract interested metrics
    """
    @property
    def metrics(self):
        return dict(
            bandwidth_receiver=Metrics.MegaBytesPerSecond,
            bandwidth_sender=Metrics.MegaBytesPerSecond,
            max_bandwidth=Metrics.MegaBytesPerSecond,
            retransmits=Metrics.Cardinal,
        )

    def extract(self, outdir, metas):
        bits_in_mb = 8 * 1024 * 1024
        with open(self.stdout(outdir)) as istr:
            data = json.load(istr)
        max_bits_per_second = max(
            [
                interval['sum']['bits_per_second']
                for interval in data['intervals']
            ]
        )
        sent = data['end']['sum_sent']
        received = data['end']['sum_received']
        return dict(
            max_bandwidth=max_bits_per_second / bits_in_mb,
            bandwidth_receiver=received['bits_per_second'] / bits_in_mb,
            bandwidth_sender=sent['bits_per_second'] / bits_in_mb,
            retransmits=sent['retransmits']
        )


class Iperf(Benchmark):
    """Benchmark wrapper for the HPLbench utility
    """
    name = 'iperf'

    description = "Provides TCP benchmark."

    DEFAULT_DEVICE = 'network'
    DEFAULT_EXECUTABLE = 'iperf3'
    DEFAULT_SERVER = "localhost"

    def __init__(self):
        # locate `stream_c` executable
        super(Iperf, self).__init__(
            attributes=dict(
                executable=Iperf.DEFAULT_EXECUTABLE,
                server=Iperf.DEFAULT_SERVER,
                options=['-w', '1024k'],
            )
        )

    @cached_property
    def executable(self):
        """Get absolute path to iperf executable
        """
        return find_executable(self.attributes['executable'])

    @property
    def execution_matrix(self):
        yield dict(
            category=Iperf.DEFAULT_DEVICE,
            command=[
                self.executable,
                '-c',
                self.attributes['server'],
                '-J',
            ] + self.attributes['options'],
        )

    @cached_property
    def metrics_extractors(self):
        return IPERFExtractor()
