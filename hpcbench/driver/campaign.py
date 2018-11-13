import datetime
import os
import shutil
import socket
from os import path as osp

import six
import yaml
from ClusterShell.NodeSet import NodeSet
from cached_property import cached_property

from hpcbench.api import Benchmark
from hpcbench.campaign import YAML_CAMPAIGN_FILE, YAML_EXPANDED_CAMPAIGN_FILE, from_file
from .benchmark import BenchmarkDriver
from .base import Enumerator, Top, LOGGER, LOCALHOST, ConstraintTag
from .executor import ExecutionDriver, SrunExecutionDriver
from .slurm import SlurmDriver
from hpcbench.toolbox.collections_ext import dict_merge
from hpcbench.toolbox.contextlib_ext import pushd
from hpcbench.toolbox.functools_ext import listify


class Network(object):
    def __init__(self, campaign, logger=None):
        self.campaign = campaign
        self.logger = logger or LOGGER

    def has_tag(self, tag):
        return tag in self.campaign.network.tags

    def node_pairs(self, tag, node):
        nodes = self.nodes(tag)
        try:
            pos = nodes.index(node)
        except ValueError:
            self.logger.error(
                'Could not find node %s in nodes %s', node, ', '.join(nodes)
            )
        return [[node, nodes[i]] for i in range(pos + 1, len(nodes))]

    def nodes(self, tag):
        """get nodes that belong to a tag
        :param tag: tag name
        :rtype: list of string
        """
        if tag == '*':
            return sorted(list(set(self.campaign.network.nodes)))
        definitions = self.campaign.network.tags.get(tag)
        if definitions is None:
            return []
        nodes = set()
        for definition in definitions:
            if len(definition.items()) == 0:
                continue
            mode, value = list(definition.items())[0]
            if mode == 'match':
                nodes = nodes.union(
                    set(
                        [
                            node
                            for node in self.campaign.network.nodes
                            if value.match(node)
                        ]
                    )
                )
            elif mode == 'constraint':
                slurm_nodes = os.environ.get('SLURM_JOB_NODELIST')
                if slurm_nodes:
                    nodes = NodeSet(slurm_nodes)
                else:
                    return ConstraintTag(tag, value)
            else:
                assert mode == 'nodes'
                nodes = nodes.union(set(value))
        return sorted(list(nodes))


class CampaignDriver(Enumerator):
    """Abstract representation of an entire campaign"""

    def __init__(
        self,
        campaign,
        node=None,
        output_dir=None,
        srun=None,
        logger=None,
        expandcampvars=True,
        exclude_nodes=None,
    ):
        node = node or socket.gethostname()
        self.exclude_nodes = exclude_nodes
        if isinstance(campaign, six.string_types):
            campaign_path = osp.normpath(osp.abspath(campaign))
            if osp.isdir(campaign_path):
                self.existing_campaign = True
                self.campaign_path = campaign_path
                campaign = osp.join(campaign, YAML_CAMPAIGN_FILE)
            else:
                # YAML file
                self.existing_campaign = False
            campaign = from_file(
                campaign, expandcampvars=expandcampvars, exclude_nodes=exclude_nodes
            )
            self.campaign_file = campaign_path
        else:
            self.existing_campaign = True
            self.campaign_path = None
        super(CampaignDriver, self).__init__(
            Top(campaign=campaign, node=node, logger=logger or LOGGER, root=self)
        )
        self.network = Network(self.campaign)
        self.filter_tag = srun
        if srun:  # overwrite process type and force srun when requested
            self.campaign.process.type = 'srun'

        if not self.existing_campaign:
            now = datetime.datetime.now()
            self.campaign_path = now.strftime(output_dir or self.campaign.output_dir)
            self.campaign_path = self.campaign_path.format(node=node)

    def child_builder(self, child):
        if self.campaign.process.type == 'slurm':
            return SlurmDriver(self)
        else:
            return HostDriver(self, name=child, tag=self.filter_tag)

    @cached_property
    def children(self):
        return [self.node]

    def __call__(self, **kwargs):
        """execute benchmarks"""
        with pushd(self.campaign_path, mkdir=True):
            if not self.existing_campaign:
                if osp.isfile(self.campaign_file):
                    shutil.copy(self.campaign_file, YAML_CAMPAIGN_FILE)
                else:
                    with open(YAML_CAMPAIGN_FILE, 'w') as ostr:
                        yaml.dump(self.campaign, ostr, default_flow_style=False)
                with open(YAML_EXPANDED_CAMPAIGN_FILE, 'w') as ostr:
                    yaml.dump(self.campaign, ostr, default_flow_style=False)
            super(CampaignDriver, self).__call__(**kwargs)

    @cached_property
    def execution_cls(self):
        """Get execution layer class
        """
        name = self.campaign.process.type
        for clazz in [ExecutionDriver, SrunExecutionDriver]:
            if name == clazz.name:
                return clazz
        raise NameError("Unknown execution layer: '%s'" % name)


class HostDriver(Enumerator):
    """Abstract representation of the campaign for the current host"""

    def __init__(self, parent, name, tag=None):
        super(HostDriver, self).__init__(parent, name)
        self.tag = tag

    @cached_property
    def children(self):
        """Retrieve tags associated to the current node"""
        tags = {'*'}
        if self.tag:
            network_tags = {self.tag: self.campaign.network.tags[self.tag]}
        else:
            network_tags = self.campaign.network.tags
        for tag, configs in network_tags.items():
            for config in configs:
                for mode, kconfig in config.items():
                    if mode == 'match':
                        if kconfig.match(self.name) or kconfig.match(LOCALHOST):
                            tags.add(tag)
                            break
                    elif mode == 'nodes':
                        if self.name in kconfig or LOCALHOST in kconfig:
                            tags.add(tag)
                            break
                    elif mode == 'constraint':
                        tags.add(tag)
                        break
                if tag in tags:
                    break
        return tags

    def child_builder(self, child):
        return BenchmarkTagDriver(self, child)


class BenchmarkTagDriver(Enumerator):
    """Abstract representation of a campaign tag
    (keys of "benchmark" YAML tag)"""

    @cached_property
    @listify
    def children(self):
        return [
            name
            for name in self.campaign.benchmarks.get(self.name, [])
            if self._precondition_is_met(name)
        ]

    def _precondition_is_met(self, name):
        if name == 'sbatch':
            # this is a special name that does not denote a benchmark
            # but tag-specific sbatch parameters
            return False
        config = self.campaign.precondition.get(name)
        if config is None:
            return True
        for var in config:
            if var in os.environ:
                return True
        return False

    def child_builder(self, child):
        conf = self.campaign.benchmarks[self.name][child]
        benchmark = Benchmark.get_subclass(conf['type'])()
        if 'attributes' in conf:
            dict_merge(benchmark.attributes, conf['attributes'] or {})
        return BenchmarkDriver(self, benchmark, child, conf)
