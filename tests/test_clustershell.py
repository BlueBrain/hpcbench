import unittest

from hpcbench.ext.ClusterShell.NodeSet import NodeSet


class TestCS(unittest.TestCase):
    def test_node_set(self):
        ns = NodeSet("foo[01-03]")
        self.assertEqual(
            set(ns),
            set(["foo01", "foo02", "foo03"])
        )
