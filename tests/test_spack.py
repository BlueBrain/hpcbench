import mock
import os
import os.path as osp
import shutil
import sys
import unittest

from hpcbench.campaign import ReportNode
from . import DriverTestCase


FOO_INSTALL_DIR = DriverTestCase.mkdtemp()


def co_mock(command):
    if command[1:4] == ['location', '--install-dir', 'foo@dev']:
        return (FOO_INSTALL_DIR + '\n').encode()
    raise NotImplementedError


def cc_mock(command):
    if command[1] == 'install' and command[-1] == 'foo@dev':
        return
    with open('/tmp/foo.txt', 'w') as ostr:
        ostr.write(repr(command))
    raise NotImplementedError


CO_MOCK = mock.Mock(side_effect=co_mock)
CC_MOCK = mock.Mock(side_effect=cc_mock)


class TestSpack(DriverTestCase, unittest.TestCase):
    @classmethod
    @mock.patch('hpcbench.toolbox.spack.check_output', new=CO_MOCK)
    @mock.patch('hpcbench.toolbox.spack.check_call', new=CC_MOCK)
    def setUpClass(cls):
        # prepare spack install directory of 'foo' package
        bin_dir = osp.join(FOO_INSTALL_DIR, 'bin')
        foo_python = osp.join(bin_dir, 'foo-python')
        os.mkdir(bin_dir)
        os.symlink(sys.executable, foo_python)
        super(cls, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(FOO_INSTALL_DIR)
        super(cls, cls).tearDownClass()

    def test(self):
        report = ReportNode(self.CAMPAIGN_PATH)
        data = list(report.collect('command_succeeded'))
        self.assertEqual(data, [True] * 3)
