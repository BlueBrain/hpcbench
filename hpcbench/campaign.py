"""HPCBench campaign helper functions
"""
import collections
from contextlib import contextmanager
import filecmp
import json
import os
import os.path as osp
import re
import shutil
import socket
import uuid

import six
import yaml

import hpcbench
from hpcbench.api import Benchmark
from hpcbench.ext.ClusterShell.NodeSet import NodeSet
from hpcbench.report import render
from . toolbox.collections_ext import (
    Configuration,
    dict_map_kv,
    nameddict,
)
from . toolbox.env import expandvars


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
    ),
    precondition=dict(),
)


class Generator(object):
    """Generate default campaign file"""
    DEFAULT_TEMPLATE = 'hpcbench.yaml.jinja'

    def __init__(self, template=None):
        """Jinja template to use (in hpcbench/templates/ directory)
        """
        self.template = template or Generator.DEFAULT_TEMPLATE

    def write(self, file):
        """Write YAML campaign template to the given open file
        """
        render(
            self.template, file,
            benchmarks=self.benchmarks,
            hostname=socket.gethostname()
        )

    @property
    def benchmarks(self):
        # instantiate all benchmarks
        benches = [b() for b in Benchmark.__subclasses__()]
        # filter benchmark whose API says they should be included
        # in the template
        benches = [b for b in benches if b.in_campaign_template]
        # sort by name
        benches = sorted(benches, key=lambda b: b.name)
        # return payload for Jinja template
        return [
            dict(
                name=b.name,
                description=Generator._description(b.description),
                attributes={
                    attr: dict(
                        doc=Generator._format_attrdoc(b.__class__, attr),
                        value=Generator._format_attrvalue(b.attributes[attr])
                    )
                    for attr in b.attributes
                }
            )
            for b in benches
        ]

    @classmethod
    def _format_attrdoc(cls, clazz, attr):
        doc = (getattr(clazz, attr).__doc__ or '')
        doc = doc.strip()
        doc = '# ' + doc
        return doc.replace('\n        ', '\n          # ').strip()

    @classmethod
    def _format_attrvalue(cls, value):
        if isinstance(value, set):
            value = list(value)
        if isinstance(value, list):
            return yaml.dump(value).rstrip()
        return value

    @classmethod
    def _description(cls, desc):
        desc = desc.strip()
        desc = '# ' + desc
        return desc.replace('\n        ', '\n      # ').strip()


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

    for precondition in campaign.precondition.keys():
        config = campaign.precondition[precondition]
        if not isinstance(config, list):
            campaign.precondition[precondition] = [config]

    def _expandvars(value):
        if isinstance(value, six.string_types):
            return expandvars(value)
        return value
    campaign = nameddict(dict_map_kv(campaign, _expandvars))

    NetworkConfig(campaign).expand()
    return campaign


class NetworkConfig(object):
    """Wrapper around network configuration
    """
    def __init__(self, campaign):
        self.campaign = campaign

    @property
    def network(self):
        """Get network section of the campaign
        """
        return self.campaign.network

    def expand(self):
        """Perforn node expansion of network section.
        """
        self.network.nodes = NetworkConfig._expand_nodes(self.network.nodes)
        for tag in list(self.network.tags):
            self._expand_tag(tag)

    @classmethod
    def _expand_nodes(cls, nodes):
        if isinstance(nodes, six.string_types):
            nodes = [nodes]
        if not isinstance(nodes, list):
            raise Exception('Invalid "nodes" value type.'
                            ' list expected')
        eax = NodeSet()
        for node in nodes:
            eax.update(node)
        return list(eax)

    @classmethod
    def _expand_tag_pattern(cls, pattern):
        for mode in list(pattern):
            if mode == 'match':
                pattern[mode] = re.compile(pattern[mode])
            elif mode == 'nodes':
                pattern[mode] = NetworkConfig._expand_nodes(pattern[mode])
            else:
                raise Exception('Unknown tag association pattern: %s',
                                mode)

    def _expand_tag(self, tag):
        config = self.network.tags[tag]
        if isinstance(config, dict):
            config = [config]
            self.network.tags[tag] = config
        for pattern in config:
            self._expand_tag_pattern(pattern)


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


