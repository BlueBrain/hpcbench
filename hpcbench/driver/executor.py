from __future__ import print_function

from collections import Mapping
import contextlib
import copy
import os
import shlex
import stat
import subprocess
import tempfile

from cached_property import cached_property

from .base import Enumerator, Leaf, Top, SEQUENCES, ConstraintTag, write_yaml_report

import six

from hpcbench import jinja_environment
from hpcbench.toolbox.contextlib_ext import pushd
from hpcbench.toolbox.environment_modules import Module
from hpcbench.toolbox.process import (
    build_slurm_arguments,
    find_executable,
    parse_constraint_in_args,
)

Top.__new__.__defaults__ = (None,) * len(Top._fields)


class ExecutionDriver(Leaf):
    """Abstract representation of a benchmark command execution
    (a benchmark is made of several commands)
    """

    name = 'local'

    def __init__(self, parent):
        super(ExecutionDriver, self).__init__(parent)
        self.benchmark = self.parent.benchmark
        self.execution = parent.execution
        self.command_expansion_vars = dict(process_count=1)
        self.config = parent.config
        self.exec_context = parent.exec_context

    @cached_property
    def _executor_script(self):
        """Create shell-script in charge of executing the benchmark
        and return its path.
        """
        fd, path = tempfile.mkstemp(suffix='.sh', dir=os.getcwd())
        os.close(fd)
        with open(path, 'w') as ostr:
            self._write_executor_script(ostr)
        mode = os.stat(path).st_mode
        os.chmod(path, mode | stat.S_IEXEC | stat.S_IRGRP | stat.S_IRUSR)
        return path

    @property
    def _jinja_executor_template(self):
        """:return Jinja template of the shell-script executor"""
        template = self.campaign.process.executor_template
        if template.startswith('#!'):
            return jinja_environment.from_string(template)
        else:
            return jinja_environment.get_template(template)

    def _write_executor_script(self, ostr):
        """Write shell script in charge of executing the command"""
        environment = self.execution.get('environment') or {}
        if not isinstance(environment, Mapping):
            msg = 'Expected mapping for environment but got '
            msg += str(type(environment))
            raise Exception(msg)
        escaped_environment = dict(
            (var, six.moves.shlex_quote(str(value)))
            for var, value in environment.items()
        )
        modules = self.execution.get('modules') or []
        properties = dict(
            command=self.command,
            cwd=os.getcwd(),
            modules=modules,
            environment=escaped_environment,
        )
        self._jinja_executor_template.stream(**properties).dump(ostr)

    @cached_property
    def command(self):
        """:return command to execute inside the generated shell-script"""
        exec_prefix = self.parent.parent.parent.config.get('exec_prefix', [])
        command = self.execution['command']
        if isinstance(command, SEQUENCES):
            command = [arg.format(**self.command_expansion_vars) for arg in command]
        else:
            command = command.format(**self.command_expansion_vars)
        if self.execution.get('shell', False):
            if not isinstance(exec_prefix, six.string_types):
                exec_prefix = ' '.join(exec_prefix)
            if not isinstance(command, six.string_types):
                msg = "Expected string for shell command, not {type}: {value}"
                msg = msg.format(type=type(command).__name__, value=repr(command))
                raise Exception(msg)
            eax = [exec_prefix + command]
        else:
            if not isinstance(exec_prefix, SEQUENCES):
                exec_prefix = shlex.split(exec_prefix)
            if not isinstance(command, SEQUENCES):
                eax = exec_prefix + shlex.split(command)
            else:
                eax = exec_prefix + command
            eax = [six.moves.shlex_quote(arg) for arg in eax]
        return eax

    @cached_property
    def command_str(self):
        """get command to execute as string properly escaped

        :return: string
        """
        if isinstance(self.command, six.string_types):
            return self.command
        return ' '.join(map(six.moves.shlex_quote, self.command))

    def popen(self, stdout, stderr):
        """Build popen object to run

        :rtype: subprocess.Popen
        """
        self.logger.info('Executing command: %s', self.command_str)
        return subprocess.Popen([self._executor_script], stdout=stdout, stderr=stderr)

    @contextlib.contextmanager
    def module_env(self):
        """Set current process environment according
        to execution `environment` and `modules`
        """
        env = copy.copy(os.environ)
        try:
            for mod in self.execution.get('modules') or []:
                Module.load(mod)
            os.environ.update(self.execution.get('environment') or {})
            yield
        finally:
            os.environ = env

    def __execute(self, stdout, stderr):
        with self.module_env():
            self.benchmark.pre_execute(self.execution, self.exec_context)
        exit_status = self.popen(stdout, stderr).wait()
        with self.module_env():
            self.benchmark.post_execute(self.execution, self.exec_context)
        return exit_status

    @write_yaml_report
    @Enumerator.call_decorator
    def __call__(self, **kwargs):
        with open('stdout', 'w') as stdout, open('stderr', 'w') as stderr:
            cwd = self.execution.get('cwd')
            if cwd is not None:
                ctx = self.parent.parent.parent.exec_context
                cwd = cwd.format(node=ctx.node, tag=ctx.tag)
                with pushd(cwd):
                    exit_status = self.__execute(stdout, stderr)
            else:
                exit_status = self.__execute(stdout, stderr)
        report = dict(
            exit_status=exit_status,
            benchmark=self.benchmark.name,
            executor=type(self).name,
        )

        expected_es = self.execution.get('expected_exit_statuses', {0})
        report['command_succeeded'] = exit_status in expected_es
        if not report['command_succeeded']:
            self.logger.error('Command failed with exit status: %s', exit_status)
        report.update(self.execution)

        report.update(command=self.command)
        return report


