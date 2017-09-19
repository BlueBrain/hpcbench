import os
import os.path as osp
import unittest

from hpcbench.benchmark.iossd import (
    IOSSD,
    IOSSDExtractor,
)
from hpcbench.toolbox.contextlib_ext import (
    mkdtemp,
    pushd,
)
from . benchmark import AbstractBenchmarkTest


class TestIossd(AbstractBenchmarkTest, unittest.TestCase):
    EXPECTED_METRICS = {
        IOSSD.SSD_READ: dict(
            bandwidth=494.29915046691895,
        ),
        IOSSD.SSD_WRITE: dict(
            bandwidth=398.93171882629395,
        ),
    }

    def get_benchmark_clazz(self):
        return IOSSD

    def get_expected_metrics(self, category):
        return TestIossd.EXPECTED_METRICS[category]

    def get_benchmark_categories(self):
        return IOSSD.DEFAULT_CATEGORIES

    @property
    def attributes(self):
        return dict(
            executable='/path/to/fake'
        )

    def test_parse_bandwidth_linux(self):
        expected = 150
        self.assertEqual(
            IOSSDExtractor.parse_bandwidth_linux(expected * 1024, "KB/s"),
            expected
        )
        self.assertEqual(
            IOSSDExtractor.parse_bandwidth_linux(expected / 1024.0, "GB/s"),
            expected
        )
        self.assertEqual(
            IOSSDExtractor.parse_bandwidth_linux(expected * 1024 * 1024,
                                                 "bytes/s"),
            expected
        )
        with self.assertRaises(Exception):
            IOSSDExtractor.parse_bandwidth_linux(0, '?')

    def test_pre_execute_copy(self):
        with mkdtemp() as path:
            with pushd(path):
                benchmark = IOSSD()
                benchmark.pre_execute(None)
                self.assertTrue(osp.isfile(IOSSD.SCRIPT_NAME))
                self.assertTrue(os.access(IOSSD.SCRIPT_NAME, os.X_OK))
