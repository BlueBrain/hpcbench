"""Distribute benchmark execution across your cluster
"""
from contextlib import closing, contextmanager
import datetime
import functools
import logging
from multiprocessing import Pool
import os
import os.path as osp
import re
import shutil
import subprocess
import tempfile

from cached_property import cached_property
import six
import yaml

from hpcbench import jinja_environment
from hpcbench.campaign import from_file as campaign_from_file
from hpcbench.driver import write_yaml_report
from hpcbench.toolbox.contextlib_ext import mkdtemp, pushd
from hpcbench.toolbox.process import find_executable


LOGGER = logging.getLogger('benet')
SSH = find_executable('ssh')
SCP = find_executable('scp')
RE_TYPE = type(re.compile('hello'))


class CampaignHolder(object):
    """Abstract class to ease usage of ``campaign`` configuration
    """

    def __init__(self, campaign):
        self.campaign = campaign

    def ssh(self, *args):
        """Build a SSH command
        :param args: arguments given to the command
        :return: command line
        :rtype: list of string
        """
        return self._ssh_cmd(list(args))

    def scp(self, *args):
        """Build a SCP command
        :param args: arguments given to the command
        :return: command line
        :rtype: list of string
        """
        return self._ssh_cmd(list(args), cmd=SCP)

    def _ssh_cmd(self, args, cmd=None):
        cmd = cmd or SSH
        command = [cmd]
        ssh_config = self.campaign.network.get('ssh_config_file')
        if ssh_config:
            command += ['-F', ssh_config]
        return command + args

    @cached_property
    def remote_output_dir(self):
        """Get path where campaign is created on remote nodes
        """
        return self.campaign.campaign_id

    @cached_property
    def remote_work_dir(self):
        """Get working path on remote nodes
        """
        return self.campaign.network.remote_work_dir

    @cached_property
    def installer_template(self):
        """Get Jinja template to use for shell-script installer
        """
        return self.campaign.network.installer_template


class BeNet(CampaignHolder):
    """Main driver
    """

    INSTALLER_SCRIPT = 'hpcbench-benet.sh'
    REMOTE_BENCH_RUNNER = osp.join(tempfile.gettempdir(), INSTALLER_SCRIPT)

    def __init__(self, campaign_file, logger=None):
        self.campaign_file = campaign_file
        super(BeNet, self).__init__(campaign_from_file(campaign_file))
        self.log = logger or LOGGER
        now = datetime.datetime.now()
        output_dir = now.strftime(self.campaign.output_dir)
        self.campaign_path = osp.normpath(output_dir)

    def run(self, *nodes):
        """Execute benchmarks on every node specified in arguments.
        If none are given, then execute benchmarks on every nodes
        specified in the ``network.nodes`` campaign configuration.
        """
        nodes = nodes or self.nodes
        self._prelude(*nodes)

        @write_yaml_report
        def _run():
            self._build_installer()
            runner = functools.partial(run_on_host, self.campaign)
            if self.campaign.network.max_concurrent_runs > 1:
                pool = Pool(self.campaign.network.max_concurrent_runs)
                pool.map(runner, nodes)
            else:
                for node in nodes:
                    runner(node)
            return nodes

        with pushd(self.campaign_path):
            _run()

    @property
    def nodes(self):
        """Alias to the list of nodes specified in the campaign configuration
        :rtype: list of string
        """
        return self.campaign.network.nodes

    def _build_installer(self):
        self.log.info('Generating installer script %s', BeNet.REMOTE_BENCH_RUNNER)
        template = jinja_environment.get_template(self.installer_template)
        prelude = ''
        if self.campaign.network.installer_prelude_file:
            with open(self.campaign.network.installer_prelude_file) as istr:
                prelude = istr.read()
        properties = dict(
            prelude=prelude,
            work_dir=self.remote_work_dir,
            hpcbench_pip_pkg=self.pip_installer_url,
            output_dir=self.remote_output_dir,
        )
        with open(BeNet.REMOTE_BENCH_RUNNER, 'w') as ostr:
            template.stream(**properties).dump(ostr)

    def _prelude(self, *nodes):
        if osp.isdir(self.campaign_path):
            raise RuntimeError(
                'Campaign output directory already exists: %s' % self.campaign_path
            )
        has_error = False
        for node in nodes:
            if not self._check_ssh_access(node):
                has_error = True
        if has_error:
            raise RuntimeError('Could not reach some nodes')

    @cached_property
    def pip_installer_url(self):
        """Alias to the pip installer url in the campaign configuration
        """
        return self.campaign.network.pip_installer_url

    def _check_ssh_access(self, node):
        self.log.info('checking SSH connectivity with node: %s', node)
        command = self.ssh(node, 'true')
        if subprocess.call(command) == 0:
            return True
        return False


