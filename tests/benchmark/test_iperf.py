import unittest

from hpcbench.benchmark.iperf import Iperf
from .benchmark import AbstractBenchmarkTest


class TestIperf(AbstractBenchmarkTest, unittest.TestCase):
    EXPECTED_METRICS = dict(
        bandwidth_receiver=13.488642581094329,
        bandwidth_sender=13.803695281821934,
        max_bandwidth=14.991833899605632,
        retransmits=42,
    )

    def get_benchmark_clazz(self):
        return Iperf

    def get_expected_metrics(self, category):
        return TestIperf.EXPECTED_METRICS

    def get_benchmark_categories(self):
        return [Iperf.DEFAULT_DEVICE]

    @property
    def attributes(self):
        return dict(executable='/path/to/fake')
