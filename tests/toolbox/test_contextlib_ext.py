import os
import os.path as osp
import unittest

from hpcbench.toolbox.contextlib_ext import mkdtemp, pushd


class TestTempfile(unittest.TestCase):
    def test_pushd(self):
        cwd = osp.realpath(os.getcwd())
        with mkdtemp() as path, pushd(path) as ppath:
            path = osp.realpath(path)
            ppath = osp.realpath(ppath)
            cwd_in_context = osp.realpath(os.getcwd())
            self.assertNotEqual(cwd, cwd_in_context)
            self.assertEqual(path, ppath)
            self.assertEqual(path, cwd_in_context)
        self.assertEqual(cwd, osp.realpath(os.getcwd()))
        self.assertFalse(osp.isdir(path))

    def test_mkdtemp(self):
        with mkdtemp() as path:
            self.assertTrue(osp.isdir(path))
        self.assertFalse(osp.isdir(path))

    def test_mkdtemp_keep_file(self):
        with mkdtemp(remove=False) as path:
            self.assertTrue(osp.isdir(path))
        self.assertTrue(osp.isdir(path))


if __name__ == '__main__':
    unittest.main()
