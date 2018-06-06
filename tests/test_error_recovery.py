import unittest

from . import DriverTestCase


class TestErrorRecovery(DriverTestCase, unittest.TestCase):
    check_campaign_consistency = True

    def test_except(self):
        pass

    @classmethod
    def tearDownClass(cls):
        pass
