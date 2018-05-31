from io import StringIO
import os
import os.path as osp
import shutil
import stat
import subprocess
import tempfile
import textwrap
import unittest

import mock
from mock import Mock

from hpcbench.campaign import ReportNode
from hpcbench.driver import (
    CampaignDriver,
    SbatchDriver,
    SlurmDriver,
)
from hpcbench.toolbox.edsl import kwargsql
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
                echo "Starting job"
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
                exec $@ >slurm-localhost-1.stdout 2>slurm-localhost-1.stderr
                """))
        st = os.stat(srun_ut)
        os.chmod(srun_ut, st.st_mode | stat.S_IEXEC)
        os.environ['PATH'] = (cls.SLURM_UT_DIR + os.pathsep +
                              os.environ['PATH'])
        super(cls, cls).setUpClass()

    def test_sbatch_command(self):
        self.assertTrue(osp.isdir(TestSlurm.CAMPAIGN_PATH))
        for tag in ['uc2']:
            root = ReportNode(TestSlurm.CAMPAIGN_PATH)
            for path, jobid in root.collect('jobid', with_path=True):
                if path.endswith(tag):
                    break
            self.assertEqual(jobid, 12345)
            slurm_report = ReportNode(path)
            sbatch_f = osp.join(path, slurm_report['sbatch'])
            self.assertTrue(osp.isfile(sbatch_f),
                            "Not file: " + sbatch_f)
            with open(sbatch_f) as f:
                sbatch_content = f.readlines()
            self.assertFalse(sbatch_content[-1].find(tag) == -1)
            self.assertIn(TestSlurm.CONSTRAINT, sbatch_content)
            data = slurm_report.collect_one('metrics')
            dummy = kwargsql.get(data, '0__measurement__dummy')
            self.assertEqual(dummy, 42.0)

    @classmethod
    def tearDownClass(cls):
        length = len(cls.SLURM_UT_DIR + os.pathsep)
        os.environ['PATH'] = os.environ['PATH'][length:]
        shutil.rmtree(cls.SLURM_UT_DIR)
        super(cls, cls).tearDownClass()


class TestSbatchFail(DriverTestCase, unittest.TestCase):

    check_output = Mock()
    check_output.side_effect = subprocess.CalledProcessError(
        42, 'sbatch-ut', output="Error")
    find_exec = Mock()
    find_exec.return_value = 'sbatch-ut'

    @classmethod
    @mock.patch('subprocess.check_output', check_output)
    @mock.patch('hpcbench.driver.find_executable', find_exec)
    def setUpClass(cls):
        super(cls, cls).setUpClass()

    def test_sbatch_fail(self):
        report = ReportNode(TestSbatchFail.CAMPAIGN_PATH)
        self.assertEqual(list(report.collect('jobid')), [-1] * 2)


class TestSbatchTemplate(unittest.TestCase):
    SBATCH_PRELUDE = textwrap.dedent("""\
        #!/bin/bash
        {sbatch_args}
        module load nix/spack
        spack load nix
    """)

    def _test_template(self, yaml_file, uc, expected_sbatch_opts,
                       assert_method=None):
        yaml_file = osp.join(osp.dirname(__file__), yaml_file)
        sbatch_driver = SbatchDriver(
            SlurmDriver(CampaignDriver(yaml_file)),
            uc
        )
        sbatch = StringIO()
        sbatch_driver._create_sbatch(sbatch)
        expected = TestSbatchTemplate.SBATCH_PRELUDE.format(
            sbatch_args=expected_sbatch_opts
        )
        assert_method = assert_method or self.assertTrue
        assert_method(sbatch.getvalue().startswith(expected))
        sbatch.close()

    def test_embedded_sbatch_template(self):
        """Globally override sbatch template"""
        sbatch_str = "\n".join([
            "#SBATCH --account=42",
            "#SBATCH --nodelist=n1,n2",
            "#SBATCH --nodes=2",
        ])
        self._test_template(
            'test_slurm_embedded_sbatch_template.yaml',
            'uc1',
            sbatch_str
        )

    def test_sbatch_template_per_uc(self):
        """Override sbatch template per UC"""
        sbatch_str = "\n".join([
            "#SBATCH --account=42",
            "#SBATCH --nodelist=n1,n2",
            "#SBATCH --nodes=2",
        ])
        self._test_template(
            'test_slurm_sbatch_template_per_uc.yaml',
            'uc1',
            sbatch_str
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
        sbatch_str = "\n".join([
            "#SBATCH --account=43",
            "#SBATCH --nodelist=n1,n2",
            "#SBATCH --nodes=2",
        ])

        self._test_template(
            'test_slurm_default_sbatch_template_per_uc.yaml',
            'uc1',
            sbatch_str
        )
        sbatch_str = "\n".join([
            "#SBATCH --account=42",
            "#SBATCH --nodelist=n3,n4",
            "#SBATCH --nodes=2",
        ])

        # fallback on default template in YAML
        self._test_template(
            'test_slurm_default_sbatch_template_per_uc.yaml',
            'uc2',
            sbatch_str
        )

    def test_per_tag_sbatch_args(self):
        """Override sbatch arguments in a benchmark tag"""
        sbatch_str = "\n".join([
            "#SBATCH --account=43",
            "#SBATCH --nodelist=n1,n2",
            "#SBATCH --nodes=2",
        ])
        self._test_template(
            'test_slurm_per_tag_sbatch_args.yaml',
            'uc1',
            sbatch_str
        )
