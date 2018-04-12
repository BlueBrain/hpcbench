import unittest

from hpcbench.api.v1 import Benchmark
from . import AbstractBenchmarkTest


class TestFakeBenchmark(AbstractBenchmarkTest, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from hpcbench.campaign import PluginsLoader
        PluginsLoader().load('tests/benchmark/fake')

    def get_benchmark_clazz(self):
        return Benchmark.get_subclass('fake')

    def get_expected_metrics(self, category):
        return dict(
            performance=10.0,
            standard_error=1.0,
            pairs=[
                dict(first=1.5, second=True),
                dict(first=3.0, second=False),
            ],
        )

    def get_benchmark_categories(self):
        return ['main']
