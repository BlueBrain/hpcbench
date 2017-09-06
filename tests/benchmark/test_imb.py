import unittest

from hpcbench.benchmark.imb import IMB
from . benchmark import AbstractBenchmarkTest


class TestImb(AbstractBenchmarkTest, unittest.TestCase):
    EXPECTED_METRICS = dict(
        latency=0.20,
        bandwidth=8344.45,
    )

    def get_benchmark_clazz(self):
        return IMB

    def get_expected_metrics(self, category):
        return TestImb.EXPECTED_METRICS

    def get_benchmark_categories(self):
        return [self.get_benchmark_clazz().DEFAULT_DEVICE]

    @property
    def attributes(self):
        return dict(
            executable='/path/to/fake'
        )
