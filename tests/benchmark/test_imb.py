import unittest

from hpcbench.benchmark.imb import IMB
from . benchmark import AbstractBenchmarkTest


class TestImb(AbstractBenchmarkTest, unittest.TestCase):
    EXPECTED_METRICS = {
        IMB.PING_PONG: dict(
            latency=0.20,
            bandwidth=8344.45,
        ),
        IMB.ALL_TO_ALL: dict(
            latency=0.38,
        ),
        IMB.ALL_GATHER: dict(
            latency=0.65,
        ),
    }

    def get_benchmark_clazz(self):
        return IMB

    def get_expected_metrics(self, category):
        return TestImb.EXPECTED_METRICS[category]

    def get_benchmark_categories(self):
        return IMB.DEFAULT_CATEGORIES

    @property
    def attributes(self):
        return dict(
            executable='/path/to/fake'
        )
