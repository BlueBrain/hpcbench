"""HPCBench campaign helper functions
"""
import collections
import os
import re
import socket
import uuid

import hpcbench

from . toolbox.collections_ext import Configuration


def pip_installer_url(version=None):
    """Get argument to give to ``pip`` to install HPCBench.
    """
    version = version or hpcbench.__version__
    version = str(version)
    if '.dev' in version:
        git_rev = 'master'
        if 'TRAVIS_BRANCH' in os.environ:
            git_rev = version.split('+', 1)[-1]
            if '.' in git_rev:  # get rid of date suffix
                git_rev = git_rev.split('.', 1)[0]
            git_rev = git_rev[1:]  # get rid of scm letter
        return 'git+{project_url}@{git_rev}#egg=hpcbench'.format(
            project_url='http://github.com/tristan0x/hpcbench',
            git_rev=git_rev or 'master'
        )
    return 'hpcbench=={}'.format(version)


DEFAULT_CAMPAIGN = dict(
    output_dir="hpcbench-%Y%m%d-%H:%M:%S",
    network=dict(
        nodes=[
            socket.gethostname(),
        ],
        tags=dict(),
        ssh_config_file=None,
        remote_work_dir='.hpcbench',
        installer_template='ssh-installer.sh.jinja',
        installer_prelude_file=None,
        max_concurrent_runs=4,
        pip_installer_url=pip_installer_url(),
    ),
    process=dict(
        type='local',
        config=dict(),
    ),
    tag=dict(),
    benchmarks={
        '*': {}
    },
    export=dict(
        elasticsearch=dict(
            host='localhost',
            connection_params=dict(),
            index_name='hpcbench-{date}'
        )
    )

)


def from_file(campaign_file):
    """Load campaign from YAML file

    :param campaign_file: path to YAML file
    :return: memory representation of the YAML file
    :rtype: dictionary
    """
    campaign = Configuration.from_file(campaign_file)
    return fill_default_campaign_values(campaign)


def fill_default_campaign_values(campaign):
    """Fill an existing campaign with default
    values for optional keys

    :param campaign: dictionary
    :return: object provided in parameter
    :rtype: dictionary
    """
    def _merger(_camp, _deft):
        for key in _deft.keys():
            if (key in _camp and isinstance(_camp[key], dict)
                    and isinstance(_deft[key], collections.Mapping)):
                _merger(_camp[key], _deft[key])
            elif key not in _camp:
                _camp[key] = _deft[key]
    _merger(campaign, DEFAULT_CAMPAIGN)
    campaign.setdefault('campaign_id', str(uuid.uuid4()))

    for tag in list(campaign.network.tags):
        config = campaign.network.tags[tag]
        if isinstance(config, dict):
            config = [config]
            campaign.network.tags[tag] = config
        for pattern in config:
            for mode in list(pattern):
                if mode == 'match':
                    pattern[mode] = re.compile(pattern[mode])
                elif mode == 'nodes':
                    if not isinstance(pattern[mode], list):
                        raise Exception('Invalid "nodes" value type.'
                                        ' list expected')
                    pattern[mode] = set(pattern[mode])
                else:
                    raise Exception('Unknown tag association pattern: %s',
                                    mode)
    return campaign


def get_benchmark_types(campaign):
    """Get of benchmarks referenced in the configuration

    :return: benchmarks
    :rtype: string generator
    """
    for benchmarks in campaign.benchmarks.values():
        for benchmark in benchmarks.values():
            yield benchmark.type


def get_metrics(campaign):
    """Get all metrics of a campaign

    :return: metrics
    :rtype: dictionary generator
    """
    for hostname, host_driver in campaign.traverse():
        for tag, tag_driver in host_driver.traverse():
            for suite, bench_obj in tag_driver.traverse():
                for category, cat_obj in bench_obj.traverse():
                    yield (
                        dict(
                            hostname=hostname,
                            tag=tag,
                            category=category,
                            suite=suite,
                            campaign_id=campaign.campaign.campaign_id,
                        ),
                        cat_obj.metrics
                    )
