"""Campaign execution and post-processing
"""
from __future__ import print_function

from abc import (
    ABCMeta,
    abstractmethod,
    abstractproperty,
)
import argparse
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
import shlex
import shutil
import socket
import stat
import subprocess
import tempfile
import types
import uuid

from cached_property import cached_property
try:
    import magic
except ImportError:
    _HAS_MAGIC = False
else:
    _HAS_MAGIC = True
import six
import yaml

from . import jinja_environment
from . api import (
    Benchmark,
    ExecutionContext,
    Metric,
)
from . campaign import from_file
from . plot import Plotter
from . toolbox.buildinfo import extract_build_info
from . toolbox.collections_ext import (
    dict_merge,
    nameddict,
)
from . toolbox.contextlib_ext import (
    pushd,
    Timer,
)
from . toolbox.edsl import kwargsql
from . toolbox.functools_ext import listify
from . toolbox.process import find_executable

LOGGER = logging.getLogger('hpcbench')
YAML_REPORT_FILE = 'hpcbench.yaml'
YAML_CAMPAIGN_FILE = 'campaign.yaml'
JSON_METRICS_FILE = 'metrics.json'
LOCALHOST = 'localhost'


class ConstraintTag(object):
    def __init__(self, name, constraint):
        self._name = name
        self._constraint = constraint

    @property
    def name(self):
        return self._name

    @property
    def constraint(self):
        return self._constraint


def write_yaml_report(func):
    """Decorator used in campaign node post-processing
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
        self.root = parent.root
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
    def has_children(self):
        return len(self.children) > 0

    @cached_property
    def report(self):
        """Get object report. Content of ``YAML_REPORT_FILE``
        """
        with open(YAML_REPORT_FILE) as istr:
            return nameddict(yaml.safe_load(istr))

    def children_objects(self):
        for child in self._children:
            yield self.child_builder(child)

    def _call_without_report(self, **kwargs):
        for child in self._children:
            child_obj = self.child_builder(child)
            with pushd(str(child), cleanup=isinstance(child_obj, Enumerator)
                       and not child_obj.has_children):
                child_obj(**kwargs)
                yield child

    @write_yaml_report
    def __call__(self, **kwargs):
        return self._call_without_report(**kwargs)

    @property
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

    @cached_property
    def children(self):
        return []


Top = namedtuple('top', ['campaign', 'node', 'logger', 'root'])
Top.__new__.__defaults__ = (None, ) * len(Top._fields)


class Network(object):
    def __init__(self, campaign):
        self.campaign = campaign

    def has_tag(self, tag):
        return tag in self.campaign.network.tags

    def nodes(self, tag):
        """get list of nodes that belong to a tag
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
                nodes = nodes.union(set([
                    node for node in self.campaign.network.nodes
                    if value.match(node)
                ]))
            elif mode == 'constraint':
                return ConstraintTag(tag, value)
            else:
                assert mode == 'nodes'
                nodes = nodes.union(set(value))
        return sorted(list(nodes))


class CampaignDriver(Enumerator):
    """Abstract representation of an entire campaign"""
    def __init__(self, campaign_file=None, campaign_path=None,
                 node=None, output_dir=None, srun=None,
                 logger=None, expandcampvars=True):
        node = node or socket.gethostname()
        if campaign_file and campaign_path:
            raise Exception('Either campaign_file xor path can be specified')
        if campaign_path:
            campaign_file = osp.join(campaign_path, YAML_CAMPAIGN_FILE)
        self.campaign_file = osp.abspath(campaign_file)
        super(CampaignDriver, self).__init__(
            Top(
                campaign=from_file(campaign_file, expandcampvars),
                node=node,
                logger=logger or LOGGER,
                root=self
            ),
        )
        self.network = Network(self.campaign)
        self.filter_tag = srun
        if srun:  # overwrite process type and force srun when requested
            self.campaign.process.type = 'srun'
        if campaign_path:
            self.existing_campaign = True
            self.campaign_path = campaign_path
        else:
            self.existing_campaign = False
            now = datetime.datetime.now()
            self.campaign_path = now.strftime(output_dir or
                                              self.campaign.output_dir)
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
                        yaml.dump(self.campaign, ostr,
                                  default_flow_style=False)
            super(CampaignDriver, self).__call__(**kwargs)


