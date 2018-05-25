import datetime
import os
import os.path as osp
import shutil
import tempfile
import unittest

import mock
import six
import yaml

from hpcbench.campaign import (
    ReportNode,
    YAML_REPORT_FILE,
)
from hpcbench.cli.benwait import (
    main as benwait,
    wait_for_completion,
)


class sacct:
    """Helper class to create mock objets in unit-tests below"""
    SACCT_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'

    def __init__(self):
        self._returned_values = []

    def r(self, end=None):
        """Append a sacct response to the Mock object
        informing that the job is still running
        """
        if end:
            assert isinstance(end, datetime.datetime)
            end = end.strftime(sacct.SACCT_DATE_FORMAT)
        else:
            end = 'Unknown'
        self._returned_values.append(end.encode())
        return self

    def cd(self):
        """Append a sacct response to the Mock object
        informing that the job completed
        """
        return self.r(end=datetime.datetime.now())

    def mock(self):
        """Build the mock object"""
        return mock.patch(
            "subprocess.check_output",
            side_effect=self._returned_values
        )


class TestBenWait(unittest.TestCase):
    SACCT_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'

    @classmethod
    def setUpClass(cls):
        cls.REPORT = ReportNode(cls._create_fake_campaign())
        os.environ['SACCT'] = 'true'

    @classmethod
    def tearDownClass(cls):
        os.environ.pop('SACCT')
        shutil.rmtree(cls.REPORT.path)

    @classmethod
    def _create_fake_campaign(cls):
        campaign = tempfile.mkdtemp()
        with open(osp.join(campaign, YAML_REPORT_FILE), 'w') as ostr:
            yaml.dump(dict(children=['sbatch1', 'sbatch2']), ostr)
        for jobid in range(1, 3):
            path = osp.join(campaign, 'sbatch' + str(jobid))
            os.mkdir(path)
            with open(osp.join(path, YAML_REPORT_FILE), 'w') as ostr:
                yaml.dump(dict(jobid=jobid), ostr)
        return campaign

    def test_all_completed(self):
        """both sbatch jobs terminated"""
        with sacct().cd().cd().mock() as mock:
            six.assertCountEqual(
                self,
                wait_for_completion(self.REPORT),
                [1, 2]
            )
            self.assertEqual(mock.call_count, 2)

    def test_wait_one(self):
        """wait for a job once"""
        scenarii = [
            sacct().r().cd().cd().mock(),  # wait once for the first job
            sacct().cd().r().cd().mock(),  # wait once for the second job
        ]
        for scenario in scenarii:
            with scenario as mock:
                six.assertCountEqual(
                    self,
                    wait_for_completion(self.REPORT, interval=0.5),
                    [1, 2]
                )
                self.assertEqual(mock.call_count, 3)

    def test_benwait_executable(self):
        """Test ben-wait entry-point"""
        with sacct().r().cd().r().cd().mock() as mock:
            benwait(["-n", "0.5", self.REPORT.path])
        self.assertEqual(mock.call_count, 4)
