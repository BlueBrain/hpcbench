import unittest

from hpcbench.benchmark.custream import CUDAStream
from .benchmark import AbstractBenchmarkTest


class TestCUDAStream(AbstractBenchmarkTest, unittest.TestCase):
    EXPECTED_METRICS = dict(
        copy_bandwidth=746.0,
        copy_avg_time=0.00134171,
        copy_min_time=0.00133991,
        copy_max_time=0.00134277,
        scale_bandwidth=745.7866,
        scale_avg_time=0.00134183,
        scale_min_time=0.00134087,
        scale_max_time=0.00134301,
        add_bandwidth=784.5686,
        add_avg_time=0.00191258,
        add_min_time=0.00191188,
        add_max_time=0.00191402,
        triad_bandwidth=785.3521,
        triad_avg_time=0.00191215,
        triad_min_time=0.00190997,
        triad_max_time=0.00192785,
    )

    def get_benchmark_clazz(self):
        return CUDAStream

    def get_expected_metrics(self, category):
        return TestCUDAStream.EXPECTED_METRICS

    def get_benchmark_categories(self):
        return [self.get_benchmark_clazz().name]

    @property
    def attributes(self):
        return dict(executable='/path/to/fake')
