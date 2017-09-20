import unittest

from hpcbench.benchmark.mdtest import MDTest
from . benchmark import AbstractBenchmarkTest


class TestMDTestBenchmark(AbstractBenchmarkTest, unittest.TestCase):
    def get_benchmark_clazz(self):
        return MDTest

    def get_expected_metrics(self, category):
        return {
            'max_directory_creation': 34007.259,
            'max_directory_removal': 152233.725,
            'max_directory_stat': 1006125.068,
            'max_file_creation': 133494.636,
            'max_file_read': 608366.537,
            'max_file_removal': 272025.849,
            'max_file_stat': 998033.108,
            'max_tree_creation': 127100.121,
            'max_tree_removal': 23.701,
            'mean_directory_creation': 30427.408,
            'mean_directory_removal': 138105.155,
            'mean_directory_stat': 1001892.446,
            'mean_file_creation': 132076.899,
            'mean_file_read': 606460.822,
            'mean_file_removal': 271328.055,
            'mean_file_stat': 994007.14,
            'mean_tree_creation': 87924.496,
            'mean_tree_removal': 23.611,
            'min_directory_creation': 27696.68,
            'min_directory_removal': 128462.328,
            'min_directory_stat': 998097.232,
            'min_file_creation': 130104.228,
            'min_file_read': 603241.794,
            'min_file_removal': 270554.002,
            'min_file_stat': 990060.924,
            'min_tree_creation': 29127.111,
            'min_tree_removal': 23.46,
            'stddev_directory_creation': 2645.324,
            'stddev_directory_removal': 10209.84,
            'stddev_directory_stat': 3291.912,
            'stddev_file_creation': 1438.675,
            'stddev_file_read': 2289.008,
            'stddev_file_removal': 603.294,
            'stddev_file_stat': 3255.119,
            'stddev_tree_creation': 42335.468,
            'stddev_tree_removal': 0.107,
        }

    def get_benchmark_categories(self):
        return ['disk']

    @property
    def attributes(self):
        return dict(
            executable='/path/to/fake'
        )
