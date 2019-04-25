"""HPCBench campaign helper functions
"""
import collections
from contextlib import contextmanager
import filecmp
import functools
import json
import logging
import operator
import os
import os.path as osp
import re
import shutil
import socket
import uuid

from cached_property import cached_property
from ClusterShell.NodeSet import NodeSet
import six
import yaml

import hpcbench
from hpcbench.api import Benchmark
from hpcbench.report import render
from .toolbox.collections_ext import Configuration, dict_map_kv, freeze, nameddict
from .toolbox.env import expandvars
from .toolbox.functools_ext import listify
from .toolbox.slurm import SlurmCluster


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
            project_url='http://github.com/BlueBrain/hpcbench',
            git_rev=git_rev or 'master',
        )
    return 'hpcbench=={}'.format(version)


LOGGER = logging.getLogger('hpcbench')
JSON_METRICS_FILE = 'metrics.json'
SBATCH_JINJA_TEMPLATE = 'sbatch.jinja'
YAML_CAMPAIGN_FILE = 'campaign.yaml'
YAML_EXPANDED_CAMPAIGN_FILE = 'campaign.expanded.yaml'
YAML_REPORT_FILE = 'hpcbench.yaml'
DEFAULT_CAMPAIGN = dict(
    output_dir="hpcbench-%Y%m%d-%H%M%S",
    network=dict(
        nodes=[socket.gethostname()],
        tags=dict(),
        ssh_config_file=None,
        remote_work_dir='.hpcbench',
        installer_template='ssh-installer.sh.jinja',
        installer_prelude_file=None,
        max_concurrent_runs=4,
        pip_installer_url=pip_installer_url(),
        slurm_blacklist_states=[
            'down',
            'down*',
            'drain',
            'drained',
            'draining',
            'error',
            'fail',
            'failing',
            'future',
        ],
    ),
    process=dict(
        type='local',
        config=dict(),
        executor_template='executor.sh.jinja',
        sbatch_template=SBATCH_JINJA_TEMPLATE,
    ),
    tag=dict(),
    benchmarks={'*': {}},
    export=dict(
        elasticsearch=dict(connection_params=dict(), index_name='hpcbench-{date}')
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
            self.template,
            file,
            benchmarks=self.benchmarks,
            hostname=socket.gethostname(),
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
                description=Generator._description(b),
                attributes={
                    attr: dict(
                        doc=Generator._format_attrdoc(b.__class__, attr),
                        value=Generator._format_attrvalue(b.attributes[attr]),
                    )
                    for attr in b.attributes
                },
            )
            for b in benches
        ]

    @classmethod
    def _format_attrdoc(cls, clazz, attr):
        doc = getattr(clazz, attr).__doc__ or ''
        doc = doc.strip()
        doc = '# ' + doc
        return doc.replace('\n        ', '\n          # ').strip()

    @classmethod
    def _format_attrvalue(cls, value):
        if isinstance(value, set):
            value = list(value)
        if isinstance(value, list):
            return yaml.dump(value, default_flow_style=True).rstrip()
        return value

    @classmethod
    def _description(cls, benchmark):
        desc = benchmark.__class__.__doc__
        if desc is None:
            msg = 'Missing %s benchmark class docstring' % benchmark.__class__
            raise Exception(msg)
        desc = desc.split('\n', 1)[0].strip()
        desc = '# ' + desc
        return desc.replace('\n        ', '\n      # ').strip()


def from_file(campaign_file, **kwargs):
    """Load campaign from YAML file

    :return: memory representation of the YAML file
    :rtype: dictionary
    """
    realpath = osp.realpath(campaign_file)
    if osp.isdir(realpath):
        campaign_file = osp.join(campaign_file, YAML_CAMPAIGN_FILE)
    campaign = Configuration.from_file(campaign_file)
    return default_campaign(campaign, **kwargs)


