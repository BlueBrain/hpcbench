import json
import os.path as osp
import unittest

from . import DriverTestCase


class DefaultMetricsTest(DriverTestCase, unittest.TestCase):
    def test(self):
        aggregated_metrics_f = osp.join(
            DefaultMetricsTest.CAMPAIGN_PATH,
            DefaultMetricsTest.driver.node,
            '*',
            'test_default_metrics',
            'main',
            'metrics.json'
        )
        with open(aggregated_metrics_f) as istr:
            resp = json.load(istr)
            run0 = resp[0]
            metrics = run0['metrics']
            self.assertEqual(metrics['foo'], 'bar')
            self.assertEqual(metrics['bar'], 42)
