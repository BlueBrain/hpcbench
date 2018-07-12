import glob
import json
import logging
import os
import re
import shlex
import uuid
from collections import namedtuple, Mapping
from os import path as osp

try:
    import magic
except ImportError:
    _HAS_MAGIC = False
else:
    _HAS_MAGIC = True

import six
import yaml
from cached_property import cached_property

from hpcbench.api import ExecutionContext, NoMetricException, Metric
from hpcbench.campaign import YAML_REPORT_FILE, JSON_METRICS_FILE
from .executor import ExecutionDriver, SrunExecutionDriver
from .base import Enumerator, ClusterWrapper, write_yaml_report, Leaf
from hpcbench.toolbox.buildinfo import extract_build_info
from hpcbench.toolbox.collections_ext import nameddict
from hpcbench.toolbox.contextlib_ext import pushd
from hpcbench.toolbox.edsl import kwargsql
from hpcbench.toolbox.functools_ext import listify
from hpcbench.toolbox.process import find_executable


class BenchmarkDriver(Enumerator):
    """Abstract representation of a benchmark, part of a campaign tag
    """

    def __init__(self, parent, benchmark, config):
        super(BenchmarkDriver, self).__init__(
            parent, benchmark.name, catch_child_exception=True
        )
        self.benchmark = benchmark
        self.config = BenchmarkDriver._prepare_config(config)

    @classmethod
    def _prepare_config(cls, config):
        config = dict(config)
        config.setdefault('srun_options', [])
        if isinstance(config['srun_options'], six.string_types):
            config['srun_options'] = shlex.split(config['srun_options'])
        config['srun_options'] = [str(e) for e in config['srun_options']]
        return config

    @cached_property
    def children(self):
        categories = set()
        for execution in self.execution_matrix:
            categories.add(execution['category'])
        return categories

    def child_builder(self, child):
        return BenchmarkCategoryDriver(self, child)

    @cached_property
    def exec_context(self):
        tag = self.parent.name
        cluster = ClusterWrapper(self.root.network, tag, self.node)
        return ExecutionContext(
            cluster=cluster,
            logger=self.logger,
            node=self.node,
            srun_options=self.config['srun_options'],
            tag=tag,
        )

    @property
    def execution_matrix(self):
        return self.benchmark.execution_matrix(self.exec_context)


class BenchmarkCategoryDriver(Enumerator):
    """Abstract representation of one benchmark to execute
    (one of "benchmarks" YAML tag values")"""

    def __init__(self, parent, category):
        super(BenchmarkCategoryDriver, self).__init__(parent, category)
        self.category = category
        self.benchmark = self.parent.benchmark
        self.config = parent.config
        self.exec_context = parent.exec_context

    @cached_property
    def commands(self):
        """Get all commands of the benchmark category

        :return generator of string
        """
        for child in self._children:
            with open(osp.join(child, YAML_REPORT_FILE)) as istr:
                command = yaml.safe_load(istr)['command']
                yield ' '.join(map(six.moves.shlex_quote, command))

    @cached_property
    @listify
    def children(self):
        for execution in self.parent.execution_matrix:
            category = execution.get('category')
            if category != self.category:
                continue
            # Override `environment` if specified in YAML
            if 'environment' in self.config:
                yaml_env = self.config.get('environment')
                if not yaml_env:
                    # empty dict or None wipes environment
                    execution['environment'] = {}
                else:
                    env = execution.setdefault('environment', {})
                    for name, value in yaml_env.items():
                        if value is None:
                            env.pop(name, None)
                        else:
                            env[name] = value
                    if not env:
                        self.config.pop('environment')
            # Override `modules` if specified in YAML
            if 'modules' in self.config:
                yaml_modules = self.config['modules'] or []
                execution['modules'] = list(yaml_modules)
            # Enrich `metas` if specified in YAML
            if 'metas' in self.campaign:
                metas = dict(self.campaign.metas)
                metas.update(execution.setdefault('metas', {}))
                execution['metas'] = metas
            name = execution.get('name') or ''
            yield execution, osp.join(name, self.child_id())

    def child_id(self):
        while True:
            child_id = str(uuid.uuid4()).split('-', 2)[0]
            if not hasattr(self, '__child_ids'):
                self.__child_ids = set()
            if child_id not in self.__child_ids:
                self.__child_ids.add(child_id)
                break
        return child_id

    def child_builder(self, child):
        del child  # unused

    def attempt_run_class(self, execution):
        config = self.parent.config.get('attempts')
        if config:
            fixed = config.get('fixed')
            if fixed is not None:
                assert isinstance(fixed, int)
                return FixedAttempts
            return DynamicAttempts
        return FixedAttempts

    @write_yaml_report
    @Enumerator.call_decorator
    def __call__(self, **kwargs):
        if "no_exec" not in kwargs:
            for run_dir in self._execute(**kwargs):
                yield run_dir
        else:
            self._extract_metrics(**kwargs)

    def _extract_metrics(self, **kwargs):
        runs = dict()
        for child in self.report['children']:
            child_yaml = osp.join(child, YAML_REPORT_FILE)
            with open(child_yaml) as istr:
                child_config = yaml.safe_load(istr)
            child_config.pop('children', None)
            runs.setdefault(self.category, []).append(child)
            with pushd(child):
                MetricsDriver(self, self.benchmark)(**kwargs)
        self.gather_metrics(runs)

    def _add_build_info(self, execution):
        executable = execution['command'][0]
        try:
            exepath = find_executable(executable, required=True)
        except NameError:
            self.logger.info(
                "Could not find exe %s to examine for build info", executable
            )
        else:
            try:
                file_type = magic.from_file(osp.realpath(exepath))
            except IOError as exc:
                self.logger.warn('Could not find file type of %s: %s', exepath, exc)
            else:
                if file_type.startswith('ELF'):
                    binfo = extract_build_info(exepath)
                    if binfo:
                        execution.setdefault('metas', {})['build_info'] = binfo
                else:
                    self.logger.info('%s is not pointing to an ELF executable', exepath)

    def _execute(self, **kwargs):
        runs = dict()
        for execution, run_dir in self.children:
            if _HAS_MAGIC and 'shell' not in execution:
                self._add_build_info(execution)
            else:
                self.logger.info(
                    "No build information recorded " "(libmagic available: %s)",
                    _HAS_MAGIC,
                )
            runs.setdefault(execution['category'], []).append(run_dir)
            with pushd(run_dir, mkdir=True):
                attempt_cls = self.attempt_run_class(execution)
                attempt = attempt_cls(self, execution)
                for attempt in attempt(**kwargs):
                    pass
                yield run_dir
        self.gather_metrics(runs)

    def gather_metrics(self, runs):
        """Write a JSON file with the result of every runs
        """
        for run_dirs in runs.values():
            with open(JSON_METRICS_FILE, 'w') as ostr:
                ostr.write('[\n')
                for i in range(len(run_dirs)):
                    with open(osp.join(run_dirs[i], YAML_REPORT_FILE)) as istr:
                        data = yaml.safe_load(istr)
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
            return json.load(istr)


