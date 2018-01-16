import json
import os.path as osp
import socket
import unittest

from . import DriverTestCase


class CwdTest(DriverTestCase, unittest.TestCase):
    def test(self):
        aggregated_metrics_f = osp.join(
            CwdTest.CAMPAIGN_PATH,
            CwdTest.driver.node,
            '*',
            'test_cwd',
            'main',
            'metrics.json'
        )
        with open(aggregated_metrics_f) as istr:
            resp = json.load(istr)
            run0 = resp[0]
            metrics = run0['metrics']
            self.assertEqual(
                metrics['path'],
                '/tmp/hpcbench-ut/test_cwd/{node}/{tag}'.format(
                    node=socket.gethostname(),
                    tag='*'
                )
            )
