import inspect
import os.path as osp
import shutil
import tempfile

from hpcbench.cli import bensh
from hpcbench.toolbox.contextlib_ext import pushd


class DriverTestCase(object):
    @classmethod
    def get_campaign_file(cls):
        return osp.splitext(inspect.getfile(cls))[0] + '.yaml'

    @classmethod
    def setUpClass(cls):
        cls.TEST_DIR = tempfile.mkdtemp(prefix='hpcbench-ut')
        with pushd(cls.TEST_DIR):
            cls.driver = bensh.main(cls.get_campaign_file())
        cls.CAMPAIGN_PATH = osp.join(cls.TEST_DIR,
                                     cls.driver.campaign_path)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.TEST_DIR)
