import unittest

from hpcbench.benchmark.basic import BASIC
from . benchmark import AbstractBenchmarkTest


class TestBasic(AbstractBenchmarkTest, unittest.TestCase):
    EXPECTED_METRICS = {
        'fs_local':True,
        'fs_gpfs':True,
        'in_network':True,
        'out_network':True,
        'hello':True,
    }

    def get_benchmark_clazz(self):
        return BASIC

    def get_expected_metrics(self, category):
        return TestBasic.EXPECTED_METRICS
    def get_benchmark_categories(self):
        return [self.get_benchmark_clazz().DEFAULT_DEVICE]

    @property
    def attributes(self):
        return dict(
            executable='/path/to/fake'
        )
