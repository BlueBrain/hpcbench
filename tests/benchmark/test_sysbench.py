import unittest

from . benchmark import AbstractBenchmark

from hpcbench.benchmark.sysbench import Sysbench


class TestSysbench(AbstractBenchmark, unittest.TestCase):
    def get_benchmark_clazz(self):
        return Sysbench

    def get_expected_metrics(self, category):
        return dict(
            minimum=0.03,
            average=0.03,
            maximum=0.19,
            percentile95=0.04,
            total_time=0.0876,
        )

    def get_benchmark_categories(self):
        return ['cpu']
