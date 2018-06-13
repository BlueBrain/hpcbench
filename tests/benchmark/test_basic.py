import unittest

from hpcbench.benchmark.basic import Basic
from .benchmark import AbstractBenchmarkTest


class TestBasic(AbstractBenchmarkTest, unittest.TestCase):
    EXPECTED_METRICS = {
        'fs_local': True,
        'fs_network': True,
        'outside_network': True,
        'hello_world': False,
    }

    def get_benchmark_clazz(self):
        return Basic

    def get_expected_metrics(self, category):
        return TestBasic.EXPECTED_METRICS

    def get_benchmark_categories(self):
        return [Basic.CATEGORY]

    def check_executable_availability(self):
        return True
