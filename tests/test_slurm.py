import os.path as osp
import unittest

import yaml

from . import DriverTestCase


class TestSlurm(DriverTestCase, unittest.TestCase):

    def test_srun_command(self):
        self.assertTrue(osp.isdir(TestSlurm.CAMPAIGN_PATH))
        for tag in ['uc1', 'uc2']:
            hpcb_f = osp.join(
                TestSlurm.CAMPAIGN_PATH,
                TestSlurm.driver.node,
                tag, 'hpcbench.yaml'
            )
            with open(hpcb_f) as f:
                hpcb = yaml.safe_load(f)
            sbatch = hpcb['sbatch']
            sbatch_f = osp.join(
                TestSlurm.CAMPAIGN_PATH,
                TestSlurm.driver.node,
                tag, sbatch
            )
            self.assertTrue(osp.isfile(sbatch_f),
                            "Not file: " + sbatch_f)
            with open(sbatch_f) as f:
                sbatch_content = f.readlines()
            self.assertFalse(sbatch_content[-1].find(tag) == -1)
