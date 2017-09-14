import unittest

from hpcbench.benchmark.iperf import IPERF
from . benchmark import AbstractBenchmarkTest


class TestIperf(AbstractBenchmarkTest, unittest.TestCase):
    EXPECTED_METRICS = dict(
        bandwidth_receiver=5.75,
    )

    def get_benchmark_clazz(self):
        return IPERF

    def get_expected_metrics(self, category):
        return TestIperf.EXPECTED_METRICS

    def get_benchmark_categories(self):
        return [self.get_benchmark_clazz().DEFAULT_DEVICE]

    @property
    def attributes(self):
        return dict(
            executable='/path/to/fake'
        )
