from __future__ import print_function

import contextlib
import glob
import os.path as osp
import unittest

from cached_property import cached_property
import six
import yaml

from hpcbench.api import Benchmark
from hpcbench.campaign import ReportNode
from . import DriverTestCase, NullExtractor


class EnvBenchmark(Benchmark):
    name = "environment"
    description = "only for testing purpose"

    def __init__(self):
        super(EnvBenchmark, self).__init__(
            attributes=dict(
                environment={},
                modules=[]
            )
        )

    @property
    def metric_required(self):
        return False

    @property
    def metrics_extractors(self):
        return NullExtractor()

    @property
    def environment(self):
        return self.attributes['environment']

    @property
    def modules(self):
        return self.attributes['modules']

    def execution_matrix(self, context):
        yield dict(
            category='ut',
            command=['true'],
            environment=self.environment,
            modules=self.modules
        )


class TestEnvironment(DriverTestCase, unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        pass

    def _shell_prelude(self, environment=None, modules=None):
        """Rebuild shell-script prelude to ensure that
        both environment variables and modules are properly
        set.
        """
        environment = environment or {}
        modules = modules or []

        ostr = six.StringIO()
        print('#!/bin/sh', file=ostr)
        print(file=ostr)
        print('module purge', file=ostr)
        for module in modules:
            print('module load ' + module, file=ostr)
        for name, value in environment.items():
            print('export', name + '=' + value, file=ostr)
        with contextlib.closing(ostr):
            return ostr.getvalue()

    @cached_property
    def expected_results(self):
        with open(self.get_campaign_file()) as istr:
            return yaml.load(istr)['expected_results']

    def test(self):
        report = ReportNode(self.CAMPAIGN_PATH)
        for path, results in report.collect('modules', 'environment',
                                            with_path=True):
            context = report.path_context(path)
            self.assertIn(context.benchmark, self.expected_results)
            expected_results = self.expected_results[context.benchmark]
            self.assertEqual(
                expected_results['modules'],
                results[0],
            )
            self.assertEqual(
                expected_results['environment'],
                results[1],
            )
            shell_script = glob.glob(osp.join(path, '*.sh'))[0]
            with open(shell_script) as istr:
                prelude = self._shell_prelude(**expected_results)
                script = istr.read()
                self.assertTrue(script.startswith(prelude))
