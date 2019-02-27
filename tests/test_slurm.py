from io import StringIO
import os
import os.path as osp
import shutil
import stat
import subprocess
import textwrap
import unittest

import mock
from mock import Mock

from hpcbench.campaign import from_file, ReportNode
from hpcbench.driver import CampaignDriver
from hpcbench.driver.slurm import SlurmDriver, SbatchDriver
from hpcbench.toolbox.edsl import kwargsql
from . import DriverTestCase
from . test_spack import CO_MOCK, CC_MOCK


class TestSlurm(DriverTestCase, unittest.TestCase):
    CONSTRAINT = '#SBATCH --constraint=skylake\n'

    @classmethod
    @mock.patch('hpcbench.toolbox.spack.check_output', new=CO_MOCK)
    @mock.patch('hpcbench.toolbox.spack.check_call', new=CC_MOCK)
    def setUpClass(cls):
        cls.SLURM_ALLOC_NODE = 'n3'
        cls.SLURM_UT_DIR = cls.mkdtemp()
        sbatch_ut = osp.join(cls.SLURM_UT_DIR, 'sbatch-ut')
        with open(sbatch_ut, 'w') as ostr:
            ostr.write(
                textwrap.dedent(
                    """\
                #!/bin/bash -e
                # output a job id
                while [[ "$1" == -* ]] ; do shift ; done
                export SLURMD_NODENAME={node}
                echo "Starting job"
                source $@ > slurm-12345.out 2>&1
                echo "12345"
                """.format(
                        node=cls.SLURM_ALLOC_NODE
                    )
                )
            )
        st = os.stat(sbatch_ut)
        os.chmod(sbatch_ut, st.st_mode | stat.S_IEXEC)
        srun_ut = osp.join(cls.SLURM_UT_DIR, 'srun-ut')
        with open(srun_ut, 'w') as ostr:
            ostr.write(
                textwrap.dedent(
                    """\
                #!/bin/bash -e
                # skip options
                while [[ "$1" == -* ]] ; do shift ; done
                exec $@ >slurm-localhost-1.stdout 2>slurm-localhost-1.stderr
                """
                )
            )
        st = os.stat(srun_ut)
        os.chmod(srun_ut, st.st_mode | stat.S_IEXEC)
        os.environ['PATH'] = cls.SLURM_UT_DIR + os.pathsep + os.environ['PATH']
        super(TestSlurm, cls).setUpClass()

    def test_sbatch_command(self):
        self.assertTrue(osp.isdir(self.CAMPAIGN_PATH))
        for tag in ['uc2']:
            root = ReportNode(self.CAMPAIGN_PATH)
            for path, jobid in root.collect('jobid', with_path=True):
                if path.endswith(tag):
                    break
            self.assertEqual(jobid, 12345)
            slurm_report = ReportNode(path)
            sbatch_f = osp.join(path, slurm_report['sbatch'])
            self.assertTrue(osp.isfile(sbatch_f), "Not file: " + sbatch_f)
            with open(sbatch_f) as f:
                sbatch_content = f.readlines()
            self.assertFalse(sbatch_content[-1].find(tag) == -1)
            self.assertIn(self.CONSTRAINT, sbatch_content)
            if self.EXCLUDE_NODES:
                self.assertIn(
                    '--exclude-nodes=' + self.EXCLUDE_NODES + ' ', sbatch_content[-1]
                )
            data = slurm_report.collect_one('metrics')
            dummy = kwargsql.get(data, '0__measurement__dummy')
            self.assertEqual(dummy, 42.0)

    @classmethod
    def tearDownClass(cls):
        length = len(cls.SLURM_UT_DIR + os.pathsep)
        os.environ['PATH'] = os.environ['PATH'][length:]
        shutil.rmtree(cls.SLURM_UT_DIR)
        super(TestSlurm, cls).tearDownClass()


class TestExcludeNodeInSbatch(TestSlurm):
    EXCLUDE_NODES = "node01,node02"


class TestSbatchFail(DriverTestCase, unittest.TestCase):

    check_output = Mock()
    check_output.side_effect = subprocess.CalledProcessError(
        42, 'sbatch-ut', output="Error"
    )
    find_exec = Mock()
    find_exec.return_value = 'sbatch-ut'

    @classmethod
    @mock.patch('subprocess.check_output', check_output)
    @mock.patch('hpcbench.driver.slurm.find_executable', find_exec)
    def setUpClass(cls):
        super(cls, cls).setUpClass()

    def test_sbatch_fail(self):
        report = ReportNode(TestSbatchFail.CAMPAIGN_PATH)
        self.assertEqual(list(report.collect('jobid')), [-1] * 2)


