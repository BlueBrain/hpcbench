import json
import os
import os.path as osp
import shutil
import stat
import tempfile
import textwrap
import unittest

from . import DriverTestCase


class TestSrun(DriverTestCase, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.SRUN_UT_DIR = tempfile.mkdtemp(prefix='hpcbench-ut')
        srun_ut = osp.join(cls.SRUN_UT_DIR, 'srun-ut')
        with open(srun_ut, 'w') as ostr:
            ostr.write(textwrap.dedent("""\
                #!/bin/bash -e
                # skip options
                while [[ "$1" == -* ]] ; do shift ; done
                exec $@
                """))
            st = os.stat(srun_ut)
            os.chmod(srun_ut, st.st_mode | stat.S_IEXEC)
        os.environ['PATH'] = cls.SRUN_UT_DIR + os.pathsep + os.environ['PATH']
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

    @classmethod
    def tearDownClass(cls):
        length = len(cls.SRUN_UT_DIR + os.pathsep)
        os.environ['PATH'] = os.environ['PATH'][length:]
        shutil.rmtree(cls.SRUN_UT_DIR)
        super(cls, cls).tearDownClass()