class CampaignMerge(object):
    """Merge 2 campaign directories
    """

    def __init__(self, lhs, rhs):
        """Merge 2 campaign directories

        :param lhs: path to campaign that will receive data
        of the second campaign
        :param rhs: campaign to merge data from
        """
        self.lhs = lhs
        self.rhs = rhs
        self.serializers = dict(
            json=CampaignMerge.SERIALIZER_CLASS(
                reader=CampaignMerge._reader_json,
                writer=CampaignMerge._writer_json
            ),
            yaml=CampaignMerge.SERIALIZER_CLASS(
                reader=CampaignMerge._reader_yaml,
                writer=CampaignMerge._writer_yaml
            )
        )

    def merge(self):
        """Perform merge operation between 2 campaign directories
        """
        self.ensure_has_same_campaigns()
        self._merge()

    @staticmethod
    def _reader_json(path):
        with open(path) as istr:
            return json.load(istr)

    @staticmethod
    def _reader_yaml(path):
        with open(path) as istr:
            return yaml.safe_load(istr)

    @staticmethod
    def _writer_json(data, path):
        with open(path, 'w') as ostr:
            json.dump(data, ostr, indent=2)

    @staticmethod
    def _writer_yaml(data, path):
        with open(path, 'w') as ostr:
            yaml.dump(data, ostr, default_flow_style=False)

    DATA_FILE_EXTENSIONS = {'yaml', 'json'}
    IGNORED_FILES = 'campaign.yaml'
    SERIALIZER_CLASS = collections.namedtuple('serializer',
                                              ['reader', 'writer'])

    def _merge_data_file(self, path, extension):
        def _merge(lhs, rhs):
            if isinstance(rhs, list):
                lhs += rhs
                return
            for key in rhs.keys():
                if key in lhs:
                    if (isinstance(lhs[key], dict)
                            and isinstance(rhs[key], collections.Mapping)):
                        _merge(lhs[key], rhs[key])
                    elif (isinstance(lhs[key], list)
                          and isinstance(rhs[key], list)):
                        lhs[key] += rhs[key]
                    elif key == 'elapsed':
                        lhs[key] += rhs[key]
                elif key not in lhs:
                    lhs[key] = rhs[key]
        lhs_file = osp.join(self.lhs, path)
        rhs_file = osp.join(self.lhs, path)
        assert osp.isfile(rhs_file)
        assert osp.isfile(lhs_file)
        lhs_data = self.serializers[extension].reader(lhs_file)
        rhs_data = self.serializers[extension].reader(rhs_file)
        _merge(lhs_data, rhs_data)
        self.serializers[extension].writer(lhs_data, lhs_file)

    def ensure_has_same_campaigns(self):
        """Ensure that the 2 campaigns to merge have been generated
        from the same campaign.yaml
        """
        lhs_yaml = osp.join(self.lhs, 'campaign.yaml')
        rhs_yaml = osp.join(self.rhs, 'campaign.yaml')
        assert osp.isfile(lhs_yaml)
        assert osp.isfile(rhs_yaml)
        assert filecmp.cmp(lhs_yaml, rhs_yaml)

    def _merge(self):
        for filename in os.listdir(self.rhs):
            file_path = osp.join(self.rhs, filename)
            if osp.isdir(file_path):
                dest_path = osp.join(self.lhs, filename)
                if not osp.isdir(dest_path):
                    shutil.copytree(file_path, dest_path)
                else:
                    with self._push(filename):
                        self._merge()
            else:
                if file_path in CampaignMerge.IGNORED_FILES:
                    continue
                extension = osp.splitext(filename)[1][1:]
                if extension in CampaignMerge.DATA_FILE_EXTENSIONS:
                    self._merge_data_file(filename, extension)

    @contextmanager
    def _push(self, subdir):
        lhs = self.lhs
        rhs = self.rhs
        try:
            self.lhs = osp.join(self.lhs, subdir)
            self.rhs = osp.join(self. rhs, subdir)
            yield
        finally:
            self.lhs = lhs
            self.rhs = rhs


def merge_campaigns(output_campaign, *campaigns):
    """Merge campaign directories

    :param output_campaign: existing campaign directory
    where data from others campaigns will be merged into
    :param campaigns: existing campaigns to merge from
    """
    for campaign in campaigns:
        CampaignMerge(output_campaign, campaign).merge()
