# -*- coding: utf-8 -*-
"""API to declare benchmarks
"""

from abc import ABCMeta, abstractmethod, abstractproperty
from collections import namedtuple
import os.path as osp

from six import with_metaclass

__all__ = [
    'MetricsExtractor',
    'Benchmark',
]

# Metrics have simply a unit and a type
# namedtuples are compact and have a nice str representation
Metric = namedtuple("Metric", "unit type")


ExecutionContext = namedtuple(
    "ExecutionContext",
    [
        "node",
        "tag",
        "nodes",
        "logger",
        "srun_options",
    ]
)


class UnexpectedMetricsException(Exception):
    def __init__(self, unset_metrics, metrics):
        self.unset_metrics = unset_metrics
        self.metrics = metrics

    def __str__(self):
        error = \
            'Could not extract some metrics: %s\n' \
            'metrics set: %s'
        return error % (', '.join(self.unset_metrics),
                        ', '.join(set(self.metrics)))


class Metrics(object):  # pragma pylint: disable=too-few-public-methods
    """List of common metrics
    """
    Milisecond = Metric('ms', float)
    Second = Metric('s', float)
    MegaBytesPerSecond = Metric('MB/s', float)
    Cardinal = Metric('#', int)
    Byte = Metric('B', int)
    Flops = Metric('flop/s', float)
    Bool = Metric('bool', bool)
    Ops = Metric('op/s', float)


class MetricsExtractor(with_metaclass(ABCMeta, object)):
    """Extract data from a benchmark command outputs
    """

    @abstractproperty
    def metrics(self):
        """List of exported metrics

        :return: exported metrics
        :rtype: ``dict of
                metric_name: dict('type'=python_type, 'unit'=string)``

        for instance:

        >>> def metrics(self):
            return dict(
                rmax=dict(type=float, unit='Gflops'),
                parallel_efficiency=dict(type=float, unit='percent')
            )

        """
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def extract_metrics(self, outdir, metas):
        """Extract metrics from benchmark output

        :return: ``dict of metric_name: metric_value``

        ``metric_value`` type should be the one specified in
        the ``metrics`` member funtion.
        """
        raise NotImplementedError  # pragma: no cover

    @property
    def check_metrics(self):
        """Ensures that metrics returned by ``extract`` member function
        is exactly what was declared.
        """
        return True

    def extract(self, outdir, metas):
        metrics = self.extract_metrics(outdir, metas)
        if self.check_metrics:
            self._check_metrics(metrics)
        return metrics

    def _check_metrics(self, metrics):
        unset_metrics = set(self.metrics) - set(metrics)
        if any(unset_metrics):
            raise UnexpectedMetricsException(unset_metrics, metrics)

    @classmethod
    def stdout(cls, outdir):
        """Get path to the file containing stdout written
        by benchmark command

        :param outdir: absolute path to the benchmark output directory
        :return: path to standard output file
        :rtype: string
        """
        return osp.join(outdir, 'stdout.txt')

    @classmethod
    def stderr(cls, outdir):
        """Get path to the file containing stderr written
        by benchmark command

        :param outdir: absolute path to the benchmark output directory
        :return: path to error output file
        :rtype: string
        """
        return osp.join(outdir, 'stderr.txt')