class MetricsDriver(Leaf):
    """Abstract representation of metrics already
    built by a previous run
    """

    def __init__(self, parent, benchmark):
        super(MetricsDriver, self).__init__(parent)
        self.campaign = parent.campaign
        self.benchmark = benchmark

    @write_yaml_report
    @Enumerator.call_decorator
    def __call__(self, **kwargs):
        with open(YAML_REPORT_FILE) as istr:
            report = yaml.safe_load(istr)
        cat = report.get('category')
        metas = report.get('metas')
        all_extractors = self.benchmark.metrics_extractors
        if isinstance(all_extractors, Mapping):
            if cat not in all_extractors:
                raise Exception('No extractor for benchmark category %s' % cat)
            extractors = all_extractors[cat]
        else:
            extractors = all_extractors
        if not isinstance(extractors, list):
            extractors = [extractors]
        all_metrics = report.setdefault('metrics', [])
        for log in self.logs:
            metrics = {}
            for extractor in extractors:
                with extractor.context(log.path, log.log_prefix):
                    try:
                        run_metrics = extractor.extract(metas)
                    except NoMetricException:
                        pass
                    else:
                        MetricsDriver._check_metrics(extractor.metrics, run_metrics)
                        metrics.update(run_metrics)
            if metrics:
                rc = dict(context=log.context, measurement=metrics)
                all_metrics.append(rc)
        if self.benchmark.metric_required and not all_metrics:
            # at least one of the logs must provide metrics
            raise NoMetricException()
        return report

    class LocalLog(namedtuple('LocalLog', ['path', 'log_prefix'])):
        @property
        def context(self):
            return dict(executor='local')

    class SrunLog(namedtuple('SrunLog', ['path', 'log_prefix', 'node', 'rank'])):
        @property
        def context(self):
            return dict(executor='slurm', node=self.node, rank=self.rank)

    @property
    def logs(self):

        if self.report['executor'] == 'local':
            yield MetricsDriver.LocalLog(path=os.getcwd(), log_prefix='')
        else:
            STDOUT_RE_PATTERN = r'slurm-(\w+)-(\w+)\.stdout'
            STDOUT_RE = re.compile(STDOUT_RE_PATTERN)
            for file in glob.glob('slurm-*-*.stdout'):
                match = STDOUT_RE.match(file)
                if match:
                    node, rank = match.groups()
                    yield MetricsDriver.SrunLog(
                        path=os.getcwd(), log_prefix=file[:-6], node=node, rank=rank
                    )
                else:
                    logging.warn(
                        '"%s" does not match regular expression "%s"',
                        file,
                        STDOUT_RE_PATTERN,
                    )

    @classmethod
    def _check_metrics(cls, schema, metrics):
        """Ensure that returned metrics are properly exposed
        """
        for name, value in metrics.items():
            metric = schema.get(name)
            if not metric:
                message = "Unexpected metric '{}' returned".format(name)
                raise Exception(message)
            cls._check_metric(schema, metric, name, value)

    @classmethod
    def _check_metric(cls, schema, metric, name, value):
        if isinstance(metric, Metric):
            if not isinstance(value, metric.type):
                message = "Unexpected type for metrics {}:\n".format(name)
                message += "expected {}, but got {}".format(metric.type, type(value))
                raise Exception(message)
        elif isinstance(metric, list):
            if not isinstance(value, list):
                message = "Unexpected type for metrics {}".format(name)
                message += "expected {}, but got {}".format(list, type(value))
                raise Exception(message)
            for item in value:
                cls._check_metric(schema, metric[0], name, item)
        elif isinstance(metric, dict):
            if not isinstance(value, dict):
                message = "Unexpected type for metrics {}".format(name)
                message += "expected {}, but got {}".format(dict, type(value))
                raise Exception(message)
            cls._check_metrics(metric, value)
        else:
            message = "benchmark metric {} is neither ".format(metric)
            message += "a Metric, dict or list"
            raise Exception(message)


