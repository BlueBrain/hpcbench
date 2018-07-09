import os.path as osp
import unittest

import mock

from hpcbench.toolbox.slurm import SlurmCluster


class TestSlurm(unittest.TestCase):
    SINFO_OUTPUT_FILE = osp.join(osp.dirname(__file__), 'sinfo-mock.txt')
    SINFO_RESERVATIONS_FILE = osp.join(
        osp.dirname(__file__), 'sinfo-reservations-mock.txt'
    )

    @mock.patch('subprocess.check_output')
    def test_introspect_cluster(self, co_mock):
        with open(TestSlurm.SINFO_OUTPUT_FILE) as istr:
            co_mock.return_value = istr.read().encode()
        c = SlurmCluster()
        self.assertEqual(108, len(c.nodes))
        self.assertEqual(
            {'partition_1', 'partition_2', 'partition_3'}, set(c.partitions.keys())
        )

    @mock.patch('subprocess.check_output')
    def test_reservations(self, co_mock):
        with open(TestSlurm.SINFO_RESERVATIONS_FILE) as istr:
            co_mock.return_value = istr.read().encode()
        rsvs = SlurmCluster.reservations()
        self.assertEqual(2, len(rsvs))
        for foo in [SlurmCluster.reservation('foo'), rsvs['foo']]:
            self.assertEqual(foo.name, 'foo')
            self.assertTrue(foo.active)
            self.assertEqual(11, len(foo.nodes))
        bar = rsvs['bar']
        self.assertEqual(bar.name, 'bar')
        self.assertFalse(bar.active)
        with self.assertRaises(KeyError):
            SlurmCluster.reservation('?')
