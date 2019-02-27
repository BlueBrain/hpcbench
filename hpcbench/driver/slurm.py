from collections import Mapping
import datetime
import inspect
import logging
import re
import subprocess
import os
from os import path as osp
import sys

import jinja2.exceptions
from cached_property import cached_property
import six

from hpcbench import jinja_environment
from hpcbench.campaign import SBATCH_JINJA_TEMPLATE
from .base import Enumerator, LOGGER, ConstraintTag, write_yaml_report
from hpcbench.toolbox.functools_ext import listify
from hpcbench.toolbox.process import (
    build_slurm_arguments,
    parse_constraint_in_args,
    find_executable,
)
from hpcbench.toolbox.spack import SpackCmd


class SlurmDriver(Enumerator):
    """Abstract representation of the campaign for the current cluster"""

    def __init__(self, parent):
        super(SlurmDriver, self).__init__(parent)
        LOGGER.info("We are in SLURM/SBATCH mode")

    @cached_property
    def children(self):
        bench_tags = set(
            [
                tag
                for tag in self.campaign.benchmarks
                if any(self.campaign.benchmarks[tag])
            ]
        )

        cluster_tags = bench_tags & set(self.campaign.network.tags)
        return list(cluster_tags)

    def child_builder(self, child):
        return SbatchDriver(self, child)


