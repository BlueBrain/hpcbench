"""Campaign execution and post-processing
"""
from abc import (
    ABCMeta,
    abstractmethod,
    abstractproperty,
)
from collections import (
    Mapping,
    namedtuple,
)
import copy
import datetime
from functools import wraps
import json
import logging
import os
import os.path as osp
import shutil
import socket
import subprocess
import types
import uuid

from cached_property import cached_property
import six
import yaml

from . api import Benchmark
from . campaign import from_file
from . plot import Plotter
from . toolbox.collections_ext import (
    dict_merge,
    nameddict,
)
from . toolbox.contextlib_ext import (
    pushd,
    Timer,
)
from . toolbox.functools_ext import listify
from . toolbox.process import find_executable

LOGGER = logging.getLogger('hpcbench')
YAML_REPORT_FILE = 'hpcbench.yaml'
YAML_CAMPAIGN_FILE = 'campaign.yaml'
JSON_METRICS_FILE = 'metrics.json'


def write_yaml_report(func):
    """Decorator used to campaign node post-processing
    """
    @wraps(func)
    def _wrapper(*args, **kwargs):
        now = datetime.datetime.now()
        with Timer() as timer:
            data = func(*args, **kwargs)
            if isinstance(data, (list, types.GeneratorType)):
                report = dict(children=list(map(str, data)))
            elif isinstance(data, dict):
                report = data
            else:
                raise Exception('Unexpected data type: %s', type(data))
        report['elapsed'] = timer.elapsed
        report['date'] = now.isoformat()
        if "no_exec" not in kwargs and report is not None:
            with open(YAML_REPORT_FILE, 'w') as ostr:
                yaml.dump(report, ostr, default_flow_style=False)
        return report
    return _wrapper


class Enumerator(six.with_metaclass(ABCMeta, object)):
    """Common class for every campaign node"""
    def __init__(self, parent, name=None, logger=None):
        self.parent = parent
        self.campaign = parent.campaign
        self.node = parent.node
        self.name = name
        if logger:
            self.logger = logger
        elif name:
            self.logger = parent.logger.getChild(name)
        else:
            self.logger = parent.logger

    @abstractmethod
    def child_builder(self, child):
        """Provides callable object returning child instance.
        """
        raise NotImplementedError  # pragma: no cover

    @abstractproperty
    def children(self):
        """Property to be overriden be subclass to provide child objects"""
        raise NotImplementedError  # pragma: no cover

    @cached_property
    def report(self):
        """Get object report. Content of ``YAML_REPORT_FILE``
        """
        with open(YAML_REPORT_FILE) as istr:
            return nameddict(yaml.load(istr))

    @write_yaml_report
    def __call__(self, **kwargs):
        for child in self._children:
            with pushd(str(child), mkdir=True):
                child_obj = self.child_builder(child)
                child_obj(**kwargs)
                yield child

    @cached_property
    def _children(self):
        if osp.isfile(YAML_REPORT_FILE):
            return self.report['children']
        return self.children

    def traverse(self):
        """Enumerate children and build associated objects
        """
        builder = self.child_builder
        for child in self._children:
            with pushd(str(child)):
                yield child, builder(child)


class Leaf(Enumerator):
    """Enumerator class for classes at the bottom of the hierarchy
    """
    def child_builder(self, child):
        del child  # unused

    def children(self):
        return []


class CampaignDriver(Enumerator):
    """Abstract representation of an entire campaign"""
    def __init__(self, campaign_file=None, campaign_path=None,
                 node=None, logger=None):
        node = node or socket.gethostname()
        if campaign_file and campaign_path:
            raise Exception('Either campaign_file xor path can be specified')
        if campaign_path:
            campaign_file = osp.join(campaign_path, YAML_CAMPAIGN_FILE)
        self.campaign_file = osp.abspath(campaign_file)
        top = namedtuple('top', ['campaign', 'node'])
        super(CampaignDriver, self).__init__(
            top(campaign=from_file(campaign_file), node=node),
            None,
            logger=logger or LOGGER
        )
        if campaign_path:
            self.existing_campaign = True
            self.campaign_path = campaign_path
        else:
            self.existing_campaign = False
            now = datetime.datetime.now()
            self.campaign_path = now.strftime(self.campaign.output_dir)

    def child_builder(self, child):
        return HostDriver(self, name=child)

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
                        yaml.dump(self.campaign, ostr,
                                  default_flow_style=False)
            super(CampaignDriver, self).__call__(**kwargs)