class SlurmDriver(Enumerator):
    """Abstract representation of the campaign for the current cluster"""

    SBATCH_JINJA = 'sbatch.jinja'

    def __init__(self, parent):
        super(SlurmDriver, self).__init__(parent)
        self.campaign.process.setdefault('sbatch_template',
                                         self.SBATCH_JINJA)
        LOGGER.info("We are in SLURM/SBATCH mode")

    @cached_property
    def children(self):
        bench_tags = set([tag for tag in self.campaign.benchmarks
                          if any(self.campaign.benchmarks[tag])])

        cluster_tags = bench_tags & set(self.campaign.network.tags)
        return list(cluster_tags)

    def child_builder(self, child):
        return SbatchDriver(self, child)


class SbatchDriver(Enumerator):
    """Abstract representation of sbatch jobs created for each non-empty tag"""

    def __init__(self, parent, tag):
        super(SbatchDriver, self).__init__(parent, name=tag)
        self.tag = tag
        now = datetime.datetime.now()
        sbatch_filename = '{tag}-%Y%m%d-%H%M%S.sbatch'
        cmd = ('ben-sh --srun={tag} '
               + '-n $SLURMD_NODENAME '
               + '--output-dir={tag}-%Y%m%d-%H%M%S '
               + self.parent.parent.campaign_file)
        self.sbatch_filename = now.strftime(sbatch_filename)
        self.sbatch_filename = self.sbatch_filename.format(tag=tag)
        self.sbatch_outdir = osp.splitext(self.sbatch_filename)[0]
        self.hpcbench_cmd = now.strftime(cmd)
        self.hpcbench_cmd = self.hpcbench_cmd.format(tag=tag)

    @cached_property
    def sbatch_args(self):
        sbatch_options = self.campaign.process.get('sbatch', {})
        if 'constraint' not in sbatch_options:
            tag = self.root.network.nodes(self.tag)
            if isinstance(tag, ConstraintTag):
                sbatch_options['constraint'] = tag.constraint
        return sbatch_options

    @cached_property
    def children(self):
        return [self.tag]

    def child_builder(self, child):
        del child  # not needed

    @property
    def sbatch_template(self):
        """:return Jinja sbatch template for the current tag"""
        templates = self.campaign.process.sbatch_template
        if isinstance(templates, Mapping):
            # find proper template according to the tag
            template = templates.get(self.tag)
            if template is None:
                template = templates.get('*')
            if template is None:
                template = self.parent.SBATCH_JINJA
        else:
            template = templates
        if template.startswith('#!'):
            # script is embedded in YAML
            return jinja_environment.from_string(template)
        return jinja_environment.get_template(template)

    @write_yaml_report
    def __call__(self, **kwargs):
        with open(self.sbatch_filename, 'w') as sbatch:
            self._create_sbatch(sbatch)
        sbatch_jobid = self._execute_sbatch()
        return dict(sbatch=self.sbatch_filename,
                    jobid=sbatch_jobid,
                    children=[self.sbatch_outdir])

    def _create_sbatch(self, ostr):
        """Write sbatch template to output stream
        :param ostr: opened file to write to
        """
        properties = dict(
            sbatch_arguments={k: six.moves.shlex_quote(str(v))
                              for k, v in self.sbatch_args.items()},
            hpcbench_command=self.hpcbench_cmd
        )
        self.sbatch_template.stream(**properties).dump(ostr)

    def _execute_sbatch(self):
        """Schedule the sbatch file using the sbatch command
        :returns the slurm job id
        """
        commands = self.campaign.process.get('commands', {})
        sbatch = find_executable(commands.get('sbatch', 'sbatch'))
        sbatch_command = [sbatch, '--parsable', self.sbatch_filename]
        sbatch_out = subprocess.check_output(sbatch_command,
                                             universal_newlines=True)
        jobid = sbatch_out.split(';')[0]
        LOGGER.info("Submitted SBATCH job %s for tag %s",
                    jobid, self.tag)
        return int(jobid)


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
                        if (kconfig.match(self.name) or
                                kconfig.match(LOCALHOST)):
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
            name for name in
            self.campaign.benchmarks.get(self.name, [])
            if self._precondition_is_met(name)
        ]

    def _precondition_is_met(self, name):
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
            dict_merge(
                benchmark.attributes,
                conf['attributes']
            )
        return BenchmarkDriver(self, benchmark, conf)


