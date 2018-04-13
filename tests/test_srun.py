import json
import os
import os.path as osp
import shutil
import stat
import tempfile
import textwrap
import unittest

from hpcbench.driver import (
    CampaignDriver,
)
from . import DriverTestCase


class TestSrun(DriverTestCase, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.SLURM_ALLOC_NODE = 'n3'
        cls.SLURM_UT_DIR = tempfile.mkdtemp(prefix='hpcbench-ut')
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
        os.environ['PATH'] = cls.SLURM_UT_DIR + os.pathsep + os.environ['PATH']
        super(cls, cls).setUpClass()

    def test_srun_command(self):
        self.assertTrue(osp.isdir(TestSrun.CAMPAIGN_PATH))
        # simply ensure metrics have been generated
        aggregated_metrics_f = osp.join(
            TestSrun.CAMPAIGN_PATH,
            TestSrun.driver.node,
            '*',
            'test-slurm',
            'main',
            'metrics.json'
        )
        self.assertTrue(osp.isfile(aggregated_metrics_f),
                        "Not file: " + aggregated_metrics_f)
        with open(aggregated_metrics_f) as istr:
            data = json.load(istr)
        self.assertEqual(data[0]['metrics']['performance'], 42.0)

    def test_srun_dependent(self):
        yaml_file = 'test_srun_dependent.yaml'
        campaign_file = osp.join(osp.dirname(__file__), yaml_file)
        output_dir = osp.join(self.TEST_DIR, 'test_srun_uc2')
        node = 'n3'
        driver = CampaignDriver(campaign_file=campaign_file,
                                node=node,
                                srun='uc2',
                                output_dir=output_dir)
        driver()
        aggregated_metrics_f = osp.join(
            output_dir,
            node,
            'uc2',
            'test-slurm2',
            'main',
            'metrics.json'
        )
        self.assertTrue(osp.isfile(aggregated_metrics_f),
                        "Not file: " + aggregated_metrics_f)
        with open(aggregated_metrics_f) as istr:
            data = json.load(istr)
        self.assertEqual(data[0]['metrics']['performance'], 42.0)

    @classmethod
    def tearDownClass(cls):
        length = len(cls.SLURM_UT_DIR + os.pathsep)
        os.environ['PATH'] = os.environ['PATH'][length:]
        shutil.rmtree(cls.SLURM_UT_DIR)
        super(cls, cls).tearDownClass()
