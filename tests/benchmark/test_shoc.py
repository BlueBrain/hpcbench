import unittest

from hpcbench.benchmark.shoc import SHOC
from . benchmark import AbstractBenchmarkTest


class TestShoc(AbstractBenchmarkTest, unittest.TestCase):
    EXPECTED_METRICS = dict(
        h2d_bw=6.0504,
        d2h_bw=6.7152,
        flops_sp=3098.2900,
        flops_dp=1164.7500,
        gmem_readbw=147.9450,
        gmem_writebw=139.5960,
        lmem_readbw=1042.4400,
        lmem_writebw=925.3470,
    )

    def get_benchmark_clazz(self):
        return SHOC

    def get_expected_metrics(self, category):
        return TestShoc.EXPECTED_METRICS

    def get_benchmark_categories(self):
        return [self.get_benchmark_clazz().CATEGORY]

    @property
    def attributes(self):
        return dict(
            executable='/path/to/fake'
        )
