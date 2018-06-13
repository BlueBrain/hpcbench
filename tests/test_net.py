import os
import os.path as osp
import unittest

from hpcbench.cli import bennett
from hpcbench.net import CampaignHolder
from hpcbench.toolbox.contextlib_ext import mkdtemp, pushd


def custom_ssh(self, *args):
    # get rid of node
    return list(args[1:])


def custom_scp(self, *args):
    src, dest = args
    if ':' in src:
        src = src.split(':', 1)[1]
    elif ':' in dest:
        dest = dest.split(':', 1)[1]
    if src != dest:
        return ['cp', src, dest]
    else:
        return ['true']


CampaignHolder.ssh = custom_ssh
CampaignHolder.scp = custom_scp


class TestNet(unittest.TestCase):
    @staticmethod
    def get_campaign_file():
        return osp.splitext(__file__)[0] + '.yaml'

    @unittest.skipIf(
        'TRAVIS_TAG' in os.environ, 'version to deploy is not available on PyPi yet'
    )
    def test_local(self):
        with mkdtemp() as temp_dir:
            with pushd(temp_dir):
                bennett.main(TestNet.get_campaign_file())