class SrunExecutionDriver(ExecutionDriver):
    """Manage process execution with srun (SLURM)
    """

    name = 'srun'

    @cached_property
    def srun(self):
        """Get path to srun executable

        :rtype: string
        """
        commands = self.campaign.process.get('commands', {})
        return find_executable(commands.get('srun', 'srun'))

    @cached_property
    def common_srun_options(self):
        """Get options to be given to all srun commands

        :rtype: list of string
        """
        default = dict(self.campaign.process.get('srun') or {})
        default.update(output='slurm-%N-%t.stdout', error='slurm-%N-%t.error')
        return default

    @cached_property
    def tag(self):
        return self.parent.parent.parent.parent.name

    @cached_property
    def command(self):
        """get command to execute

        :return: list of string
        """
        srun_options = copy.copy(self.common_srun_options)
        srun_options.update(self.config.get('srun') or {})
        srun_optlist = build_slurm_arguments(srun_options)
        if not isinstance(self.root.network.nodes(self.tag), ConstraintTag):
            pargs = parse_constraint_in_args(srun_optlist)
            self.command_expansion_vars['process_count'] = pargs.ntasks
            if not pargs.constraint:
                # Expand nodelist if --constraint option is not specified
                # in srun options
                srun_optlist += [
                    '--nodelist=' + ','.join(self.srun_nodes),
                    '--nodes=' + str(len(self.srun_nodes)),
                ]
        command = super(SrunExecutionDriver, self).command
        return [self.srun] + srun_optlist + command

    @cached_property
    def srun_nodes(self):
        """Get list of nodes where to execute the command
        """
        count = self.execution.get('srun_nodes', 0)
        if isinstance(count, six.string_types):
            tag = count
            count = 0
        elif isinstance(count, SEQUENCES):
            return count
        else:
            assert isinstance(count, int)
            tag = self.tag
        nodes = self._srun_nodes(tag, count)
        if 'srun_nodes' in self.execution:
            self.execution['srun_nodes'] = nodes
            self.execution['srun_nodes_count'] = len(nodes)
        return nodes

    def _srun_nodes(self, tag, count):
        assert count >= 0
        if tag != '*' and not self.root.network.has_tag(tag):
            raise ValueError('Unknown tag: {}'.format(tag))
        nodes = sorted(list(self.root.network.nodes(tag)))
        if count > 0:
            return self._filter_srun_nodes(nodes, count)
        return nodes

    def _filter_srun_nodes(self, nodes, count):
        assert count <= len(nodes)
        pos = nodes.index(self.node)
        nodes = nodes * 2
        return nodes[pos : pos + count]