class SbatchDriver(Enumerator):
    """Abstract representation of sbatch jobs created for each non-empty tag"""

    def __init__(self, parent, tag):
        super(SbatchDriver, self).__init__(parent, name=tag)
        self.tag = tag
        now = datetime.datetime.now()
        sbatch_filename = '{tag}-%Y%m%d-%H%M%S.sbatch'
        level = self.logger.getEffectiveLevel()
        verb = ''
        if level == logging.NOTSET or level >= logging.WARNING:
            verb = ''
        elif level == logging.INFO:
            verb = '-v '
        elif level == logging.DEBUG:
            verb = '-vv '
        exclude_nodes = ''
        if self.root.exclude_nodes:
            exclude_nodes = '--exclude-nodes=' + self.root.exclude_nodes + ' '

        cmd = (
            '{bensh} --srun={tag} '
            + verb
            + '-n $SLURMD_NODENAME '
            + '--output-dir={tag}-%Y%m%d-%H%M%S '
            + exclude_nodes
            + self.parent.parent.campaign_file
        )

        self.sbatch_filename = now.strftime(sbatch_filename)
        self.sbatch_filename = self.sbatch_filename.format(tag=tag)
        self.sbatch_outdir = osp.splitext(self.sbatch_filename)[0]
        self.hpcbench_cmd = now.strftime(cmd)
        self.hpcbench_cmd = self.hpcbench_cmd.format(
            tag=tag, bensh=self.bensh_executable
        )

    @cached_property
    def bensh_executable(self):
        candidates = []
        main_script = inspect.stack()[-1][1]
        if main_script.endswith('ben-sh'):
            candidates.append(osp.realpath(osp.join(os.getcwd(), main_script)))
        candidates.append(osp.realpath(osp.join(osp.dirname(sys.executable), 'ben-sh')))
        candidates.append('ben-sh')
        for candidate in candidates:
            if osp.exists(candidate):
                break
        return candidate

    @property
    def default_job_name(self):
        """Slurm job name if not already specified
        in the `sbatch` section"""
        name = ''
        if not self.root.existing_campaign:
            campaign_file = osp.basename(self.root.campaign_file)
            campaign = osp.splitext(campaign_file)[0]
            name += campaign + '/'
        name += self.tag
        return name

    @cached_property
    def sbatch_args(self):
        nodes = self.root.network.nodes(self.tag)
        sbatch_options = dict(self.campaign.process.get('sbatch', {}))
        if 'job-name' not in sbatch_options:
            sbatch_options['job-name'] = self.default_job_name
        if isinstance(nodes, ConstraintTag):
            sbatch_options['constraint'] = nodes.constraint
        if self.tag in self.campaign.benchmarks:
            tag_sbatch_opts = self.campaign.benchmarks[self.tag].get('sbatch', dict())
            sbatch_options.update(tag_sbatch_opts)
        sbatch_options = build_slurm_arguments(sbatch_options)
        if not isinstance(nodes, ConstraintTag):
            pargs = parse_constraint_in_args(sbatch_options)
            if not pargs.constraint:
                # Expand nodelist if --constraint option is not specified
                # in srun options
                count = pargs.nodes or len(nodes)
                sbatch_options += [
                    '--nodelist=' + ','.join(self._filter_nodes(nodes, count)),
                    '--nodes=' + str(count),
                ]
        return sbatch_options

    def _filter_nodes(self, nodes, count):
        assert count <= len(nodes), "Expected # of nodes <= {} but got {}".format(
            count, len(nodes)
        )
        if count < len(nodes):
            self.logger.warning(
                "Asking to run SBATCH job with " "%d of %d declared nodes in tag",
                count,
                len(nodes),
            )
        return nodes[:count]

    @cached_property
    def children(self):
        return [self.tag]

    def child_builder(self, child):
        del child  # not needed

    @property
    def sbatch_template(self):
        """:return Jinja sbatch template for the current tag"""
        template = self.sbatch_template_str
        if template.startswith('#!'):
            # script is embedded in YAML
            return jinja_environment.from_string(template)
        return jinja_environment.get_template(template)

    @property
    def sbatch_template_str(self):
        """:return Jinja sbatch template for the current tag as string"""
        templates = self.campaign.process.sbatch_template
        if isinstance(templates, Mapping):
            # find proper template according to the tag
            template = templates.get(self.tag)
            if template is None:
                template = templates.get('*')
            if template is None:
                template = SBATCH_JINJA_TEMPLATE
        else:
            template = templates
        return template

    @write_yaml_report
    @Enumerator.call_decorator
    def __call__(self, **kwargs):
        self._install_spack_specs()
        with open(self.sbatch_filename, 'w') as sbatch:
            self._create_sbatch(sbatch)
        sbatch_jobid = self._execute_sbatch()
        return dict(
            sbatch=self.sbatch_filename,
            jobid=sbatch_jobid,
            children=[self.sbatch_outdir],
        )

    def _create_sbatch(self, ostr):
        """Write sbatch template to output stream
        :param ostr: opened file to write to
        """
        properties = dict(
            sbatch_arguments=self.sbatch_args, hpcbench_command=self.hpcbench_cmd
        )
        try:
            self.sbatch_template.stream(**properties).dump(ostr)
        except jinja2.exceptions.UndefinedError:
            self.logger.error('Error while generating SBATCH template:')
            self.logger.error('%%<--------' * 5)
            for line in self.sbatch_template_str.splitlines():
                self.logger.error(line)
            self.logger.error('%%<--------' * 5)
            self.logger.error('Template properties: %s', properties)
            raise

    def _install_spack_specs(self):
        spack = SpackCmd()
        for spec in self.spack_specs:
            spack.install(spec)

    @property
    @listify
    def spack_specs(self):
        benchmarks = self.campaign.benchmarks[self.tag] or {}
        for config in benchmarks.values():
            spack = config.get('spack') or {}
            for spec in spack.get('specs') or []:
                yield spec

    def _execute_sbatch(self):
        """Schedule the sbatch file using the sbatch command
        :returns the slurm job id
        """
        commands = self.campaign.process.get('commands', {})
        sbatch = find_executable(commands.get('sbatch', 'sbatch'))
        sbatch_command = [sbatch, '--parsable', self.sbatch_filename]
        try:
            self.logger.debug(
                'Executing command: %s',
                ' '.join(map(six.moves.shlex_quote, sbatch_command)),
            )
            sbatch_out = subprocess.check_output(
                sbatch_command, universal_newlines=True
            )
        except subprocess.CalledProcessError as cpe:
            self.logger.error(
                "SBATCH return non-zero exit" "status %d for tag %s",
                cpe.returncode,
                self.tag,
            )
            sbatch_out = cpe.output
        jobidre = re.compile(r'^([\d]+)(?:;\S*)?$')
        jobid = None
        for line in sbatch_out.splitlines():
            res = jobidre.match(line)
            if res is not None:
                jobid = res.group(1)
                self.logger.info("Submitted SBATCH job %s for tag %s", jobid, self.tag)
            elif line:
                self.logger.warning("SBATCH: %s", line)
        if jobid is None:
            self.logger.error("SBATCH submission failed for tag %s", self.tag)
            return -1
        else:
            return int(jobid)
