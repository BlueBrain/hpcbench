from io import StringIO
import json
import os
import os.path as osp
import shutil
import stat
import tempfile
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
    CONSTRAINT = '#SBATCH --constraint=skylake\n'

    @classmethod
    def setUpClass(cls):
        cls.SLURM_ALLOC_NODE = 'n3'
        cls.SLURM_UT_DIR = tempfile.mkdtemp(prefix='hpcbench-ut')
        sbatch_ut = osp.join(cls.SLURM_UT_DIR, 'sbatch-ut')
        with open(sbatch_ut, 'w') as ostr:
            ostr.write(textwrap.dedent("""\
                #!/bin/bash -e
                # output a job id
                while [[ "$1" == -* ]] ; do shift ; done
                export SLURMD_NODENAME={node}
                source $@ > slurm-12345.out 2>&1
                echo "12345"
                """.format(node=cls.SLURM_ALLOC_NODE)))
        st = os.stat(sbatch_ut)
        os.chmod(sbatch_ut, st.st_mode | stat.S_IEXEC)
        srun_ut = osp.join(cls.SLURM_UT_DIR, 'srun-ut')
        with open(srun_ut, 'w') as ostr:
            ostr.write(textwrap.dedent("""\
                #!/bin/bash -e
                # skip options
                while [[ "$1" == -* ]] ; do shift ; done
                exec $@
                """))
        st = os.stat(srun_ut)
        os.chmod(srun_ut, st.st_mode | stat.S_IEXEC)
        os.environ['PATH'] = (cls.SLURM_UT_DIR + os.pathsep +
                              os.environ['PATH'])
        super(cls, cls).setUpClass()

    def test_sbatch_command(self):
        self.assertTrue(osp.isdir(TestSlurm.CAMPAIGN_PATH))
        for tag in ['uc2']:
            hpcb_f = osp.join(
                TestSlurm.CAMPAIGN_PATH,
                TestSlurm.driver.node,
                tag, 'hpcbench.yaml'
            )
            with open(hpcb_f) as f:
                hpcb = yaml.safe_load(f)
            self.assertEqual(hpcb['jobid'], 12345)
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
            self.assertIn(TestSlurm.CONSTRAINT, sbatch_content)
            child_hpcbench_root = osp.join(
                TestSlurm.CAMPAIGN_PATH,
                TestSlurm.driver.node,
                tag, hpcb['children'][0])
            child_metrics_f = osp.join(
                child_hpcbench_root,
                self.SLURM_ALLOC_NODE,
                tag,
                'test-slurm2',
                'standard',
                'metrics.json'
            )
            self.assertTrue(osp.isfile(child_metrics_f),
                            "Not file: " + child_metrics_f)
            with open(child_metrics_f) as istr:
                data = json.load(istr)
            self.assertEqual(data[0]['metrics']['dummy'], 42.0)

    @classmethod
    def tearDownClass(cls):
        length = len(cls.SLURM_UT_DIR + os.pathsep)
        os.environ['PATH'] = os.environ['PATH'][length:]
        shutil.rmtree(cls.SLURM_UT_DIR)
        super(cls, cls).tearDownClass()


class TestSbatchTemplate(unittest.TestCase):
    SBATCH_PRELUDE = textwrap.dedent("""\
        #!/bin/bash
        #SBATCH --account={value}
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