class HostDriver(Enumerator):
    """Abstract representation of the campaign for the current host"""

    @cached_property
    def children(self):
        """Retrieve tags associated to the current node"""
        benchmarks = {'*'}
        for tag, configs in self.campaign.network.tags.items():
            for config in configs:
                for mode, kconfig in config.items():
                    if mode == 'match':
                        if kconfig.match(self.name):
                            benchmarks.add(tag)
                            break
                    elif mode == 'nodes':
                        if self.name in kconfig:
                            benchmarks.add(tag)
                            break
                    else:
                        raise Exception('Unknown tag association pattern: %s',
                                        mode)
                if tag in benchmarks:
                    break
        return benchmarks

    def child_builder(self, child):
        return BenchmarkTagDriver(self, child)

    def nodes(self, tag):
        """get list of nodes that belong to a tag
        :rtype: list of string
        """
        if tag == '*':
            return self.campaign.network.nodes
        definition = self.campaign.network.tags.get('tag')
        if definition is None:
            return []
        mode, value = definition.items()[0]
        if mode == 'match':
            return [
                node for node in self.campaign.network.nodes
                if value.match(node)
            ]
        elif mode == 'nodes':
            return value
        else:
            raise Exception('Unknown tag association pattern: %s',
                            mode)


class BenchmarkTagDriver(Enumerator):
    """Abstract representation of a campaign tag
    (keys of "benchmark" YAML tag)"""

    @cached_property
    def children(self):
        return list(self.campaign.benchmarks.get(self.name, []))

    def child_builder(self, child):
        conf = self.campaign.benchmarks[self.name][child]
        benchmark = Benchmark.get_subclass(conf['type'])()
        if 'attributes' in conf:
            dict_merge(
                benchmark.attributes,
                conf['attributes']
            )
        return BenchmarkDriver(self, benchmark)


class BenchmarkDriver(Enumerator):
    """Abstract representation of a benchmark, part of a campaign tag
    """
    def __init__(self, parent, benchmark):
        super(BenchmarkDriver, self).__init__(parent, benchmark.name)
        self.benchmark = benchmark

    @cached_property
    def children(self):
        categories = set()
        for execution in self.benchmark.execution_matrix:
            categories.add(execution['category'])
        return categories

    def child_builder(self, child):
        return BenchmarkCategoryDriver(self, child, self.benchmark)


class BenchmarkCategoryDriver(Enumerator):
    """Abstract representation of one benchmark to execute
    (one of "benchmarks" YAML tag values")"""
    def __init__(self, parent, category, benchmark):
        super(BenchmarkCategoryDriver, self).__init__(parent, category)
        self.category = category
        self.benchmark = benchmark

    @cached_property
    def plot_files(self):
        """Get path to the benchmark category plots files
        """
        for plot in self.benchmark.plots[self.category]:
            yield osp.join(os.getcwd(), Plotter.get_filename(plot))

    @cached_property
    def commands(self):
        """Get all commands of the benchmark category

        :return generator of string
        """
        for child in self._children:
            with open(osp.join(child, YAML_REPORT_FILE)) as istr:
                command = yaml.load(istr)['command']
                yield ' '.join(map(six.moves.shlex_quote, command))

    @cached_property
    @listify
    def children(self):
        for execution in self.benchmark.execution_matrix:
            category = execution.get('category')
            if category != self.category:
                continue
            name = execution.get('name') or ''
            yield (
                execution,
                osp.join(
                    name,
                    str(uuid.uuid4())
                )
            )

    def child_builder(self, child):
        del child  # unused

    @cached_property
    def execution_layer_class(self):
        """Get execution layer class
        """
        name = self.campaign.process.type
        for clazz in [ExecutionDriver, SlurmExecutionDriver]:
            if name == clazz.name:
                return clazz
        raise NameError("Unknown execution layer: '%s'" % name)

    def execution_layer(self, execution):
        """Build the proper execution layer
        """
        return self.execution_layer_class(self, self.benchmark, execution)

    @write_yaml_report
    def __call__(self, **kwargs):
        if "no_exec" not in kwargs:
            runs = dict()
            for execution, run_dir in self.children:
                runs.setdefault(execution['category'], []).append(run_dir)
                with pushd(run_dir, mkdir=True):
                    driver = self.execution_layer(execution)
                    driver(**kwargs)
                    mdriver = MetricsDriver(self.campaign, self.benchmark)
                    mdriver(**kwargs)
                    yield run_dir
            self.gather_metrics(runs)
        elif 'plot' in kwargs:
            for plot in self.benchmark.plots.get(self.category):
                self._generate_plot(plot, self.category)
        else:
            runs = dict()
            for child in self.report['children']:
                child_yaml = osp.join(child, YAML_REPORT_FILE)
                with open(child_yaml) as istr:
                    child_config = yaml.load(istr)
                child_config.pop('children', None)
                runs.setdefault(self.category, []).append(child)
                with pushd(child):
                    MetricsDriver(self.campaign, self.benchmark)(**kwargs)
            self.gather_metrics(runs)

    def gather_metrics(self, runs):
        """Write a JSON file with the result of every runs
        """
        for run_dirs in runs.values():
            with open(JSON_METRICS_FILE, 'w') as ostr:
                ostr.write('[\n')
                for i in range(len(run_dirs)):
                    with open(osp.join(run_dirs[i], YAML_REPORT_FILE)) as istr:
                        data = yaml.load(istr)
                        data.pop('category', None)
                        data.pop('command', None)
                        data['id'] = run_dirs[i]
                        json.dump(data, ostr, indent=2)
                    if i != len(run_dirs) - 1:
                        ostr.write(',')
                    ostr.write('\n')
                ostr.write(']\n')

    @cached_property
    def metrics(self):
        """Get content of the JSON metrics file
        """
        with open(JSON_METRICS_FILE) as istr:
            return yaml.load(istr)

    def _generate_plot(self, desc, category):
        with open(JSON_METRICS_FILE) as istr:
            metrics = json.load(istr)
        plotter = Plotter(
            metrics,
            category=category,
            hostname=self.node
        )
        plotter(desc)


