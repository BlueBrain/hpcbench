"""Standard benchmark
"""

from collections import Mapping
import copy
from functools import reduce
import itertools
import os.path as osp
import re

from cached_property import cached_property
import six

from hpcbench.api import (
    Benchmark,
    Metrics,
    MetricsExtractor,
)
from hpcbench.toolbox.functools_ext import listify


class Configuration(object):
    def __init__(self, attributes):
        self.attributes = attributes
        metrics = attributes.get('metrics', {})
        self._extractors = Configuration._create_extractors(metrics)

    def execution_matrix(self, context):
        for cmd in self.cmds:
            yield cmd

    @classmethod
    def _create_extractors(cls, metrics):
        """Build metrics extractors according to the `metrics` config

        :param metrics: Benchmark `metrics` configuration section
        """
        metrics_dict = {}
        # group entries by `category` attribute (default is "standard")
        for metric, config in six.iteritems(metrics):
            category = config.get('category', StdBenchmark.DEFAULT_CATEGORY)
            metrics_dict.setdefault(category, {})[metric] = config
        # create one StdExtractor instance per category,
        # passing associated metrics
        return dict(
            (category, StdExtractor(metrics))
            for category, metrics in six.iteritems(metrics_dict)
        )

    @property
    def cmds(self):
        for cmd in self.attributes['executables']:
            for exec_ in self._create_executable(cmd):
                yield exec_

    def _create_executable(self, cmd):
        shells = self.attributes.get('shells', [])
        for metas in self.shell_metas_set(cmd):
            execution = copy.deepcopy(cmd)
            execution['metas'] = metas
            if not shells:
                execution['command'] = self._fmtcmd(
                    execution['command'],
                    metas
                )
                yield Configuration._fill_default_execution(execution)
            else:
                for shell in shells:
                    for shell_metas in self.shell_metas_set(shell):
                        sexec = copy.deepcopy(execution)
                        sexec['metas'].update(shell_metas)
                        sexec['shell'] = True
                        all_commands = []
                        # prelude commands
                        for prelude_cmd in shell['commands']:
                            if not isinstance(prelude_cmd, list):
                                all_commands.append([prelude_cmd])
                            else:
                                all_commands.append(prelude_cmd)
                        # real benchmark command
                        if not isinstance(sexec['command'], list):
                            all_commands.append([sexec['command']])
                        else:
                            all_commands.append(sexec['command'])
                        sexec['command'] = [
                            self._fmtcmd(cmd_, sexec['metas'])
                            for cmd_ in all_commands
                        ]
                        yield Configuration._fill_default_execution(sexec)

    def _fmtcmd(self, command, metas):
        if isinstance(command, list):
            return [arg.format(**metas) for arg in command]
        return command.format(**metas)

    @classmethod
    def _fill_default_execution(cls, execution):
        execution.setdefault('category', StdBenchmark.DEFAULT_CATEGORY)
        return execution

    def shell_metas_set(self, cmd):
        metas = cmd.get('metas')
        if metas is None:
            metas = [{}]
        elif isinstance(metas, Mapping):
            metas = [metas]

        for metas_c in metas:
            metas_c = dict(
                (k, v) if isinstance(v, list) else (k, [v])
                for k, v in six.iteritems(metas_c)
            )
            metas_c = list(
                list((name, value) for value in values)
                for name, values in six.iteritems(metas_c)
            )
            for combination in itertools.product(*metas_c):
                eax = list(combination)
                yield dict(eax)

    def metrics_extractors(self):
        return self._extractors


class StdExtractor(MetricsExtractor):
    """Generic Metric extractor for a particular category
    """
    def __init__(self, metrics):
        """Metrics as specified in the benchmark `metrics` section
        """
        super(StdExtractor, self).__init__()
        self._metrics = metrics

    @cached_property
    def metrics(self):
        """
        :return: Description of metrics extracted by this class
        """
        return dict(
            (name, getattr(Metrics, config['type']))
            for name, config in six.iteritems(self._metrics)
        )

    @cached_property
    def froms(self):
        """Group metrics according to the `from` property.
        """
        eax = {}
        for name, config in six.iteritems(self._metrics):
            from_ = self._get_property(config, 'from',
                                       default=StdBenchmark.DEFAULT_FROM)
            eax.setdefault(from_, {})[name] = config
        return eax

    @listify(wrapper=dict)
    def extract_metrics(self, outdir, metas):
        return itertools.chain.from_iterable(
            six.iteritems(self._metrics_from_file(outdir, from_,
                                                  metrics, metas))
            for from_, metrics in six.iteritems(self.froms)
        )

    def _metrics_from_file(self, outdir, file, metrics, metas):
        if file in {'stdout', 'stderr'}:
            file += '.txt'
        with open(osp.join(outdir, file)) as istr:
            return self._metrics_from_stream(istr, metrics, metas)

    def _metrics_from_stream(self, istr, metrics, metas):
        regex = {}
        metas = metas or {}
        for name, config in six.iteritems(metrics):
            expression = self._get_property(config, 'match',
                                            metas=metas, required=True)
            expression = expression.format(**metas)
            regex[name] = dict(
                re=re.compile(expression),
                metric=getattr(
                    Metrics,
                    self._get_property(config, 'type', required=True)
                ),
                multiply_by=self._get_property(config, 'multiply_by',
                                               metas=metas),
            )
        metrics = dict()
        for line in istr:
            line = line.rstrip()
            for meta, config in six.iteritems(regex):
                match = config['re'].match(line)
                if match:
                    value = config['metric'].type(match.group(1))
                    factor = config['multiply_by']
                    if factor is not None:
                        value *= factor
                    metrics.setdefault(meta, []).append(value)
                    break
        return dict(
            (
                name,
                self._reduce_metric(
                    self._get_property(config, 'reduce', default='max'),
                    values
                ),
            )
            for name, values in six.iteritems(metrics)
        )

    def _reduce_metric(self, op, metrics):
        elt_type = type(metrics[0])
        if len(metrics) == 1:
            return metrics[0]
        try:
            op = dict(
                avg=lambda l: sum(l) / elt_type(len(l)),
                max=max,
                min=min,
            )[op]
        except KeyError:
            raise Exception('Unknown reduce operation: "{}"'.format(op))
        else:
            return reduce(op, metrics)

    def _get_property(self, config, name, metas=None,
                      default=None, required=False):
        lookups = []
        whens = config.get('when', [])
        for when in whens if metas else []:
            cond_met = True
            for meta, cvalue in six.iteritems(when['conditions']):
                if meta not in metas:
                    cond_met = False
                    break
                if not isinstance(cvalue, list):
                    cvalue = [cvalue]
                if metas[meta] not in cvalue:
                    cond_met = False
                    break
            if cond_met:
                lookups.append(when)
                break
        lookups.append(config)
        for lookup in lookups:
            try:
                return lookup[name]
            except KeyError:
                continue
        if required:
            raise KeyError
        else:
            return default


class StdBenchmark(Benchmark):
    name = "standard"
    description = "benchmark class for generic usage"

    DEFAULT_FROM = 'stdout'
    DEFAULT_CATEGORY = "standard"

    def __init__(self):
        super(StdBenchmark, self).__init__()

    @cached_property
    def config(self):
        return StdBenchmark._load_config(self.attributes)

    @classmethod
    def _load_config(cls, attributes):
        return Configuration(attributes)

    def execution_matrix(self, context):
        return self.config.execution_matrix(context)

    @cached_property
    def metrics_extractors(self):
        return self.config.metrics_extractors()