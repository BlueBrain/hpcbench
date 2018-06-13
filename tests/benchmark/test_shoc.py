import unittest

from hpcbench.benchmark.shoc import SHOC
from .benchmark import AbstractBenchmarkTest


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
        sgemm_n=579.3240,
        dgemm_n=75.6221,
    )

    def get_benchmark_clazz(self):
        return SHOC

    def get_expected_metrics(self, category):
        return TestShoc.EXPECTED_METRICS

    def get_benchmark_categories(self):
        return [self.get_benchmark_clazz().CATEGORY]

    @property
    def attributes(self):
        return dict(executable='/path/to/fake')

    def test_extra_attributes(self):
        self.assertExecutionMatrix(
            dict(size=42, executable='/fake'),
            [dict(category='gpu', command=['/fake', '-cuda', '-d', '0', '-s', '42'])],
        )
        self.assertExecutionMatrix(
            dict(device=42, executable='/fake'),
            [dict(category='gpu', command=['/fake', '-cuda', '-d', '42', '-s', '1'])],
        )
        self.assertExecutionMatrix(
            dict(executable='/fake', options='uber option'),
            [
                dict(
                    category='gpu',
                    command=['/fake', '-cuda', '-d', '0', '-s', '1', 'uber', 'option'],
                )
            ],
        )
        self.assertExecutionMatrix(
            dict(executable='/fake', options=['uber', 'option']),
            [
                dict(
                    category='gpu',
                    command=['/fake', '-cuda', '-d', '0', '-s', '1', 'uber', 'option'],
                )
            ],
        )