class MetricsDriver(object):
    """Abstract representation of metrics already
    built by a previous run
    """
    def __init__(self, campaign, benchmark):
        self.campaign = campaign
        self.benchmark = benchmark
        with open(YAML_REPORT_FILE) as istr:
            self.report = yaml.load(istr)

    @write_yaml_report
    def __call__(self, **kwargs):
        cat = self.report.get('category')
        all_extractors = self.benchmark.metrics_extractors
        if isinstance(all_extractors, Mapping):
            if cat not in all_extractors:
                raise Exception('No extractor for benchmark category %s' %
                                cat)
            extractors = all_extractors[cat]
        else:
            extractors = all_extractors
        if not isinstance(extractors, list):
            extractors = [extractors]
        metrics = self.report.setdefault('metrics', {})
        for extractor in extractors:
            run_metrics = extractor.extract(os.getcwd(),
                                            self.report.get('metas'))
            metrics.update(run_metrics)
        return self.report

    @classmethod
    def _check_metrics(cls, extractor, metrics):
        """Ensure that returned metrics are properly exposed
        """
        exposed_metrics = extractor.metrics
        for name, value in metrics.items():
            metric = exposed_metrics.get(name)
            if not metric:
                message = "Unexpected metric '{}' returned".format(name)
                raise Exception(message)
            elif not isinstance(value, metric.type):
                message = "Unexpected type for metrics {}".format(name)
                raise Exception(message)


class ExecutionDriver(Leaf):
    """Abstract representation of a benchmark command execution
    (a benchmark is made of several commands)
    """

    name = 'local'

    def __init__(self, parent, benchmark, execution):
        super(ExecutionDriver, self).__init__(parent)
        self.benchmark = benchmark
        self.execution = execution

    @property
    def command(self):
        """get command to execute

        :return: list of string
        """
        return self.execution['command']

    @cached_property
    def command_str(self):
        """get command to execute as string properly escaped

        :return: string
        """
        return ' '.join(map(
            six.moves.shlex_quote,
            self.command
        ))

    def _popen_env(self, kwargs):
        custom_env = self.execution.get('environment')
        if custom_env:
            env = copy.deepcopy(os.environ)
            env.update(custom_env)
            kwargs.update(env=env)

    def popen(self, stdout, stderr):
        """Build popen object to run

        :rtype: subprocess.Popen
        """
        kwargs = dict(stdout=stdout, stderr=stderr)
        self._popen_env(kwargs)
        self.logger.info('Executing command: %s', self.command_str)
        return subprocess.Popen(
            self.command,
            **kwargs
        )

    @write_yaml_report
    def __call__(self, **kwargs):
        self.benchmark.pre_execute()
        with open('stdout.txt', 'w') as stdout, \
                open('stderr.txt', 'w') as stderr:
            exit_status = self.popen(stdout, stderr).wait()
        self.benchmark.post_execute()
        report = dict(
            exit_status=exit_status,
            benchmark=self.benchmark.name,
        )
        report.update(self.execution)
        report.update(command=self.command)
        return report


class SlurmExecutionDriver(ExecutionDriver):
    """Manage process execution with srun (SLURM)
    """
    name = 'srun'

    @cached_property
    def srun(self):
        """Get path to srun executable

        :rtype: string
        """
        srun = self.campaign.process.config.get('srun') or 'srun'
        return find_executable(srun)

    @cached_property
    def common_srun_options(self):
        """Get options to be given to all srun commands

        :rtype: list of string
        """
        slurm_config = self.campaign.process.get('config', {})
        return slurm_config.get('options') or []

    @cached_property
    def command(self):
        """get command to execute

        :return: list of string
        """
        srun_options = copy.copy(self.common_srun_options)
        srun_options += self.execution.get('srun_options') or []
        srun_options.append('--nodelist=' + ','.join(self.srun_nodes))
        command = super(SlurmExecutionDriver, self).command
        return [self.srun] + srun_options + command

    @cached_property
    def srun_nodes(self):
        """Get list of nodes where to execute the command
        """
        count = self.execution.get('srun_nodes') or 1
        assert isinstance(count, int)
        assert count > 0
        tag = self.parent.parent.parent.name
        self.logger.info(tag)
        tag_nodes = self.parent.parent.parent.parent.nodes(tag)
        self.logger.info(tag_nodes)
        assert count <= len(tag_nodes)
        pos = tag_nodes.index(self.node)
        tag_nodes = tag_nodes + tag_nodes
        return tag_nodes[pos:pos + count]