class FixedAttempts(Enumerator):
    def __init__(self, parent, execution):
        super(FixedAttempts, self).__init__(parent)
        self.execution = execution
        self.paths = []
        self.config = parent.config
        self.exec_context = parent.exec_context

    __call__ = Enumerator._call_without_report

    @property
    def benchmark(self):
        return self.parent.benchmark

    @cached_property
    def attempts_config(self):
        return self.parent.parent.config.get('attempts', {})

    @cached_property
    def attempts(self):
        return self.attempts_config.get('fixed', 1)

    @property
    def children(self):
        attempt = 1
        self.paths = []
        while self._should_run(attempt):
            path = 'attempt-' + str(attempt)
            self.paths.append(path)
            yield path
            attempt += 1
        attempt_path = self.last_attempt()
        for file_ in os.listdir(attempt_path):
            os.symlink(osp.join(attempt_path, file_), file_)

    def child_builder(self, child):
        def _wrap(**kwargs):
            driver = self.execution_layer()
            driver(**kwargs)
            if self.report['command_succeeded']:
                MetricsDriver(self, self.benchmark)(**kwargs)
            return self.report

        return _wrap

    def _should_run(self, attempt):
        return attempt <= self.attempts

    @cached_property
    def execution_layer_class(self):
        """Get execution layer class
        """
        name = self.campaign.process.type
        for clazz in [ExecutionDriver, SrunExecutionDriver]:
            if name == clazz.name:
                return clazz
        raise NameError("Unknown execution layer: '%s'" % name)

    def execution_layer(self):
        """Build the proper execution layer
        """
        return self.execution_layer_class(self)

    def last_attempt(self):
        self._sort_attempts()
        return self.paths[-1]

    def _sort_attempts(self):
        if self.sort_config is not None:
            attempts = []
            for path in self.paths:
                with open(osp.join(path, YAML_REPORT_FILE)) as istr:
                    report = yaml.safe_load(istr)
                report['path'] = path
                attempts.append(report)
            attempts = sorted(attempts, **self.sort_config)
            self.paths = [report_['path'] for report_ in attempts]

    @cached_property
    def sort_config(self):
        config = self.attempts_config.get('sorted')
        if config is not None:
            sql = config.pop('sql', None)
            if sql is not None:
                if not isinstance(sql, list):
                    sql = [sql]

                def key_func(report):
                    return tuple([kwargsql.get(report, query) for query in sql])

                config['key'] = key_func
        return config


class DynamicAttempts(FixedAttempts):
    def __init__(self, parent, execution):
        super(DynamicAttempts, self).__init__(parent, execution)

    @cached_property
    def metric(self):
        return self.attempts_config['metric']

    @cached_property
    def attempts(self):
        return self.attempts_config['maximum']

    @cached_property
    def epsilon(self):
        return self.attempts_config.get('epsilon')

    @cached_property
    def percent(self):
        return self.attempts_config.get('percent')

    def _should_run(self, attempt):
        if attempt > self.attempts:
            return False
        if attempt < 3:
            return True
        with open(osp.join(self.paths[-2], YAML_REPORT_FILE)) as istr:
            data_n1 = nameddict(yaml.safe_load(istr))
        with open(osp.join(self.paths[-1], YAML_REPORT_FILE)) as istr:
            data_n = nameddict(yaml.safe_load(istr))
        return not self._metric_converged(data_n1, data_n)

    def _metric_converged(self, data_n1, data_n):
        def get_metric(report):
            # Only use first command result
            return report['metrics'][0]['measurement'][self.metric]

        value_n1 = get_metric(data_n1)
        value_n = get_metric(data_n)
        if self.epsilon is not None:
            return abs(value_n - value_n1) < self.epsilon
        assert self.percent is not None
        return abs(value_n - value_n1) < self.percent / 100.0
