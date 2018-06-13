import os.path as osp
import unittest

from . import DriverTestCase


class PrunedDirTest(DriverTestCase, unittest.TestCase):
    def test(self):
        uc1path = osp.join(
            PrunedDirTest.CAMPAIGN_PATH, PrunedDirTest.driver.node, 'uc1'
        )
        uc2path = osp.join(
            PrunedDirTest.CAMPAIGN_PATH, PrunedDirTest.driver.node, 'uc2'
        )
        self.assertTrue(osp.exists(uc1path) and not osp.exists(uc2path))
