import glob
import os.path as osp
from textwrap import dedent
import unittest

from hpcbench.campaign import ReportNode
from . import DriverTestCase


class TestEnvironment(DriverTestCase, unittest.TestCase):
    EXPECTED_SHELL_SCRIPT_PRELUDE = dedent("""\
        #!/bin/sh

        module purge
        module load foo/bar
        export foo=bar
        """)

    def test(self):
        report = ReportNode(self.CAMPAIGN_PATH)
        self.assertEqual(
            report.collect_one('environment'),
            dict(foo='bar')
        )
        path, modules = report.collect_one('modules', with_path=True)
        self.assertEqual(modules, ['foo/bar'])
        shell_script = glob.glob(osp.join(path, '*.sh'))[0]
        with open(shell_script) as istr:
            expected = self.EXPECTED_SHELL_SCRIPT_PRELUDE
            self.assertTrue(istr.read().startswith(expected))
