# -*- coding: utf-8 -*-
"""API to declare benchmarks
"""

from abc import ABCMeta, abstractmethod, abstractproperty
from collections import namedtuple
import contextlib
import os.path as osp

from six import with_metaclass

__all__ = ['Benchmark', 'ExecutionContext', 'MetricsExtractor']


class Cluster(with_metaclass(ABCMeta, object)):
    @abstractproperty
    def nodes(self):
        """get nodes of the current tag
        :rtype: string list
        """

    @abstractproperty
    def node_pairs(self):
        """List of node pairs where:
        - first element is the current node
        - the second being node N for every N after the current node
          is the nodes list of the current tag.
        """
        pass

    @abstractproperty
    def tag_node_pairs(self):
        """Iterator of node pairs for every entries
        in the strictly upper triangular matrix of nodes.
        """


class ExecutionContext(
    namedtuple(
        "ExecutionContext",
        [
            "cluster",  # instance of ``Cluster``
            "logger",  # instance of logging.Logger
            "node",  # current node (string)
            "srun_options",  # given srun_options (string list)
            "tag",  # current tag processed (string)
            "benchmark",  # current benchmark processed (string)
        ],
    )
):
    @property
    def implicit_nodes(self):
        return not isinstance(self.cluster.nodes, list)


# Metrics have simply a unit and a type
# namedtuples are compact and have a nice str representation
Metric = namedtuple("Metric", "unit type")


class Metrics(object):  # pragma pylint: disable=too-few-public-methods
    """List of common metrics
    """

    Microsecond = Metric('us', float)
    Millisecond = Metric('ms', float)
    Second = Metric('s', float)
    MegaBytesPerSecond = Metric('MB/s', float)
    GigaBytesPerSecond = Metric('GB/s', float)
    Cardinal = Metric('#', int)
    Byte = Metric('B', int)
    GFlops = Metric('GFlop/s', float)
    Bool = Metric('bool', bool)
    Ops = Metric('op/s', float)


class NoMetricException(Exception):
    """Raised when a log does not contain any metric"""

    pass


class UnexpectedMetricsException(Exception):
    def __init__(self, unset_metrics, metrics):
        self.unset_metrics = unset_metrics
        self.metrics = metrics

    def __str__(self):
        error = 'Could not extract some metrics: %s\n' 'metrics set: %s'
        return error % (', '.join(self.unset_metrics), ', '.join(set(self.metrics)))


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

    @contextlib.contextmanager
    def context(self, outdir, log_prefix):
        """Setup instance to extract metrics from the proper run

        :param outdir: run directory
        :param log_prefix: log filenames prefix
        """
        try:
            self._outdir = outdir
            self._log_prefix = log_prefix
            yield
        finally:
            self._log_prefix = None
            self._outdir = None

    @abstractmethod
    def extract_metrics(self, metas):
        """Extract metrics from benchmark output

        :return: ``dict of metric_name: metric_value``

        ``metric_value`` type should be the one specified in
        the ``metrics`` member function.
        """
        raise NotImplementedError  # pragma: no cover

    @property
    def check_metrics(self):
        """Ensures that metrics returned by ``extract`` member function
        is exactly what was declared.
        """
        return True

    def extract(self, metas):
        metrics = self.extract_metrics(metas)
        if self.check_metrics:
            self._check_metrics(metrics)
        return metrics

    def _check_metrics(self, metrics):
        if not metrics:
            raise NoMetricException()
        unset_metrics = set(self.metrics) - set(metrics)
        if any(unset_metrics):
            raise UnexpectedMetricsException(unset_metrics, metrics)

    @property
    def stdout(self):
        """Get path to the file containing stdout written
        by benchmark command

        :return: path to standard output file
        :rtype: string
        """
        return osp.join(self._outdir, self._log_prefix + 'stdout')

    @property
    def stderr(self):
        """Get path to the file containing stderr written
        by benchmark command

        :return: path to error output file
        :rtype: string
        """
        return osp.join(self._outdir, self._log_prefix + 'stderr')


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

    @property
    def metric_required(self):
        """Whether a benchmark execution must emit metrics or not

        :rtype: bool
        """
        return True

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
        * *modules* (optional):
            list of modules to load before executed the command.
        * *srun_nodes* (optional):
            When the `srun` execution layer is enabled,
            an integer providing the number of required nodes.
            Must be greater equal than 0 and less than the number of nodes
            of the tag the benchmark is part of.
            If 0, then the job is executed on all nodes of the tag the
            benchmark is part of.
            If a string is provided, then all nodes of the given tag will
            be used.
            Note: this parameter is ignored if -C/--constraint
            slurm option is used.
        * *shell* (optional boolean):
          when `shell` parameter is `True`, then the given command
          is considered as a shell command.
        * *cwd* (optional):
          directory where the command is executed.
        * *expected_exit_statuses* (optional):
          list or set of statuses the command is expected to exit
          to consider it successful.
          Metrics won't be extracted if command fails.
          Default value is: {0}

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

    def pre_execute(self, execution, context):
        """Method called before executing one of the commands.
        Current working directory is the execution directory.

        :param execution: one of the dictionary
                          provided in ``execution_matrix`` member method.
        :param context: `ExecutionContext` instance. See ``execution_matrix``
                        member method for more details.
        """
        del execution  # unused
        del context  # unused

    def post_execute(self, execution, context):
        """Method called after executing one of the commands.
        Current working directory is the execution directory.

        :param execution: one of the dictionary
                          provided in ``execution_matrix`` member method.
        :param context: `ExecutionContext` instance. See ``execution_matrix``
                        member method for more details.
        """
        del execution  # unused
        del context  # unused

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