def run_on_host(campaign, node, **kwargs):
    """Wrapper function around ``BeNetHost`` class
    meant to be used with ``multiprocessing`` module.
    """
    return BeNetHost(campaign, node, **kwargs).run()


class BeNetHost(CampaignHolder):
    """Remote benchmark execution
    """

    def __init__(self, campaign, node, logger=None):
        """
        :param campaign: campaign configuration as a dictionary
        :param node: server where to execute benchmarks
        :keyword logger: optional logger object
        """
        super(BeNetHost, self).__init__(campaign)
        self.node = node
        self.log = logger or LOGGER.getChild(node)

    def run(self):
        """Execute benchmark on the specified node
        """
        with self._scp_bensh_runner():
            self._execute_bensh_runner()
            path = self._retrieve_tarball()
            try:
                self._aggregate_tarball(path)
            finally:
                os.remove(path)

    def _execute_bensh_runner(self):
        self.log.info('Executing benchmarks on node')
        with closing(six.moves.cStringIO()) as config:
            campaign = self._prepare_campaign()
            yaml.dump(campaign, config)
            command = self.ssh(self.node, 'sh', BeNet.REMOTE_BENCH_RUNNER, '-')
            process = subprocess.Popen(command, stdin=subprocess.PIPE)
            yml_config = config.getvalue()  # pragma pylint: disable=no-member
            process.communicate(input=yml_config.encode('utf-8'))
        exit_status = process.wait()
        if exit_status != 0:
            raise Exception('remote ben-sh failed')

    def _prepare_campaign(self):
        def _nameddict_to_dict(ndict):
            eax = {}
            for key, value in ndict.items():
                if isinstance(value, dict):
                    value = _nameddict_to_dict(value)
                elif isinstance(value, (list)):
                    value = [
                        _nameddict_to_dict(item) if isinstance(item, dict) else item
                        for item in value
                    ]
                elif isinstance(value, RE_TYPE):
                    value = value.pattern
                eax[key] = value
            return eax

        campaign = _nameddict_to_dict(self.campaign)
        campaign['output_dir'] = self.campaign.campaign_id
        return campaign

    def _retrieve_tarball(self):
        fdesc, archive = tempfile.mkstemp(
            prefix='hpcbench-campaign-result', suffix='.tar.bz2'
        )
        os.close(fdesc)
        remote_file = osp.join(
            self.remote_work_dir, self.remote_output_dir + '.tar.bz2'
        )
        cmd = self.scp('{}:{}'.format(self.node, remote_file), archive)
        subprocess.check_call(cmd)
        return archive

    def _aggregate_tarball(self, path):
        with mkdtemp(prefix='hpcbench-campaign-result', remove=False) as tmpd:
            local_output_dir = os.getcwd()
            with pushd(tmpd):
                subprocess.check_call(['tar', 'jxf', path])
                dirs = [
                    _dir
                    for _dir in os.listdir(self.remote_output_dir)
                    if osp.isdir(osp.join(self.remote_output_dir, _dir))
                ]
                if len(dirs) != 1:
                    raise Exception('Expected one directory but got: %s' % dirs)
                shutil.move(
                    osp.join(self.remote_output_dir, dirs[0]),
                    osp.join(local_output_dir, self.node),
                )

    @contextmanager
    def _scp_bensh_runner(self):
        self.log.info('installing remote installer')
        command = self.scp(
            BeNet.REMOTE_BENCH_RUNNER, self.node + ':' + BeNet.REMOTE_BENCH_RUNNER
        )
        subprocess.check_call(command)
        try:
            yield
        finally:
            self.log.info('removing remote installer')
            command = self.ssh(self.node, 'rm', '-f', BeNet.REMOTE_BENCH_RUNNER)
            subprocess.check_call(command)
