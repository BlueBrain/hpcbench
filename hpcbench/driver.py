import copy
import datetime
from functools import wraps
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


YAML_REPORT_FILE = 'hpcbench.yaml'
YAML_CAMPAIGN_FILE = 'campaign.yaml'


def write_yaml_report(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        with Timer() as timer:
            data = f(*args, **kwargs)
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
    def __init__(self, campaign, benchmark):
        super(BenchmarkDriver, self).__init__(campaign)
        self.benchmark = benchmark

    @write_yaml_report
    def __call__(self, **kwargs):
        if "no_exec" not in kwargs:
            for execution in self.benchmark.execution_matrix():
                run_dir = osp.join(
                    execution.get('category'),
                    execution.get('name') or '',
                    str(uuid.uuid4())
                )
                with pushd(run_dir, mkdir=True):
                    driver = ExecutionDriver(
                        self.campaign,
                        self.benchmark,
                        execution
                    )
                    driver(**kwargs)
                    MetricsDriver(self.campaign, self.benchmark)(**kwargs)
                    yield run_dir
        else:
            for child in self.report['children']:
                child_yaml = osp.join(child, YAML_REPORT_FILE)
                with open(child_yaml) as istr:
                    child_config = yaml.load(istr)
                child_config.pop('children', None)
                with pushd(child):
                    MetricsDriver(self.campaign, self.benchmark)(**kwargs)
                    yield child


class MetricsDriver(object):
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
            metrics.setdefault(cat, []).append(
                extractor.extract(os.getcwd(), self.report.get('metas'))
            )
        return self.report


class ExecutionDriver(object):
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
        )
        report.update(self.execution)
        return report
