import inspect
import os.path as osp
import shutil
import unittest

from hpcbench.campaign import merge_campaigns
from hpcbench.cli import benmerge, bensh
from hpcbench.toolbox.contextlib_ext import pushd
from . import DriverTestCase


class TestMerge(unittest.TestCase):
    def setUp(self):
        self.temp_dir = DriverTestCase.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_same_host(self):
        with pushd(self.temp_dir):
            bench1 = bensh.main(TestMerge.campaign_file())
            bench2 = bensh.main(TestMerge.campaign_file())
            merge_campaigns(bench1.campaign_path, bench2.campaign_path)

    def test_different_host(self):
        with pushd(self.temp_dir):
            campaign = TestMerge.campaign_file()
            bench1 = bensh.main(['-n', 'foo', campaign])
            bench2 = bensh.main(['-n', 'bar', campaign])
            merge_campaigns(bench1.campaign_path, bench2.campaign_path)

    def test_executable(self):
        with pushd(self.temp_dir):
            benmerge.main(
                [
                    bensh.main(TestMerge.campaign_file()).campaign_path,
                    bensh.main(TestMerge.campaign_file()).campaign_path,
                    bensh.main(TestMerge.campaign_file()).campaign_path,
                ]
            )

    @classmethod
    def campaign_file(cls, suffix=""):
        return osp.splitext(inspect.getfile(cls))[0] + suffix + '.yaml'
