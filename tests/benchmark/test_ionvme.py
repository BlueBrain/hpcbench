import os
import os.path as osp
import unittest

from hpcbench.benchmark.ionvme import IONVME, IONVMEExtractor
from hpcbench.toolbox.contextlib_ext import mkdtemp, pushd
from .benchmark import AbstractBenchmarkTest


class TestIonvme(AbstractBenchmarkTest, unittest.TestCase):
    EXPECTED_METRICS = {
        IONVME.NVME_READ: dict(bandwidth=494.29915046691895),
        IONVME.NVME_WRITE: dict(bandwidth=398.93171882629395),
    }

    def get_benchmark_clazz(self):
        return IONVME

    def get_expected_metrics(self, category):
        return TestIonvme.EXPECTED_METRICS[category]

    def get_benchmark_categories(self):
        return IONVME.DEFAULT_CATEGORIES

    @property
    def attributes(self):
        return dict(executable='/path/to/fake')

    def test_parse_bandwidth_linux(self):
        expected = 150
        self.assertEqual(
            IONVMEExtractor.parse_bandwidth_linux(expected * 1024, "KB/s"), expected
        )
        self.assertEqual(
            IONVMEExtractor.parse_bandwidth_linux(expected / 1024.0, "GB/s"), expected
        )
        self.assertEqual(
            IONVMEExtractor.parse_bandwidth_linux(expected * 1024 * 1024, "bytes/s"),
            expected,
        )
        with self.assertRaises(Exception):
            IONVMEExtractor.parse_bandwidth_linux(0, '?')

    def test_pre_execute_copy(self):
        with mkdtemp() as path:
            with pushd(path):
                benchmark = IONVME()
                benchmark.pre_execute(None)
                self.assertTrue(osp.isfile(IONVME.SCRIPT_NAME))
                self.assertTrue(os.access(IONVME.SCRIPT_NAME, os.X_OK))
