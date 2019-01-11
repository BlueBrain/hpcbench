import unittest

from hpcbench.benchmark.minigemm import MiniGEMM
from .benchmark import AbstractBenchmarkTest


class TestMiniGEMM(AbstractBenchmarkTest, unittest.TestCase):
    EXPECTED_METRICS = dict(time=135.999, gflops=198.926, checksum=1.48311e20)

    def get_benchmark_clazz(self):
        return MiniGEMM

    def get_expected_metrics(self, category):
        return TestMiniGEMM.EXPECTED_METRICS

    def get_benchmark_categories(self):
        return [self.get_benchmark_clazz().name]

    @property
    def attributes(self):
        return dict(executable='/path/to/fake')
