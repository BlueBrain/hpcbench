import csv
import inspect
import os.path as osp
import shutil
import tempfile
import unittest

from hpcbench.campaign import PluginsLoader
from hpcbench.cli import (
    bencsv,
    bensh,
)
from hpcbench.export.csvexport import CSVExporter
from hpcbench.toolbox.contextlib_ext import pushd


class TestCSV(unittest.TestCase):

    OUTFILE = 'output.csv'

    @classmethod
    def setUpClass(cls):
        mod = PluginsLoader().load('tests/benchmark/fake')
        cls.FAKE_INPUTS = set(mod.FakeBenchmark.INPUTS)

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix='hpcbench-ut')

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_csv(self):
        with pushd(self.temp_dir):
            bench = bensh.main(TestCSV.campaign_file())
            with pushd(bench.campaign_path):
                csv_exporter = CSVExporter(bench, TestCSV.OUTFILE)
                csv_exporter.export()
                with open(self.OUTFILE, 'r') as f:
                    table = [row for row in csv.DictReader(f)]
                    metric_perf = {float(p['metrics.performance'])
                                   for p in table}
                    self.assertEqual(metric_perf, TestCSV.FAKE_INPUTS)

    def test_csv_cli(self):
        with pushd(self.temp_dir):
            bench = bensh.main(TestCSV.campaign_file())
            bencsv.main(['--output', self.OUTFILE, bench.campaign_path])
            with open(osp.join(bench.campaign_path, self.OUTFILE), 'r') as f:
                table = [row for row in csv.DictReader(f)]
                metric_perf = {float(p['metrics.performance']) for p in table}
                self.assertEqual(metric_perf, TestCSV.FAKE_INPUTS)

    @classmethod
    def campaign_file(cls, suffix=""):
        return osp.splitext(inspect.getfile(cls))[0] + suffix + '.yaml'
