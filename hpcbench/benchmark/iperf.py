"""Iperf benchmark
    https://github.com/esnet/iperf
"""
from __future__ import division

import json

from cached_property import cached_property

from hpcbench.api import Benchmark, Metrics, MetricsExtractor
from hpcbench.toolbox.process import find_executable, physical_cpus


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

    def extract_metrics(self, metas):
        bits_in_mb = float(8 * 1024 * 1024)
        with open(self.stdout) as istr:
            data = json.load(istr)
        if not data['intervals']:
            raise Exception('Missing "intervals" in JSON: ')
        max_bits_per_second = max(
            [interval['sum']['bits_per_second'] for interval in data['intervals']]
        )
        sent = data['end']['sum_sent']
        received = data['end']['sum_received']
        return dict(
            max_bandwidth=max_bits_per_second / bits_in_mb,
            bandwidth_receiver=received['bits_per_second'] / bits_in_mb,
            bandwidth_sender=sent['bits_per_second'] / bits_in_mb,
            retransmits=sent['retransmits'],
        )


class Iperf(Benchmark):
    """Provides TCP benchmark.
    """

    name = 'iperf'

    DEFAULT_DEVICE = 'network'
    DEFAULT_EXECUTABLE = 'iperf3'
    DEFAULT_SERVER = "localhost"

    def __init__(self):
        # locate `stream_c` executable
        super(Iperf, self).__init__(
            attributes=dict(
                executable=Iperf.DEFAULT_EXECUTABLE,
                server=Iperf.DEFAULT_SERVER,
                options=["-P", str(physical_cpus())],
                mpirun=[],
            )
        )

    @cached_property
    def executable(self):
        """Get absolute path to iperf executable
        """
        return self.attributes['executable']

    @property
    def server(self):
        """Specifies the Iperf server to connect to"""
        return self.attributes['server']

    @property
    def mpirun(self):
        """List of mpirun options (prepended to the command)
        "mpirun" is added if attribute is not empty and
        do not start by mpirun
        """
        return [str(e) for e in self.attributes['mpirun']]

    @property
    def options(self):
        """List of additional arguments appended
        to the command line"""
        return [str(e) for e in self.attributes['options']]

    def execution_matrix(self, context):
        del context  # unused
        yield dict(
            category=Iperf.DEFAULT_DEVICE,
            command=self.mpirun
            + [
                find_executable(self.executable, required=False),
                '-c',
                self.server,
                '-J',
            ]
            + self.options,
        )

    @cached_property
    def metrics_extractors(self):
        return IPERFExtractor()
