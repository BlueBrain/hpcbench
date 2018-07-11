"""
Test --campaign-path-fd option of ben-sh executable.
"""
import os
import os.path as osp
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest


class TestCampaignPathFd(unittest.TestCase):
    CAMPAIGN_CONTENT = textwrap.dedent(
        '''\
        network:
          nodes:
            - localhost
    '''
    )

    @classmethod
    def setUpClass(cls):
        fd, cls.CAMPAIGN = tempfile.mkstemp(suffix='.yaml')
        os.write(fd, cls.CAMPAIGN_CONTENT.encode())
        os.close(fd)

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.CAMPAIGN)

    def bensh(self, fd=None):
        bensh = osp.join(osp.dirname(sys.executable), 'ben-sh')
        command = [bensh]
        if fd:
            command += ['--campaign-path-fd', str(fd)]
        command.append(self.CAMPAIGN)
        return subprocess.check_output(command, close_fds=False)

    def test_default(self):
        path = self.bensh().splitlines()[-1]
        shutil.rmtree(path)

    def test_fd_3(self):
        fd, path = tempfile.mkstemp()
        # dirty workaround before mkstemp() returns non-inheritable fd
        os.close(fd)
        fd = os.open(path, os.O_RDWR | os.O_CREAT)
        # ---
        if hasattr(os, 'set_inheritable'):
            os.set_inheritable(fd, True)
        self.bensh(fd)
        os.close(fd)
        # 'path' file must have absolute path to campaign
        with open(path) as istr:
            content = istr.read()
        os.remove(path)
        lines = content.splitlines(True)
        self.assertEqual(1, len(lines))
        campaign_path = lines[0][:-1]
        self.assertTrue(osp.isdir(campaign_path))
        self.assertTrue(osp.isabs(campaign_path))
        shutil.rmtree(campaign_path)
