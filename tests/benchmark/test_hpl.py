import unittest

from hpcbench.benchmark.hpl import HPL
from . benchmark import AbstractBenchmarkTest


class TestHpl(AbstractBenchmarkTest, unittest.TestCase):
    EXPECTED_METRICS = dict(
        size_n=2096,
        size_nb=192,
        size_p=2,
        size_q=2,
        time=0.29,
        flops=2.098e+01,
        validity="PASSED",
        precision=0.0051555,
    )

    def get_benchmark_clazz(self):
        return HPL

    def get_expected_metrics(self, category):
        return TestHpl.EXPECTED_METRICS

    def get_benchmark_categories(self):
        return [self.get_benchmark_clazz().DEFAULT_DEVICE]
