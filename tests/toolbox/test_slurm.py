import os.path as osp
import unittest

import mock

from hpcbench.toolbox.slurm import SlurmCluster


class TestSlurm(unittest.TestCase):
    SINFO_OUTPUT_FILE = osp.join(osp.dirname(__file__), 'sinfo-mock.txt')

    @mock.patch('subprocess.check_output')
    def test_introspect_cluster(self, co_mock):
        with open(TestSlurm.SINFO_OUTPUT_FILE) as istr:
            co_mock.return_value = istr.read().encode()
        c = SlurmCluster()
        self.assertEqual(108, len(c.nodes))
        self.assertEqual(
            {'partition_1', 'partition_2', 'partition_3'}, set(c.partitions.keys())
        )
