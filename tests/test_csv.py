import csv
import inspect
import os.path as osp
import shutil
import unittest

from hpcbench.cli import bencsv, bensh
from hpcbench.export.csvexport import CSVExporter
from hpcbench.toolbox.contextlib_ext import pushd
from . import DriverTestCase, FakeBenchmark


class TestCSV(unittest.TestCase):

    OUTFILE = 'output.csv'
    PERFORMANCE_METRIC = 'metrics.0.measurement.performance'

    def setUp(self):
        self.temp_dir = DriverTestCase.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_csv(self):
        with pushd(self.temp_dir):
            bench = bensh.main(TestCSV.campaign_file())
            csv_exporter = CSVExporter(bench.campaign_path, TestCSV.OUTFILE)
            csv_exporter.export()
            with open(self.OUTFILE, 'r') as f:
                table = [row for row in csv.DictReader(f)]
                metric_perf = {float(p[self.PERFORMANCE_METRIC]) for p in table}
                self.assertEqual(metric_perf, set(FakeBenchmark.INPUTS))

    def test_csv_cli(self):
        with pushd(self.temp_dir):
            bench = bensh.main(TestCSV.campaign_file())
            bencsv.main(['--output', self.OUTFILE, bench.campaign_path])
            with open(self.OUTFILE, 'r') as f:
                table = [row for row in csv.DictReader(f)]
                metric_perf = {float(p[self.PERFORMANCE_METRIC]) for p in table}
                self.assertEqual(metric_perf, set(FakeBenchmark.INPUTS))

    @classmethod
    def campaign_file(cls, suffix=""):
        return osp.splitext(inspect.getfile(cls))[0] + suffix + '.yaml'