def default_campaign(
    campaign=None, expandcampvars=True, exclude_nodes=None, frozen=True
):
    """Fill an existing campaign with default
    values for optional keys

    :param campaign: dictionary
    :type campaign: str
    :param exclude_nodes: node set to exclude from allocations
    :type exclude_nodes: str
    :param expandcampvars: should env variables be expanded? True by default
    :type expandcampvars: bool
    :param frozen: whether the returned data-structure is immutable or not
    :type frozen: bool
    :return: object provided in parameter
    :rtype: dictionary
    """
    campaign = campaign or nameddict()

    def _merger(_camp, _deft):
        for key in _deft.keys():
            if (
                key in _camp
                and isinstance(_camp[key], dict)
                and isinstance(_deft[key], collections.Mapping)
            ):
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

    if expandcampvars:
        campaign = nameddict(dict_map_kv(campaign, _expandvars))
    else:
        campaign = nameddict(campaign)
    if expandcampvars:
        if campaign.network.get('tags') is None:
            campaign.network['tags'] = {}
        NetworkConfig(campaign).expand()
    return freeze(campaign) if frozen else campaign


class NetworkConfig(object):
    """Wrapper around network configuration
    """

    def __init__(self, campaign, exclude_nodes=None):
        self.campaign = campaign
        self._exclude_nodes = NodeSet(exclude_nodes)

    @property
    def exclude_nodes(self):
        return self._exclude_nodes

    @property
    def network(self):
        """Get network section of the campaign
        """
        return self.campaign.network

    @property
    def slurm(self):
        return self.campaign.network.get('cluster') == 'slurm'

    def expand(self):
        """Perform node expansion of network section.
        """
        if self.slurm:
            self._introspect_slurm_cluster()
        self.network.nodes = self._expand_nodes(self.network.nodes)
        self._expand_tags()

    @cached_property
    def blacklist_states(self):
        states = set(self.network.slurm_blacklist_states)
        if self.campaign.process.type == 'slurm':
            if 'reservation' in self.campaign.process.get('sbatch') or dict():
                states.discard('reserved')
        return states

    @cached_property
    def _reserved_nodes(self):
        if self.campaign.process.type == 'slurm':
            if 'reservation' in self.campaign.process.get('sbatch') or {}:
                rsv_name = self.campaign.process.sbatch.reservation
                try:
                    rsv = SlurmCluster.reservation(rsv_name)
                except KeyError:
                    return None
                finally:
                    return rsv.nodes
        return None

    def _filter_node(self, node):
        if node.state in self.blacklist_states:
            return True
        if self._reserved_nodes is not None:
            return str(node) not in self._reserved_nodes

    def _introspect_slurm_cluster(self):
        cluster = SlurmCluster()
        node_names = set()
        tags = dict()
        for node in cluster.nodes:
            if self._filter_node(node):
                continue
            node_names.add(str(node))
            for feature in node.active_features:
                tag_name = node.partition + '_' + feature
                tags.setdefault(tag_name, []).append(str(node))
                tags.setdefault(feature, []).append(str(node))
        for tag in tags:
            tags[tag] = dict(nodes=tags[tag])
        self.network.nodes = list(node_names)
        LOGGER.info('Found nodes: %s', NodeSet.fromlist(self.network.nodes))
        LOGGER.info('Found tags:')
        for tag in iter(sorted(tags)):
            LOGGER.info("{: >25} {}".format(tag, NodeSet.fromlist(tags[tag]['nodes'])))
        prev_tags = self.network.tags
        self.network.tags = tags
        self.network.tags.update(prev_tags)

    def _expand_nodes(self, nodes):
        if isinstance(nodes, six.string_types):
            nodes = [nodes]
        if not isinstance(nodes, list):
            raise Exception('Invalid "nodes" value type.' ' list expected')
        eax = NodeSet()
        for node in nodes:
            eax.update(node)
        eax -= self.exclude_nodes
        return list(eax)

    def _expand_tag_pattern(self, tag, pattern):
        if len(pattern) > 1:
            msg = "Tag '{tag}' is based on more than one criterion: {types}"
            raise Exception(msg.format(tag=tag, types=', '.join(pattern)))
        for mode in list(pattern):
            if mode == 'match':
                pattern[mode] = re.compile(pattern[mode])
            elif mode == 'nodes':
                pattern[mode] = self._expand_nodes(pattern[mode])
            elif mode == 'constraint':
                value = pattern[mode]
                if not isinstance(value, six.string_types):
                    msg = "Constraint tag '{tag}' "
                    msg += "may be a string, not: {value}"
                    msg = msg.format(tag=tag, value=repr(value))
                    raise Exception(msg)
            elif mode == 'tags':
                pass  # don't fail but ignore tags
            else:
                raise Exception('Unknown tag association pattern: %s', mode)

    @classmethod
    def _is_leaf(cls, config):
        # returns True if in none of the modes and patterns is 'tags'
        return all(['tags' not in pat.keys() for pat in config])

    def _resolve(self, tag, config, expanded, recursive, visited):
        for pattern in config[:]:
            # we work with a copy so we can modify the original
            # first expand all the other modes
            self._expand_tag_pattern(tag, pattern)
            # now let's go through that tags if they exist in this pattern
            if 'tags' in list(pattern):
                tags = pattern['tags']
                if isinstance(tags, six.string_types):
                    tags = [tags]
                for rectag in tags:
                    if rectag in expanded:
                        config += expanded[rectag]
                    elif rectag in visited:
                        raise Exception(
                            'found circular dependency ' + 'between %s and %s',
                            tag,
                            rectag,
                        )
                    elif rectag in recursive:
                        recconfig = recursive.pop(rectag)
                        visited.add(rectag)
                        self._resolve(rectag, recconfig, expanded, recursive, visited)
                    else:  # rectag is nowhere to be found
                        message = '"%s" refers to "%s", which is not defined.'
                        message = message % (tag, rectag)
                        raise Exception(message)
                pattern.pop('tags')  # we've expanded this, it can be deleted
        config = [c for c in config if any(c)]
        if len(config) >= 2:
            for rectag in config:
                if 'constraint' in rectag:
                    message = "Tag '%s': cannot combine constraint tags"
                    message = message % tag
                    raise Exception(message)

        expanded[tag] = config

    def _expand_tags(self):
        expanded = {}
        recursive = {}
        for tag, config in self.network.tags.items():
            if isinstance(config, dict):
                config = [config]
            if NetworkConfig._is_leaf(config):
                for pattern in config:
                    self._expand_tag_pattern(tag, pattern)
                expanded[tag] = config
            else:
                recursive[tag] = config
        # we finished all the leafs (tags without any recursive tag references)
        visited = set(expanded)
        while recursive:
            tag, config = recursive.popitem()
            visited.add(tag)
            self._resolve(tag, config, expanded, recursive, visited)
        self.network.tags = expanded


