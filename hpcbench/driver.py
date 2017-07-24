"""Campaign execution and post-processing
"""
import copy
import datetime
from functools import wraps
import json
import os
import os.path as osp
import shutil
import socket
import subprocess
import types
import uuid

from cached_property import cached_property
import yaml

from . toolbox.contextlib_ext import (
    pushd,
    Timer,
)
from . api import Benchmark
from . campaign import from_file
from . plot import Plotter


YAML_REPORT_FILE = 'hpcbench.yaml'
YAML_CAMPAIGN_FILE = 'campaign.yaml'
JSON_METRICS_FILE = 'metrics.json'


def write_yaml_report(func):
    """Decorator used to campaign node post-processing
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        with Timer() as timer:
            data = func(*args, **kwargs)
            if isinstance(data, (list, types.GeneratorType)):
                report = dict(children=list(map(str, data)))
            elif isinstance(data, dict):
                report = data
            else:
                raise Exception('Unexpected data type: %s', type(data))
        report['elapsed'] = timer.elapsed
        if "no_exec" not in kwargs and report is not None:
            with open(YAML_REPORT_FILE, 'w') as ostr:
                yaml.dump(report, ostr, default_flow_style=False)
        return report
    return wrapper


class Enumerator(object):
    """Common class for every campaign node"""
    def __init__(self, campaign):
        self.campaign = campaign

    @cached_property
    def report(self):
        with open(YAML_REPORT_FILE) as istr:
            return yaml.load(istr)

    @write_yaml_report
    def __call__(self, **kwargs):
        for child in self._children:
            with pushd(str(child), mkdir=True):
                child_obj = self.child_builder(child)
                child_obj(**kwargs)
                yield child

    def child_builder(self, child):
        raise NotImplementedError

    @cached_property
    def _children(self):
        if osp.isfile(YAML_REPORT_FILE):
            return self.report['children']
        return self.children

    @cached_property
    def children(self):
        """Property to be overriden be subclass to provide child objects"""
        raise NotImplementedError


class CampaignDriver(Enumerator):
    """Abstract representation of an entire campaign"""
    def __init__(self, campaign_file=None, campaign_path=None):
        if campaign_file and campaign_path:
            raise Exception('Either campaign_file xor path can be specified')
        if campaign_path:
            campaign_file = osp.join(campaign_path, YAML_CAMPAIGN_FILE)
        self.campaign_file = osp.abspath(campaign_file)
        super(CampaignDriver, self).__init__(
            campaign=from_file(campaign_file)
        )
        if campaign_path:
            self.existing_campaign = True
            self.campaign_path = campaign_path
        else:
            self.existing_campaign = False
            now = datetime.datetime.now()
            self.campaign_path = now.strftime(self.campaign.output_dir)

    def child_builder(self, child):
        return HostDriver(self.campaign, child)

    @cached_property
    def children(self):
        return [socket.gethostname()]

    def __call__(self, **kwargs):
        """execute benchmarks"""
        with pushd(self.campaign_path, mkdir=True):
            if not self.existing_campaign:
                shutil.copy(self.campaign_file, YAML_CAMPAIGN_FILE)
            super(CampaignDriver, self).__call__(**kwargs)


class HostDriver(Enumerator):
    """Abstract representation of the campaign for the current host"""
    def __init__(self, campaign, name):
        super(HostDriver, self).__init__(campaign)
        self.name = name

    @cached_property
    def children(self):
        """Retrieve tags associated to the current node"""
        hostnames = {'localhost', self.name}
        benchmarks = set()
        for tag, configs in self.campaign.network.tags.items():
            for config in configs:
                for mode, kconfig in config.items():
                    if mode == 'match':
                        for host in hostnames:
                            if kconfig.match(host):
                                benchmarks.add(tag)
                                break
                    elif mode == 'nodes':
                        if hostnames & kconfig:
                            benchmarks.add(tag)
                            break
                    else:
                        raise Exception('Unknown tag association pattern: %s',
                                        mode)
                if tag in benchmarks:
                    break
        return benchmarks

    def child_builder(self, child):
        return BenchmarkTagDriver(self.campaign, child)


class BenchmarkTagDriver(Enumerator):
    """Abstract representation of a campaign tag
    (keys of "benchmark" YAML tag)"""
    def __init__(self, campaign, name):
        super(BenchmarkTagDriver, self).__init__(campaign)
        self.name = name

    @cached_property
    def children(self):
        return list(self.campaign.benchmarks[self.name])

    def child_builder(self, child):
        conf = self.campaign.benchmarks[self.name][child]
        benchmark = Benchmark.get_subclass(conf['type'])()
        if 'attributes' in conf:
            benchmark.attributes = copy.deepcopy(conf['attributes'])
        return BenchmarkDriver(self.campaign, benchmark)


class BenchmarkDriver(Enumerator):
    """Abstract representation of one benchmark to execute
    (one of "benchmarks" YAML tag values")"""
    def __init__(self, campaign, benchmark):
        super(BenchmarkDriver, self).__init__(campaign)
        self.benchmark = benchmark

    @write_yaml_report
    def __call__(self, **kwargs):
        if "no_exec" not in kwargs:
            runs = dict()
            for execution in self.benchmark.execution_matrix():
                category = execution.get('category')
                name = execution.get('name') or ''
                run_dir = osp.join(
                    category,
                    name,
                    str(uuid.uuid4())
                )
                runs.setdefault(category, []).append(run_dir)
                with pushd(run_dir, mkdir=True):
                    driver = ExecutionDriver(
                        self.campaign,
                        self.benchmark,
                        execution
                    )
                    driver(**kwargs)
                    MetricsDriver(self.campaign, self.benchmark)(**kwargs)
                    yield run_dir
            self.gather_metrics(runs)
        elif 'plot' in kwargs:
            for category, plots in self.benchmark.plots().items():
                with pushd(category):
                    for plot in plots:
                        self.generate_plot(plot, category)
        else:
            runs = dict()
            for child in self.report['children']:
                child_yaml = osp.join(child, YAML_REPORT_FILE)
                with open(child_yaml) as istr:
                    child_config = yaml.load(istr)
                child_config.pop('children', None)
                category, _ = child.split(os.sep, 1)
                runs.setdefault(category, []).append(child)
                with pushd(child):
                    MetricsDriver(self.campaign, self.benchmark)(**kwargs)
                    yield child
            self.gather_metrics(runs)

    def gather_metrics(self, runs):
        for category, run_dirs in runs.items():
            with open(osp.join(category, JSON_METRICS_FILE), 'w') as ostr:
                ostr.write('[\n')
                for i in range(len(run_dirs)):
                    with open(osp.join(run_dirs[i], YAML_REPORT_FILE)) as istr:
                        data = yaml.load(istr)
                        data.pop('category', None)
                        data.pop('command', None)
                        gathered_metrics = dict()
                        for cat, metricss in data.get('metrics', {}).items():
                            gathered = dict()
                            for metrics in metricss:
                                gathered.update(metrics)
                            gathered_metrics[cat] = gathered
                        data['metrics'] = gathered_metrics
                        json.dump(data, ostr, indent=2)
                    if i != len(run_dirs) - 1:
                        ostr.write(',')
                    ostr.write('\n')
                ostr.write(']\n')

    def generate_plot(self, desc, category):
        with open(JSON_METRICS_FILE) as istr:
            metrics = json.load(istr)
        plotter = Plotter(
            metrics,
            category=category,
            hostname=socket.gethostname()
        )
        plotter(desc)


class MetricsDriver(object):
    """Abstract representation of metrics already
    built by a previous run"""
    def __init__(self, campaign, benchmark):
        self.campaign = campaign
        self.benchmark = benchmark
        with open(YAML_REPORT_FILE) as istr:
            self.report = yaml.load(istr)

    @write_yaml_report
    def __call__(self, **kwargs):
        cat = self.report.get('category')
        all_extractors = self.benchmark.metrics_extractors()
        if cat not in all_extractors:
            raise Exception('No extractor for benchmark category %s' %
                            cat)
        extractors = all_extractors[cat]
        if not isinstance(extractors, list):
            extractors = [extractors]
        metrics = self.report.setdefault('metrics', {})
        for extractor in extractors:
            run_metrics = extractor.extract(os.getcwd(),
                                            self.report.get('metas'))
            self.check_metrics(extractor, run_metrics)
            metrics.setdefault(cat, []).append(run_metrics)
        return self.report

    def check_metrics(self, extractor, metrics):
        """Ensure that returned metrics are properly exposed"""
        exposed_metrics = extractor.metrics()
        for name, value in metrics.items():
            metric = exposed_metrics.get(name)
            if not metric:
                message = "Unexpected metric '{}' returned".format(name)
                raise Exception(message)
            elif not isinstance(value, metric['type']):
                message = "Unexpected type for metrics {}".format(name)
                raise Exception(message)


class ExecutionDriver(object):
    """Abstract representation of a benchmark command execution
    (a benchmark is made of several commands)
    """
    def __init__(self, campaign, benchmark, execution):
        self.campaign = campaign
        self.benchmark = benchmark
        self.execution = execution

    @write_yaml_report
    def __call__(self, **kwargs):
        with open('stdout.txt', 'w') as stdout, \
             open('stderr.txt', 'w') as stderr:
            kwargs = dict(stdout=stdout, stderr=stderr)
            custom_env = self.execution.get('environment')
            if custom_env:
                env = copy.deepcopy(os.environ)
                env.update(custom_env)
                kwargs.update(env=env)
            process = subprocess.Popen(
                self.execution['command'],
                **kwargs
            )
            exit_status = process.wait()
        report = dict(
            exit_status=exit_status,
            benchmark=self.benchmark.name,
        )
        report.update(self.execution)
        return report
