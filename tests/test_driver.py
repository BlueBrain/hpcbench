import json
import os.path as osp
import shutil
import socket
import sys
import tempfile
from textwrap import dedent
import unittest

from hpcbench.api import (
    Benchmark,
    MetricsExtractor,
)
from hpcbench.toolbox.contextlib_ext import (
    capture_stdout,
    pushd,
)
from hpcbench.cli import (
    bendoc,
    benplot,
    bensh,
    benumb,
)

from . benchmark.benchmark import AbstractBenchmark

class FakeExtractor(MetricsExtractor):
    def metrics(self):
        return dict(
            performance=dict(type=float, unit='m'),
            standard_error=dict(type=float, unit='m')
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

    def pre_execution(self):
        with open('test.py', 'w') as ostr:
            ostr.write(dedent("""\
            from __future__ import print_function
            import sys

            print(sys.argv[1])
            print(float(sys.argv[1]) / 10)
            """))

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

    def metrics_extractors(self):
        return dict(main=FakeExtractor())

    def plots(self):
        return dict(
            main=[
                dict(
                    name="{hostname} {category} Performance",
                    series=dict(
                        metas=['field'],
                        metrics=[
                            'main__performance',
                            'main__standard_error'
                        ],
                    ),
                    plotter=self.plot_performance
                )
            ]
        )

    def plot_performance(self, plt, description, metas, metrics):
        plt.errorbar(metas['field'],
                     metrics['main__performance'],
                     yerr=metrics['main__standard_error'],
                     fmt='o', ecolor='g', capthick=2)


class TestFakeBenchmark(AbstractBenchmark, unittest.TestCase):
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
        TestDriver.CAMPAIGN_PATH = osp.join(TestDriver.TEST_DIR,
                                 self.driver.campaign_path)
        self.assertTrue(osp.isdir(TestDriver.CAMPAIGN_PATH))
        # simply ensure metrics have been generated
        aggregated_metrics_f = osp.join(
            TestDriver.CAMPAIGN_PATH,
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

    def test_02_number(self):
        self.assertIsNotNone(TestDriver.CAMPAIGN_PATH)
        benumb.main(TestDriver.CAMPAIGN_PATH)
        # FIXME add checks

    def test_03_plot(self):
        self.assertIsNotNone(TestDriver.CAMPAIGN_PATH)
        benplot.main(TestDriver.CAMPAIGN_PATH)
        plot_file_f = osp.join(
            TestDriver.CAMPAIGN_PATH,
            socket.gethostname(),
            '*',
            'test01',
            'main',
            '91859462124ccb92b82125a312b1ff3d10'
            '86fe44b668f96eddc073e3e4e37204.png'
        )
        self.assertTrue(osp.isfile(plot_file_f))

    def test_04_report(self):
        self.assertIsNotNone(TestDriver.CAMPAIGN_PATH)
        with capture_stdout() as stdout:
            bendoc.main(TestDriver.CAMPAIGN_PATH)
        content = stdout.getvalue()
        self.assertTrue(content)


    @classmethod
    def setUpClass(cls):
        cls.TEST_DIR = tempfile.mkdtemp()
        cls.CAMPAIGN_PATH = None

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.TEST_DIR)
