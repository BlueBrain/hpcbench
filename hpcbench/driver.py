import copy
import datetime
from functools import wraps
import os
import os.path as osp
import socket
import subprocess
import types
import uuid

from cached_property import cached_property
import yaml

from . toolbox.collections_ext import (
    nameddict,
)
from . toolbox.contextlib_ext import (
    pushd,
    Timer,
)
from . api import BenchmarkLibrary


YAML_REPORT_FILE = 'hpcbench.yaml'


def write_yaml_report(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        with Timer() as timer:
            data = f(*args, **kwargs)
            if isinstance(data, (list, types.GeneratorType)):
                report = dict(children=list(data))
            elif isinstance(data, dict):
                report = data
            else:
                raise Exception('Unexpected data type: %s', type(data))
        report['elapsed'] = timer.elapsed
        if report is not None:
            with open(YAML_REPORT_FILE, 'w') as ostr:
                yaml.dump(report, ostr, default_flow_style=False)
        return report
    return wrapper


class CampaignDriver(object):
    """Perform benchmarks execution"""
    def __init__(self, campaign):
        self.campaign = campaign

    @cached_property
    def output_dir(self):
        return osp.join(
            datetime.datetime.now().strftime(self.campaign.output_dir),
            socket.gethostname()
        )

    @cached_property
    def benchmarks(self):
        """Retrieve tags associated to the current node"""
        hostnames = {'localhost', socket.gethostname()}
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

    def __call__(self, **kwargs):
        """execute benchmarks"""
        with pushd(self.output_dir, mkdir=True):
            self.run(**kwargs)

    @write_yaml_report
    def run(self, **kwargs):
        for benchmark in self.benchmarks:
            with pushd(benchmark, mkdir=True):
                BenchmarkTagDriver(self.campaign, benchmark)(**kwargs)
                yield benchmark


class BenchmarkTagDriver(object):
    def __init__(self, campaign, name):
        self.campaign = campaign
        self.name = name

    @cached_property
    def benchmarks(self):
        benchmarks = []
        for benchmark in self.campaign.benchmarks[self.name]:
            for name, config in benchmark.items():
                config = nameddict(config)
                benchmarks.append(self.instantiate_benchmark(config))
        return benchmarks

    def instantiate_benchmark(self, config):
        benchmark = BenchmarkLibrary.get(config.type)()
        if 'attributes' in config:
            benchmark.attributes = copy.deepcopy(config.attributes)
        return benchmark

    @write_yaml_report
    def __call__(self, **kwargs):
        for benchmark in self.benchmarks:
            with pushd(benchmark.name, mkdir=True):
                BenchmarkDriver(self.campaign, benchmark)(**kwargs)
                yield benchmark.name


class BenchmarkDriver(object):
    def __init__(self, campaign, benchmark):
        self.campaign = campaign
        self.benchmark = benchmark

    @write_yaml_report
    def __call__(self, **kwargs):
        for execution in self.benchmark.execution_matrix():
            run_dir = osp.join(
                execution.get('category'),
                execution.get('name') or '',
                str(uuid.uuid4())
            )
            with pushd(run_dir, mkdir=True):
                ExecutionDriver(self.campaign, self.benchmark, execution)(**kwargs)
                MetricsDriver(self.campaign, self.benchmark)(**kwargs)
                yield run_dir


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