@listify(wrapper=set)
def get_benchmark_types(campaign):
    """Get of benchmarks referenced in the configuration

    :return: benchmarks
    :rtype: string generator
    """
    for benchmarks in campaign.benchmarks.values():
        for name, benchmark in benchmarks.items():
            if name != 'sbatch':  # exclude special sbatch name
                yield benchmark.type


def get_metrics(campaign, report, top=True):
    """Extract metrics from existing campaign

    :param campaign: campaign loaded with `hpcbench.campaign.from_file`
    :param report: instance of `hpcbench.campaign.ReportNode`
    :param top: this function is recursive. This parameter
    help distinguishing top-call.
    """
    if top and campaign.process.type == 'slurm':
        for path, _ in report.collect('jobid', with_path=True):
            for child in ReportNode(path).children.values():
                for metrics in get_metrics(campaign, child, top=False):
                    yield metrics
    else:

        def metrics_node_extract(report):
            metrics_file = osp.join(report.path, JSON_METRICS_FILE)
            if osp.exists(metrics_file):
                with open(metrics_file) as istr:
                    return json.load(istr)

        def metrics_iterator(report):
            return filter(
                lambda eax: eax[1] is not None,
                report.map(metrics_node_extract, with_path=True),
            )

        for path, metrics in metrics_iterator(report):
            yield report.path_context(path), metrics


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
                reader=CampaignMerge._reader_json, writer=CampaignMerge._writer_json
            ),
            yaml=CampaignMerge.SERIALIZER_CLASS(
                reader=CampaignMerge._reader_yaml, writer=CampaignMerge._writer_yaml
            ),
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
    SERIALIZER_CLASS = collections.namedtuple('serializer', ['reader', 'writer'])

    def _merge_data_file(self, path, extension):
        def _merge(lhs, rhs):
            if isinstance(rhs, list):
                lhs += rhs
                return
            for key in rhs.keys():
                if key in lhs:
                    if isinstance(lhs[key], dict) and isinstance(
                        rhs[key], collections.Mapping
                    ):
                        _merge(lhs[key], rhs[key])
                    elif isinstance(lhs[key], list) and isinstance(rhs[key], list):
                        lhs[key] += rhs[key]
                    elif key == 'elapsed':
                        lhs[key] += rhs[key]
                elif key not in lhs:
                    lhs[key] = rhs[key]

        lhs_file = osp.join(self.lhs, path)
        rhs_file = osp.join(self.rhs, path)
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
                if CampaignMerge.IGNORED_FILES in file_path:
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
            self.rhs = osp.join(self.rhs, subdir)
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


