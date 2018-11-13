from __future__ import print_function

import contextlib
import glob
import os
import os.path as osp
import re
import stat
import unittest

from cached_property import cached_property
import mock
import six
import yaml

from hpcbench.api import Benchmark
from hpcbench.campaign import from_file, ReportNode
from hpcbench.toolbox.environment_modules import Module
from . import DriverTestCase, NullExtractor


def popen_module_load(command, **kwargs):
    """Override Popen for every commands starting with
        modulecmd python load

        >>> p = Popen(['modulecmd', 'python', 'load', 'foo/bar'])
        >>> p.communicate()
        ('os.environ["foo_bar"]="loaded"', '')
        >>>
    """
    if command[0:3] != [Module.MODULECMD, 'python', 'load']:
        raise Exception("Mock used outside desired scope")
    module = command[3]
    env_var = EnvBenchmark.MODULE_TO_VAR_RE.sub('_', module)
    python_code = 'os.environ["{}"] = "loaded"'.format(env_var)

    class _popen:
        def communicate(self):
            return python_code, None

    return _popen()


POPEN_MOCK = mock.Mock(side_effect=popen_module_load)


class EnvBenchmark(Benchmark):
    """only for testing purpose"""

    MODULE_TO_VAR_RE = re.compile('[^0-9a-zA-Z]+')

    name = "environment"

    def __init__(self):
        super(EnvBenchmark, self).__init__(attributes=dict(environment={}, modules=[]))

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
            modules=self.modules,
            metas=dict(foo='foo'),
        )

    def pre_execute(self, execution, context):
        del context  # unused
        self._dump_environment(execution, 'pre_execute.yaml')

    def post_execute(self, execution, context):
        del context  # unused
        self._dump_environment(execution, 'post_execute.yaml')

    def _dump_environment(self, execution, file):
        """Write in a YAML file a dict containing sub-set
        of `os.environ`. Only the following variables are
        writen:
        * those in execution['environment']
        * based on execution['modules'], for instance if module
          `foo/bar` is specified in execution, then
          expect `foo_bar` to be in `os.environ`
        """
        env_vars = []
        for module in execution.get('modules') or []:
            env_vars.append(self.MODULE_TO_VAR_RE.sub('_', module))
        for var in execution.get('environment') or {}:
            env_vars.append(var)
        with open(file, 'w') as ostr:
            yaml.dump(dict((name, os.environ.get(name)) for name in env_vars), ostr)


class TestEnvironment(DriverTestCase, unittest.TestCase):
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
        print('if type module >/dev/null; then', file=ostr)
        print('    module purge', file=ostr)
        for module in modules:
            print('    module load ' + module, file=ostr)
        if modules:
            print('else', file=ostr)
            for module in modules:
                print(
                    '    echo "Error: could not load module {}" >&2'.format(module),
                    file=ostr,
                )
        print('fi', file=ostr)
        for name, value in environment.items():
            value = six.moves.shlex_quote(value)
            print('export', name + "=" + value, file=ostr)
        with contextlib.closing(ostr):
            return ostr.getvalue()

    @classmethod
    @mock.patch('hpcbench.toolbox.environment_modules.Popen', new=POPEN_MOCK)
    def setUpClass(cls):
        super(cls, cls).setUpClass()
        cls.driver.logger.error(cls.CAMPAIGN_PATH)

    @cached_property
    def expected_env(self):
        return from_file(self.get_campaign_file())['expected_env']

    @cached_property
    def errors(self):
        return set(from_file(self.get_campaign_file())['errors'])

    def test(self):
        report = ReportNode(self.CAMPAIGN_PATH)
        keys = ('modules', 'environment', 'metas')
        expected_tests = 14
        tests = 0
        for path, env in report.collect(*keys, with_path=True):
            context = report.path_context(path)
            self._check_campaign_report(context, env)
            self._check_shell_script(context)
            self._check_benchmark_hooks_environment(context)
            self._check_metas(env)
            self.assertNotIn(context.benchmark, self.errors)
            tests += 1
        self.assertEqual(tests, expected_tests)

    def _check_metas(self, env):
        self.assertEqual(env[2], dict(foo='foo', bar='pika'))

    def _check_campaign_report(self, context, env):
        """Verify environment and modules specified in report"""
        self.assertIn(context.benchmark, self.expected_env)
        expected_env = self.expected_env[context.benchmark]
        self.assertEqual(expected_env['modules'], env[0])
        self.assertEqual(expected_env['environment'], env[1])

    def _check_shell_script(self, context):
        """Verify generated shell-script prelude"""
        shell_script = glob.glob(osp.join(context.path, '*.sh'))[0]
        mode = os.stat(shell_script).st_mode
        expected_mode = stat.S_IEXEC | stat.S_IRGRP | stat.S_IRUSR
        self.assertEqual(mode & expected_mode, expected_mode)
        environment = self.expected_env[context.benchmark]
        with open(shell_script) as istr:
            prelude = self._shell_prelude(**environment)
            script = istr.read()
            if not script.startswith(prelude):
                print(script)
                print(prelude)
                self.assertTrue(False)

    def _check_benchmark_hooks_environment(self, context):
        """Check hook file written by benchmark
        `pre_execute` and `post_execute` member methods"""
        environment = self.expected_env[context.benchmark]
        for hook_file_prefix in ['pre', 'post']:
            hook_file = osp.join(context.path, hook_file_prefix + '_execute.yaml')
            with open(hook_file) as istr:
                hook_env = yaml.safe_load(istr)
            for var, value in environment['environment'].items():
                self.assertEqual(hook_env[var], value)
                hook_env.pop(var)
            for module in environment['modules']:
                var = EnvBenchmark.MODULE_TO_VAR_RE.sub('_', module)
                self.assertEqual(hook_env[var], 'loaded')
