import unittest

from hpcbench.benchmark.sysbench import Sysbench
from .benchmark import AbstractBenchmarkTest


class TestSysbench(AbstractBenchmarkTest, unittest.TestCase):
    _expected_metrics = dict(
        minimum=0.03, average=0.03, maximum=0.19, percentile95=0.04, total_time=0.0876
    )

    def get_benchmark_clazz(self):
        return Sysbench

    def get_expected_metrics(self, category):
        return self._expected_metrics

    def get_benchmark_categories(self):
        return ['cpu']
