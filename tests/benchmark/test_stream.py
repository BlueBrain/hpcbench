import unittest

from hpcbench.benchmark.stream import Stream
from .benchmark import AbstractBenchmarkTest


class TestStream(AbstractBenchmarkTest, unittest.TestCase):
    EXPECTED_METRICS = dict(
        copy_bandwidth=65965.0610,
        copy_avg_time=0.0340,
        copy_min_time=0.0326,
        copy_max_time=0.0411,
        scale_bandwidth=66962.5477,
        scale_avg_time=0.0340,
        scale_min_time=0.0321,
        scale_max_time=0.0440,
        add_bandwidth=64950.7676,
        add_avg_time=0.0515,
        add_min_time=0.0496,
        add_max_time=0.0546,
        triad_bandwidth=64010.9863,
        triad_avg_time=0.0508,
        triad_min_time=0.0503,
        triad_max_time=0.0516,
    )

    def get_benchmark_clazz(self):
        return Stream

    def get_expected_metrics(self, category):
        return TestStream.EXPECTED_METRICS

    def get_benchmark_categories(self):
        return [self.get_benchmark_clazz().name]

    @property
    def attributes(self):
        return dict(executable='/path/to/fake')
