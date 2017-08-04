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
    benelastic,
    benplot,
    bensh,
    benumb,
)

from .benchmark.benchmark import AbstractBenchmarkTest
from . import DriverTestCase, FakeBenchmark

class TestDriver(DriverTestCase, unittest.TestCase):
    def test_get_unknown_benchmark_class(self):
        with self.assertRaises(NameError) as exc:
            Benchmark.get_subclass('unkn0wnb3nchm4rk')
        self.assertEqual(
            str(exc.exception),
            "Not a valid Benchmark class: unkn0wnb3nchm4rk"
        )

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
            '7b9d424b038a9c89bf48c0b183864e61b1'
            '724a109b8f2d9d756b594f8f29b861.png'
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
        exporter = benelastic.main(TestDriver.CAMPAIGN_PATH)
        # Ensure they are searchable
        exporter.index_client.refresh(exporter.index_name)
        # Expect 3 documents in the index dedicated to the campaign
        resp = exporter.es_client.count(exporter.index_name)
        self.assertEqual(resp['count'], 3)
        if 'UT_KEEP_ELASTICSEARCH_INDEX' not in os.environ:
            # Cleanup
            exporter.remove_index()


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
