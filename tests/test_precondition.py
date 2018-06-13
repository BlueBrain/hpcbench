import os
import os.path as osp
import unittest

from . import DriverTestCase


class TestPrecondition(DriverTestCase, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ['ENABLE_TEST01'] = 'true'
        super(cls, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        os.environ.pop('ENABLE_TEST01', None)
        super(cls, cls).tearDownClass()

    def test(self):
        self.assertTrue(osp.isfile(TestPrecondition.metrics_file('test01')))
        self.assertFalse(osp.isfile(TestPrecondition.metrics_file('test02')))
        self.assertTrue(osp.isfile(TestPrecondition.metrics_file('test03')))
        self.assertTrue(osp.isfile(TestPrecondition.metrics_file('test04')))

    @classmethod
    def metrics_file(cls, benchmark):
        return osp.join(
            cls.CAMPAIGN_PATH, cls.driver.node, '*', benchmark, 'main', 'metrics.json'
        )