class BenchmarkDriver(Enumerator):
    """Abstract representation of a benchmark, part of a campaign tag
    """
    def __init__(self, parent, benchmark, config):
        super(BenchmarkDriver, self).__init__(parent, benchmark.name)
        self.benchmark = benchmark
        self.config = BenchmarkDriver._prepare_config(config)

    @classmethod
    def _prepare_config(cls, config):
        config.setdefault('srun_options', [])
        if isinstance(config['srun_options'], six.string_types):
            config['srun_options'] = shlex.split(config['srun_options'])
        config['srun_options'] = [
            str(e)
            for e in config['srun_options']
        ]
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
        return ExecutionContext(
            node=self.node,
            tag=self.parent.name,
            nodes=self.root.network.nodes(self.parent.name),
            logger=self.logger,
            srun_options=self.config['srun_options']
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
                command = yaml.safe_load(istr)['command']
                yield ' '.join(map(six.moves.shlex_quote, command))

    @cached_property
    @listify
    def children(self):
        for execution in self.parent.execution_matrix:
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
    def __call__(self, **kwargs):
        if "no_exec" not in kwargs:
            for run_dir in self._execute(**kwargs):
                yield run_dir
        elif 'plot' in kwargs:
            for plot in self.benchmark.plots.get(self.category):
                self._generate_plot(plot, self.category)
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
                MetricsDriver(self.campaign, self.benchmark)(**kwargs)
        self.gather_metrics(runs)

    def _add_build_info(self, execution):
        executable = execution['command'][0]
        try:
            exepath = find_executable(executable, required=True)
        except NameError:
            LOGGER.info("Could not find exe %s to examine for build info",
                        executable)
        else:
            if magic.from_file(exepath).startswith('ELF'):
                if 'metas' not in execution or execution['metas'] is None:
                    execution['metas'] = dict()
                execution['metas']['build_info'] = extract_build_info(exepath)
            else:
                LOGGER.info('%s is not pointing to an ELF executable', exepath)

    def _execute(self, **kwargs):
        runs = dict()
        for execution, run_dir in self.children:
            if _HAS_MAGIC and 'shell' not in execution:
                self._add_build_info(execution)
            else:
                LOGGER.info("No build information recorded "
                            + "(libmagic available: %s)", _HAS_MAGIC)
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
            return yaml.safe_load(istr)

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
            self.report = yaml.safe_load(istr)

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
            MetricsDriver._check_metrics(extractor.metrics, run_metrics)
            metrics.update(run_metrics)
        return self.report

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
                message += "expected {}, but got {}".format(metric.type,
                                                            type(value))
                raise Exception(message)
        elif isinstance(metric, list):
            if not isinstance(value, list):
                message = "Unexpected type for metrics {}".format(name)
                message += "expected {}, but got {}".format(list,
                                                            type(value))
                raise Exception(message)
            for item in value:
                cls._check_metric(schema, metric[0], name, item)
        elif isinstance(metric, dict):
            if not isinstance(value, dict):
                message = "Unexpected type for metrics {}".format(name)
                message += "expected {}, but got {}".format(dict,
                                                            type(value))
                raise Exception(message)
            cls._check_metrics(metric, value)


class FixedAttempts(Enumerator):
    def __init__(self, parent, execution):
        super(FixedAttempts, self).__init__(parent)
        self.execution = execution
        self.paths = []

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
            path = str(uuid.uuid4())
            self.paths.append(path)
            yield path
            attempt += 1
        attempt_path = self.last_attempt()
        for file_ in os.listdir(attempt_path):
            os.symlink(
                osp.join(attempt_path, file_),
                file_
            )

    def child_builder(self, child):
        def _wrap(**kwargs):
            driver = self.execution_layer()
            driver(**kwargs)
            mdriver = MetricsDriver(self.campaign, self.benchmark)
            mdriver(**kwargs)
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
            self.paths = [
                report_['path']
                for report_ in attempts
            ]

    @cached_property
    def sort_config(self):
        config = self.attempts_config.get('sorted')
        if config is not None:
            sql = config.pop('sql', None)
            if sql is not None:
                if not isinstance(sql, list):
                    sql = [sql]

                def key_func(report):
                    return tuple([
                        kwargsql.get(report, query)
                        for query in sql
                    ])
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
            return report['metrics'][self.metric]
        value_n1 = get_metric(data_n1)
        value_n = get_metric(data_n)
        if self.epsilon is not None:
            return abs(value_n - value_n1) < self.epsilon
        assert self.percent is not None
        return abs(value_n - value_n1) < self.percent / 100.0


class ExecutionDriver(Leaf):
    """Abstract representation of a benchmark command execution
    (a benchmark is made of several commands)
    """

    name = 'local'

    def __init__(self, parent):
        super(ExecutionDriver, self).__init__(parent)
        self.benchmark = self.parent.benchmark
        self.execution = parent.execution
        self.command_expansion_vars = dict(
            process_count=1
        )

    @cached_property
    def _executor_script(self):
        """Create shell-script in charge of executing the benchmark
        and return its path.
        """
        fd, path = tempfile.mkstemp(suffix='.sh', dir=os.getcwd())
        os.close(fd)
        with open(path, 'w') as ostr:
            self._write_executor_script(ostr)
        os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
        return path

    @property
    def _jinja_executor_template(self):
        """:return Jinja template of the shell-script executor"""
        template = self.campaign.process.executor_template
        if template.startswith('#!'):
            return jinja_environment.from_string(template)
        else:
            return jinja_environment.get_template(template)

    def _write_executor_script(self, ostr):
        """Write shell script in charge of executing the command"""
        properties = dict(
            command=self.command,
            cwd=os.getcwd(),
            environment=dict(
                (var, six.moves.shlex_quote(value))
                for var, value in
                (self.execution.get('environment') or {}).items()
            ),
        )
        self._jinja_executor_template.stream(**properties).dump(ostr)

    @cached_property
    def command(self):
        """:return command to execute inside the generated shell-script"""
        exec_prefix = self.parent.parent.parent.config.get('exec_prefix', [])
        command = self.execution['command']
        if isinstance(command, list):
            command = [arg.format(**self.command_expansion_vars)
                       for arg in command]
        else:
            command = command.format(**self.command_expansion_vars)
        if self.execution.get('shell', False):
            if not isinstance(exec_prefix, six.string_types):
                exec_prefix = ' '.join(exec_prefix)
            if not isinstance(command, six.string_types):
                msg = "Expected string for shell command, not {type}: {value}"
                msg = msg.format(type=type(command).__name__,
                                 value=repr(command))
                raise Exception(msg)
            eax = [exec_prefix + command]
        else:
            if not isinstance(exec_prefix, list):
                exec_prefix = shlex.split(exec_prefix)
            if not isinstance(command, list):
                eax = exec_prefix + shlex.split(command)
            else:
                eax = exec_prefix + command
            eax = [six.moves.shlex_quote(arg) for arg in eax]
        return eax

    @cached_property
    def command_str(self):
        """get command to execute as string properly escaped

        :return: string
        """
        if isinstance(self.command, six.string_types):
            return self.command
        return ' '.join(map(
            six.moves.shlex_quote,
            self.command
        ))

    def popen(self, stdout, stderr):
        """Build popen object to run

        :rtype: subprocess.Popen
        """
        self.logger.info('Executing command: %s', self.command_str)
        return subprocess.Popen([self._executor_script],
                                stdout=stdout, stderr=stderr)

    @write_yaml_report
    def __call__(self, **kwargs):
        with open('stdout.txt', 'w') as stdout, \
                open('stderr.txt', 'w') as stderr:
            cwd = self.execution.get('cwd')
            if cwd is not None:
                ctx = self.parent.parent.parent.exec_context
                cwd = cwd.format(node=ctx.node, tag=ctx.tag)
                with pushd(cwd):
                    self.benchmark.pre_execute(self.execution)
                    exit_status = self.popen(stdout, stderr).wait()
                    self.benchmark.post_execute(self.execution)

            else:
                self.benchmark.pre_execute(self.execution)
                exit_status = self.popen(stdout, stderr).wait()
                self.benchmark.post_execute(self.execution)
        report = dict(
            exit_status=exit_status,
            benchmark=self.benchmark.name,
        )
        report.update(self.execution)
        report.update(command=self.command)
        benchmark_config = self.parent.parent.parent.config
        metrics = benchmark_config.get('metrics', {})
        if not isinstance(metrics, Mapping):
            raise Exception('"metrics" benchmark option must be a dict')
        if metrics:
            report.update(metrics=dict(**metrics))
        return report


class SrunExecutionDriver(ExecutionDriver):
    """Manage process execution with srun (SLURM)
    """
    name = 'srun'

    @cached_property
    def srun(self):
        """Get path to srun executable

        :rtype: string
        """
        commands = self.campaign.process.get('commands', {})
        return find_executable(commands.get('srun', 'srun'))

    @cached_property
    def common_srun_options(self):
        """Get options to be given to all srun commands

        :rtype: list of string
        """
        return self.campaign.process.get('srun') or {}

    @cached_property
    def tag(self):
        return self.parent.parent.parent.parent.name

    @cached_property
    def command(self):
        """get command to execute

        :return: list of string
        """
        srun_options = copy.copy(self.common_srun_options)
        srun_options.update(self.parent.parent.parent.config.get('srun') or {})
        srun_optlist = self._make_srun_arguments(srun_options)
        command = super(SrunExecutionDriver, self).command
        return [self.srun] + srun_optlist + command

    def _make_srun_arguments(self, optdict):
        args = []
        for k, v in optdict.items():
            if v is None:
                continue
            elif v is True:  # specifically check if it is true
                args.append('--{}'.format(k))
            else:
                args.append('--{}={}'.format(k, six.moves.shlex_quote(str(v))))
        if not isinstance(self.root.network.nodes(self.tag), ConstraintTag):
            # Expand nodelist if the tag is not a "constraint" one.
            pargs = self._parse_srun_options(args)
            if not pargs.constraint:
                # Expand nodelist if --constraint option is not specified
                # in srun options
                args.append('--nodelist=' + ','.join(self.srun_nodes))
        return args

    def _parse_srun_options(self, options):
        parser = argparse.ArgumentParser()
        parser.add_argument('-n', '--ntasks', default=1)
        parser.add_argument('-C', '--constraint')
        args = parser.parse_known_args(options)
        self.command_expansion_vars['process_count'] = args[0].ntasks
        return args[0]

    @cached_property
    def srun_nodes(self):
        """Get list of nodes where to execute the command
        """
        count = self.execution.get('srun_nodes', 1)
        if isinstance(count, six.string_types):
            tag = count
            count = 0
        elif isinstance(count, list):
            return count
        else:
            assert isinstance(count, int)
            tag = self.tag
        nodes = self._srun_nodes(tag, count)
        if 'srun_nodes' in self.execution:
            self.execution['srun_nodes'] = nodes
            self.execution['srun_nodes_count'] = len(nodes)
        return nodes

    def _srun_nodes(self, tag, count):
        assert count >= 0
        if tag != '*' and not self.root.network.has_tag(tag):
            raise ValueError('Unknown tag: {}'.format(tag))
        nodes = sorted(list(self.root.network.nodes(tag)))
        if count > 0:
            return self._filter_srun_nodes(nodes, count)
        return nodes

    def _filter_srun_nodes(self, nodes, count):
        assert count <= len(nodes)
        pos = nodes.index(self.node)
        nodes = nodes * 2
        return nodes[pos:pos + count]
