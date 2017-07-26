import json
import os.path as osp
import shutil
import socket
import sys
import tempfile
from textwrap import dedent
import unittest
from cached_property import cached_property

from hpcbench.api import (
    Benchmark,
    Metric,
    MetricsExtractor,
)
from hpcbench.toolbox.contextlib_ext import pushd
from hpcbench.cli import bensh

from . benchmark.benchmark import AbstractBenchmarkTest


class FakeExtractor(MetricsExtractor):
    @property
    def metrics(self):
        return dict(
            performance=Metric('m', float),
            standard_error=Metric('m', float)
        )

    def extract(self, outdir, metas):
        with open(self.stdout(outdir)) as istr:
            content = istr.readlines()
            return dict(
                performance=float(content[0].strip()),
                standard_error=float(content[1].strip())
            )


class FakeBenchmark(Benchmark):
    name = 'fake'

    description = '''
        fake benchmark for HPCBench testing purpose
    '''

    def pre_execute(self):
        with open('test.py', 'w') as ostr:
            ostr.write(dedent("""\
            from __future__ import print_function
            import sys

            print(sys.argv[1])
            print(float(sys.argv[1]) / 10)
            """))

    @cached_property
    def execution_matrix(self):
        for value in (10, 50, 100):
            yield dict(
                category='main',
                command=[
                    sys.executable, 'test.py', str(value)
                ],
                metas=dict(
                    field=value / 10
                )
            )

    @property
    def metrics_extractors(self):
        return dict(main=FakeExtractor())

    @property
    def plots(self):
        return None


class TestFakeBenchmark(AbstractBenchmarkTest, unittest.TestCase):
    def get_benchmark_clazz(self):
        return FakeBenchmark

    def get_expected_metrics(self, category):
        return dict(
            performance=10.0,
            standard_error=1.0
        )

    def get_benchmark_categories(self):
        return ['main']


class TestDriver(unittest.TestCase):
    def get_campaign_file(self):
        return osp.splitext(__file__)[0] + '.yaml'

    def test_01_run(self):
        with pushd(TestDriver.TEST_DIR):
            self.driver = bensh.main(self.get_campaign_file())
        campaign_path = osp.join(TestDriver.TEST_DIR,
                                 self.driver.campaign_path)
        self.assertTrue(osp.isdir(campaign_path))
        # simply ensure metrics have been generated
        aggregated_metrics_f = osp.join(
            campaign_path,
            socket.gethostname(),
            '*',
            'test01',
            'main',
            'metrics.json'
        )
        self.assertTrue(osp.isfile(aggregated_metrics_f))
        with open(aggregated_metrics_f) as istr:
            aggregated_metrics = json.load(istr)
        self.assertTrue(len(aggregated_metrics), 3)

    @classmethod
    def setUpClass(cls):
        cls.TEST_DIR = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.TEST_DIR)