class Benchmark(with_metaclass(ABCMeta, object)):
    """Declare benchmark utility
    """

    # --- Class "static" properties ---
    @abstractproperty
    def name(self):
        """Get benchmark name

        :rtype: string
        """
        raise NotImplementedError  # pragma: no cover

    @abstractproperty
    def description(self):
        """Get benchmark long description

        :rtype: string
        """
        raise NotImplementedError  # pragma: no cover
    # ---

    def __init__(self, attributes=None):
        self.attributes = attributes or {}

    @property
    def in_campaign_template(self):
        """Should the benchmark class be reference in the
        campaign template YAML file
        """
        return True

    @abstractmethod
    def execution_matrix(self, context):
        """Describe benchmark commands

        :param context: `ExecutionContext` instance

        Provides list of commands to perform. Every returned command
        is a dictionary containing the following keys:

        * *command*:
            a list of string containing the command to execute.
            Variable substitution is performed on every element
            on the list, using the Python str.format
            method.

            Here is the list of available variables:
                process_count: number of processes to run.
                it provides the --ntasks value when using
                the `srun` execution layer.

            See https://docs.python.org/2/library/stdtypes.html#str.format

        * category*:
            a string used to group commands together.
            Most benchmark class may only need one category.
        * *metas*:
            a dictionary providing relevant information regarding the
            executed command that may be useful afterward. Typically,
            those are command's inputs.
        * *environment* (optional):
            a dictionary providing additional environment variables
            to be given to the executed command
        * *srun_nodes* (optional):
            When the `srun` execution layer is enabled,
            an integer providing the number of required nodes.
            Must be greater equal than 0 and less than the number of nodes
            of the tag the benchmark is part of.
            If 0, then the job is executed on all nodes of the tag the
            benchmark is part of.
            If a string is provided, then all nodes of the given tag will
            be used.
        * *shell* (optional boolean):
          when `shell` parameter is `True`, then the given command
          is considered as a shell command.

        Execution context: for every command, a dedicated output directory
        is created and the current working directory changed to this directory
        prior command execution. Standard and error outputs are redirected
        to stdout.txt and stderr.txt respectively. Additional output files
        may be created in this directory.
        Any occurence to "{outdir}" in the command field will be substituted
        by the output directory.

        :return: commands to execute
        :rtype: list of dict. For instance:

        >>> def execution_matrix(self):
            for core in [1, 4, 16, 64]:
                yield dict(
                    category='foo',
                    command=['foo', '--cores', str(cores)],
                    metas=dict(cores=cores),
                )
                yield dict(
                    category='bar',
                    command=['bar', '--cores', str(cores)],
                    metas=dict(cores=cores),
                )
        """
        raise NotImplementedError  # pragma: no cover

    def pre_execute(self, execution):
        """Method called before executing one of the commands.
        Current working directory is the execution directory.

        :param execution: one of the dictionary
                          provided in ``execution_matrix`` member method.
        """
        del execution  # unused

    def post_execute(self, execution):
        """Method called after executing one of the commands.
        Current working directory is the execution directory.

        :param execution: one of the dictionary
                          provided in ``execution_matrix`` member method.
        """
        del execution  # unused

    @abstractproperty
    def metrics_extractors(self):
        """Describe how to extract metrics from files written by
        benchmark commands.

        Provides metrics extractors for every categories specified
        in the ``execution_matrix`` member method.

        :return: metrics_extractors instances for each category
        :rtype: ``dict of list of hpcbench.api.MetricsExtractor`` instances.
                if there are dedicated extractors for each category.
                Otherwise a ``list of hpcbench.api.MetricsExtractor``
                instances of there are common extractors for all categories,

        The list structure can be skipped when there is one
        element. For instance if there are dedicated extractors for every
        categories:

        >>> def metrics_extractors(self):
                return dict(
                    foo=foo_stdout_extractor(metrics=['rmax', 'efficiency']),
                    bar=[bar_extractor(), foobar_extractor()]
                )

        If there is only one extractor:

        >>> def metrics_extractors(self):
            return foobar_extractor()

        """
        raise NotImplementedError  # pragma: no cover

    @property
    def plots(self):
        """Describe figures to generate

        :return: figure descriptions of every category
        :rtype: ``dict of string -> list of dict``

        Every dictionary is a figure's description, containing
        the following keys:

        * *name*: string providing figure's name

        * *series*: dictionary describing data required to draw the figure,
          made of 2 keys:

            * *metas*: string list of metas to retrieve.
              Data series are sorted by metas by default.
              If meta's name starts with '-',
              then series are sorted in descending order.

            * *metrics*: list of metrics to use.

        * *plotter*:
            callable object that will be given metrics to plot
        """
        return {}

    @classmethod
    def get_subclass(cls, name):
        """Get Benchmark subclass by name
        :param name: name returned by ``Benchmark.name`` property
        :return: instance of ``Benchmark`` class
        """
        for subclass in cls.__subclasses__():
            if subclass.name == name:
                return subclass
        raise NameError("Not a valid Benchmark class: " + name)