class ReportNode(collections.Mapping):
    """Navigate across hpcbench.yaml files of a campaign
    """

    CONTEXT_ATTRS = ['node', 'tag', 'benchmark', 'category', 'attempt']

    def __init__(self, path):
        """
        :param path: path to an existing campaign directory
        :type path: str
        """
        self._path = path

    @property
    def path(self):
        """get path given in constructor
        :rtype: str
        """
        return self._path

    @listify(wrapper=nameddict)
    def path_context(self, path):
        """Build of dictionary of fields extracted from
        the given path"""
        prefix = os.path.commonprefix([path, self._path])
        relative_path = path[len(prefix) :]
        relative_path = relative_path.strip(os.sep)
        attrs = self.CONTEXT_ATTRS
        for i, elt in enumerate(relative_path.split(os.sep)):
            yield attrs[i], elt
        yield 'path', path

    @property
    def report(self):
        """get path to the hpcbench.yaml report
        :rtype: str
        """
        return osp.join(self._path, YAML_REPORT_FILE)

    @cached_property
    def data(self):
        """get content of hpcbench.yaml
        :rtype: dict
        """
        with open(self.report) as istr:
            return yaml.safe_load(istr)

    @cached_property
    @listify(wrapper=dict)
    def children(self):
        """get children node referenced as `children` in the
        report.
        :rtype: dict with name (str) -> node (ReportNode)
        """
        for child in self.data.get('children', []):
            if osp.exists(osp.join(self.path, child, YAML_REPORT_FILE)):
                yield child, self.__class__(osp.join(self.path, child))

    def map(self, func, **kwargs):
        """Generator function returning result of
        `func(self)`

        :param func: callable object
        :keyword recursive: if True, then apply map to every children nodes
        :keyword with_path: whether the yield values is a tuple
        of 2 elements containing report-path and `func(self)` result or
        simply `func(self)` result.

        :rtype: generator
        """
        if kwargs.get('with_path', False):
            yield self.path, func(self)
        if kwargs.get('recursive', True):
            for child in self.children.values():
                for value in child.map(func, **kwargs):
                    yield value

    def collect(self, *keys, **kwargs):
        """Generator function traversing
        tree structure to collect values of a specified key.

        :param keys: the keys to look for in the report
        :type key: str
        :keyword recursive: look for key in children nodes
        :type recursive: bool
        :keyword with_path: whether the yield values is a tuple
        of 2 elements containing report-path and the value
        or simply the value.
        :type with_path: bool

        :rtype: generator providing either values or
        tuples of 2 elements containing report path and value
        depending on with_path parameter
        """
        if not keys:
            raise Exception('Missing key')
        has_values = functools.reduce(
            operator.__and__, [key in self.data for key in keys], True
        )
        if has_values:
            values = tuple([self.data[key] for key in keys])
            if len(values) == 1:
                values = values[0]
            if kwargs.get('with_path', False):
                yield self.path, values
            else:
                yield values
        if kwargs.get('recursive', True):
            for child in self.children.values():
                for value in child.collect(*keys, **kwargs):
                    yield value

    def collect_one(self, *args, **kwargs):
        """Same as `collect` but expects to have only one result.

        :return: the only result directly, not the generator like `collect`.
        """
        generator = self.collect(*args, **kwargs)
        try:
            value = next(generator)
        except StopIteration:
            raise Exception("Expected exactly one value don't have any")
        try:
            next(generator)
        except StopIteration:
            return value
        raise Exception('Expected exactly one value but have more')

    def __getitem__(self, item):
        return self.data[item]

    def __len__(self):
        return len(self.data)

    def __iter__(self):
        return iter(self.data)
