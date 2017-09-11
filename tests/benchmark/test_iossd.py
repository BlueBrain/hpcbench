import unittest

from hpcbench.benchmark.iossd import IOSSD
from . benchmark import AbstractBenchmarkTest


class TestIossd(AbstractBenchmarkTest, unittest.TestCase):
    EXPECTED_METRICS = {
        IOSSD.SSD_READ: dict(
            bandwidth=494,
        ),
        IOSSD.SSD_WRITE: dict(
            bandwidth=398,
        ),
    }

    def get_benchmark_clazz(self):
        return IOSSD

    def get_expected_metrics(self, category):
        return TestIossd.EXPECTED_METRICS[category]

    def get_benchmark_categories(self):
        return IOSSD.DEFAULT_CATEGORIES

    @property
    def attributes(self):
        return dict(
            executable='/path/to/fake'
        )
