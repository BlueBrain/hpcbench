import os
import os.path as osp
import unittest


from . import DriverTestCase


class MultipleAttempts(DriverTestCase, unittest.TestCase):
    def test(self):
        self.assertEqual(self._nb_runs('test01'), 2)
        self.assertEqual(self._nb_runs('test02'), 2)
        self.assertEqual(self._nb_runs('test03'), 2)

    def _nb_runs(self, test_name):
        cat_dir = osp.join(
            MultipleAttempts.CAMPAIGN_PATH,
            MultipleAttempts.driver.node,
            '*',
            test_name,
            'main',
        )
        test_dir = self._dirs(cat_dir)
        self.assertEqual(len(test_dir), 1)
        return len(self._dirs(test_dir[0]))

    def _dirs(self, path):
        return [
            osp.join(path, dir_)
            for dir_ in os.listdir(path)
            if osp.isdir(osp.join(path, dir_))
        ]