class TestSbatchTemplate(unittest.TestCase):
    SBATCH_PRELUDE = textwrap.dedent(
        """\
        #!/bin/bash
        {sbatch_args}{spack_prelude}
    """
    )

    SPACK_PRELUDE = textwrap.dedent(
        """\

        module load nix/spack
        spack load nix"""
    )

    def _test_template(
        self, yaml_file, uc, expected_sbatch_opts, spack=True, assert_method=None
    ):
        yaml_file = osp.join(osp.dirname(__file__), yaml_file)
        sbatch_driver = SbatchDriver(SlurmDriver(CampaignDriver(yaml_file)), uc)
        sbatch = StringIO()
        sbatch_driver._create_sbatch(sbatch)
        expected = TestSbatchTemplate.SBATCH_PRELUDE.format(
            sbatch_args=expected_sbatch_opts,
            spack_prelude=self.SPACK_PRELUDE if spack else '',
        )
        assert_method = assert_method or self.assertTrue
        assert_method(sbatch.getvalue().startswith(expected))
        self._test_bensh_isabs(sbatch.getvalue())
        sbatch.close()

    def _test_bensh_isabs(self, template):
        cmd = template.splitlines()[-1]
        executable = cmd.split()[0]
        self.assertTrue(osp.isabs(executable))
        self.assertTrue(os.access(executable, os.X_OK))

    def test_sbatch_list_arg(self):
        sbatch_str = "\n".join(
            [
                "#SBATCH --job-name=test_slurm_sbatch_list_arg/uc1",
                "#SBATCH --mail-user=john.doe@acme.com",
                "#SBATCH --mail-user=johnny.begood@acme.com",
                "#SBATCH --nodelist=n1,n2",
                "#SBATCH --nodes=2",
            ]
        )
        self._test_template(
            'test_slurm_sbatch_list_arg.yaml', 'uc1', sbatch_str, spack=False
        )

    def test_embedded_sbatch_template(self):
        """Globally override sbatch template"""
        sbatch_str = "\n".join(
            [
                "#SBATCH --account=42",
                "#SBATCH --job-name=test_slurm_embedded_sbatch_template/uc1",
                "#SBATCH --nodelist=n1,n2",
                "#SBATCH --nodes=2",
            ]
        )
        self._test_template(
            'test_slurm_embedded_sbatch_template.yaml', 'uc1', sbatch_str
        )

    def test_sbatch_template_per_uc(self):
        """Override sbatch template per UC"""
        sbatch_str = "\n".join(
            [
                "#SBATCH --account=42",
                "#SBATCH --job-name=test_slurm_sbatch_template_per_uc/uc1",
                "#SBATCH --nodelist=n1,n2",
                "#SBATCH --nodes=2",
            ]
        )
        self._test_template('test_slurm_sbatch_template_per_uc.yaml', 'uc1', sbatch_str)

        # fallback on default hpcbench sbatch template
        self._test_template(
            'test_slurm_sbatch_template_per_uc.yaml',
            'uc2',
            42,
            assert_method=self.assertFalse,
        )

    def test_default_sbatch_template_per_uc(self):
        """Override sbatch template per UC with default value"""
        sbatch_str = "\n".join(
            [
                "#SBATCH --account=43",
                "#SBATCH --job-name=test_slurm_default_sbatch_template_per_uc/uc1",
                "#SBATCH --nodelist=n1,n2",
                "#SBATCH --nodes=2",
            ]
        )

        self._test_template(
            'test_slurm_default_sbatch_template_per_uc.yaml', 'uc1', sbatch_str
        )
        sbatch_str = "\n".join(
            [
                "#SBATCH --account=42",
                "#SBATCH --job-name=test_slurm_default_sbatch_template_per_uc/uc2",
                "#SBATCH --nodelist=n3,n4",
                "#SBATCH --nodes=2",
            ]
        )

        # fallback on default template in YAML
        self._test_template(
            'test_slurm_default_sbatch_template_per_uc.yaml', 'uc2', sbatch_str
        )

    def test_per_tag_sbatch_args(self):
        """Override sbatch arguments in a benchmark tag"""
        sbatch_str = "\n".join(
            [
                "#SBATCH --account=43",
                "#SBATCH --job-name=test_slurm_per_tag_sbatch_args/uc1",
                "#SBATCH --nodelist=n1,n2",
                "#SBATCH --nodes=2",
            ]
        )
        self._test_template('test_slurm_per_tag_sbatch_args.yaml', 'uc1', sbatch_str)


class TestSlurmCluster(unittest.TestCase):
    SINFO_OUTPUT_FILE = osp.join(osp.dirname(__file__), 'toolbox', 'sinfo-mock.txt')
    SINFO_RESERVATIONS_FILE = osp.join(
        osp.dirname(__file__), 'toolbox', 'sinfo-reservations-mock.txt'
    )

    @mock.patch('subprocess.check_output')
    def test_campaign_network(self, co_mock):
        with open(self.__class__.SINFO_OUTPUT_FILE) as istr:
            co_mock.return_value = istr.read().encode()
        campaign = osp.join(osp.dirname(__file__), 'test_slurm_cluster.yaml')
        campaign = from_file(campaign)
        self.assertEqual(35, len(campaign.network.nodes))
        self.assertEqual(
            {
                'partition_2_rack1',
                'uc1',
                'uc2',
                'rack1',
                'partition_1_rack1',
                'partition_3_rack1',
            },
            set(campaign.network.tags),
        )

    @mock.patch('subprocess.check_output')
    def test_reservation(self, co_mock):
        inputs = [
            self.__class__.SINFO_OUTPUT_FILE,
            self.__class__.SINFO_RESERVATIONS_FILE,
        ]
        outputs = []
        for file in inputs:
            with open(file) as istr:
                outputs.append(istr.read().encode())
        co_mock.side_effect = outputs
        campaign = osp.join(osp.dirname(__file__), 'test_slurm_cluster_rsv.yaml')
        campaign = from_file(campaign)
        self.assertEqual(11, len(campaign.network.nodes))
