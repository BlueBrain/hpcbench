from io import StringIO
import os.path as osp
import textwrap
import unittest

import yaml

from hpcbench.driver import (
    CampaignDriver,
    SbatchDriver,
    SlurmDriver,
)
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


class TestSbatchTemplate(unittest.TestCase):
    SBATCH_PRELUDE = textwrap.dedent("""\
        #!/bin/bash
        #SBATCH account={value}
        module load nix/spack
        spack load nix
    """)

    def _test_template(self, yaml_file, uc, expected_arg_value,
                       assert_method=None):
        yaml_file = osp.join(osp.dirname(__file__), yaml_file)
        sbatch_driver = SbatchDriver(
            SlurmDriver(
                CampaignDriver(campaign_file=yaml_file)
            ),
            uc
        )
        sbatch = StringIO()
        sbatch_driver._create_sbatch(sbatch)
        expected = TestSbatchTemplate.SBATCH_PRELUDE.format(
            value=expected_arg_value
        )
        assert_method = assert_method or self.assertTrue
        assert_method(sbatch.getvalue().startswith(expected))
        sbatch.close()

    def test_embedded_sbatch_template(self):
        """Globaly override sbatch template"""
        self._test_template(
            'test_slurm_embedded_sbatch_template.yaml',
            'uc1',
            42
        )

    def test_sbatch_template_per_uc(self):
        """Override sbatch template per UC"""
        self._test_template(
            'test_slurm_sbatch_template_per_uc.yaml',
            'uc1',
            42
        )

        # fallback on default hpcbench sbatch template
        self._test_template(
            'test_slurm_sbatch_template_per_uc.yaml',
            'uc2',
            42,
            assert_method=self.assertFalse
        )

    def test_default_sbatch_template_per_uc(self):
        """Override sbatch template per UC with default value"""
        self._test_template(
            'test_slurm_default_sbatch_template_per_uc.yaml',
            'uc1',
            42
        )

        # fallback on default template in YAML
        self._test_template(
            'test_slurm_default_sbatch_template_per_uc.yaml',
            'unknown-uc',
            'forced'
        )
