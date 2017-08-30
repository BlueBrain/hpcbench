import os
import unittest

from hpcbench.toolbox.process import find_executable


class TestFindExecutable(unittest.TestCase):
    def test_process_find(self):
        self.assertIsNotNone(find_executable('ls'))
        self.assertIsNotNone(find_executable('ellesse', ['elaisse', 'ls']))
        os.environ['ELLESSE'] = '/usr/bin/elesse'
        try:
            self.assertEqual(find_executable('ellesse'), '/usr/bin/elesse')
            self.assertIsNone(find_executable('elaisse', ['elesse'],
                              required=False))
        finally:
            os.environ.pop('ELLESSE')

    def test_process_not_found(self):
        self.assertIsNone(find_executable('ellesse', required=False))
        with self.assertRaises(NameError):
            find_executable('ellesse')
            find_executable('ellesse', ['elaisse'])
