import json
import os
import os.path as osp
import shutil
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
from hpcbench.toolbox.contextlib_ext import (
    capture_stdout,
    pushd,
)
from hpcbench.cli import (
    bendoc,
    benelk,
    benplot,
    bensh,
    benumb,
)

from .benchmark.benchmark import AbstractBenchmarkTest


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
        assert not osp.isfile(self.stderr(outdir))


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
        return [dict(
            category='main',
            command=[
                sys.executable, 'test.py', str(value)
            ],
            metas=dict(
                field=value / 10
            )
        )
            for value in (10, 50, 100)
        ]

    @property
    def metrics_extractors(self):
        return dict(main=FakeExtractor())

    @property
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
    @staticmethod
    def get_campaign_file():
        return osp.splitext(__file__)[0] + '.yaml'

    def test_get_unknown_benchmark_class(self):
        with self.assertRaises(NameError) as exc:
            Benchmark.get_subclass('unkn0wnb3nchm4rk')
        self.assertEqual(
            str(exc.exception),
            "Not a valid Benchmark class: unkn0wnb3nchm4rk"
        )

    @classmethod
    def setUpClass(cls):
        cls.TEST_DIR = tempfile.mkdtemp()
        with pushd(TestDriver.TEST_DIR):
            cls.driver = bensh.main(cls.get_campaign_file())
        cls.CAMPAIGN_PATH = osp.join(TestDriver.TEST_DIR,
                                     cls.driver.campaign_path)

    def test_run_01(self):
        self.assertTrue(osp.isdir(self.CAMPAIGN_PATH))
        # simply ensure metrics have been generated
        aggregated_metrics_f = osp.join(
            TestDriver.CAMPAIGN_PATH,
            TestDriver.driver.node,
            '*',
            'test01',
            'main',
            'metrics.json'
        )
        self.assertTrue(osp.isfile(aggregated_metrics_f), "Not file: " + aggregated_metrics_f)
        with open(aggregated_metrics_f) as istr:
            aggregated_metrics = json.load(istr)
        self.assertTrue(len(aggregated_metrics), 3)

    def test_02_number(self):
        self.assertIsNotNone(TestDriver.CAMPAIGN_PATH)
        benumb.main(TestDriver.CAMPAIGN_PATH)
        # FIXME add checks

    def test_03_plot(self):
        self.test_02_number()
        self.assertIsNotNone(TestDriver.CAMPAIGN_PATH)
        benplot.main(TestDriver.CAMPAIGN_PATH)
        plot_file_f = osp.join(
            TestDriver.CAMPAIGN_PATH,
            TestDriver.driver.node,
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

    @unittest.skipIf('UT_SKIP_ELASTICSEARCH' in os.environ,
                     'manually disabled from environment')
    def test_05_es_dump(self):
        # Push documents to Elasticsearch
        argv = [TestDriver.CAMPAIGN_PATH]
        if 'UT_ELASTICSEARCH_HOST' in os.environ:
            argv += ['--es', os.environ['UT_ELASTICSEARCH_HOST']]
        exporter = benelk.main(TestDriver.CAMPAIGN_PATH)
        # Ensure they are searchable
        exporter.index_client.refresh(exporter.index_name)
        # Expect 3 documents in the index dedicated to the campaign
        resp = exporter.es_client.count(exporter.index_name)
        self.assertEqual(resp['count'], 3)
        if 'UT_KEEP_ELASTICSEARCH_INDEX' not in os.environ:
            # Cleanup
            exporter.remove_index()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.TEST_DIR)
