# -*- coding: utf-8 -*-
"""API to declare benchmarks
"""

import os.path as osp

from six import with_metaclass

from hpcbench.toolbox.class_lib import ClassRegistrar

__all__ = [
    'MetricsExtractor',
    'Benchmark',
]


class MetricsExtractor(object):
    """Extract data from a benchmark command outputs
    """
    def metrics(self):
        """List of exported metrics

        :return: exported metrics
        :rtype: dictionary of
        ``metric_name: dict('type'=python_type, 'unit'=string)``

        for instance:

        >>> def metrics(self):
            return dict(
                rmax=dict(type=float, unit='Gflops'),
                parallel_efficiency=dict(type=float, unit='percent')
            )

        """
        raise NotImplementedError

    def extract(self, outdir, metas):
        """Extract metrics from benchmark output

        :return: dictionary of ``metric_name: metric_value``
        metric_value type should be the one specified in
        the ``metrics`` member funtion.

        """
        raise NotImplementedError

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
        return osp.join(outdir, 'sterrr.txt')


class Benchmark(with_metaclass(ClassRegistrar, object)):
    """Declare benchmark utility
    """

    name = None
    """Get benchmark name
    :rtype: string
    """

    description = None
    """Get benchmark long description
    :rtype: string
    """

    def __init__(self, attributes=None):
        self.attributes = attributes or {}

    def __str__(self):
        return self.name

    def execution_matrix(self):
        """Describe benchmark commands

        Provides the list of commands to perform. Every returned command
        is a dict providing the following keys:

        command:
            list of string. It contains the command to execute.
        category:
            a string used to group commands together.
        metas:
            a dictionary providing relevant information regarding the
            executed command that may be useful afterward. Typically,
            those are  command's inputs.
        outputs:
            The kind of raw data written by the command.
            The values must match
            Type can be a string or a list of string.
        environment (optional):
            a dictionary providing additional environment variables
            to be given to the executed command

        Execution context: for every command, a dedicated output directory
        is created and the current working directory changed to this directory
        prior command execution. Standard and error outputs are redirected
        to stdout.txt and stderr.txt respectively. Additional output files
        may be created in this directory.
        Any occurence to "{outdir}" in the command field will be substituted
        by the output directory.

        :return: commands to execute
        :rtype: list of dictionary. For instance:

        >>> def execution_matrix(self):
            for core in [1, 4, 16, 64]:
                yield dict(
                    category='foo',
                    command=['foo', '--cores', cores],
                    metas=dict(cores=cores),
                )
                yield dict(
                    category='bar',
                    command=['bar', '--cores', cores],
                    metas=dict(cores=cores),
                )
        """
        raise NotImplementedError

    def pre_execution(self):
        """Method called before executing one of the command.
        Current working directory is the execution directory.
        """
        pass

    def metrics_extractors(self):
        """Describe how to extract metrics from files written by
        benchmark commands.

        Provides metrics extractors for every categories specified
        in the execution_matrix member method.

        :return: metrics_extractors instances for each category
        :rtype: ``dict of list of hpcbench.api.MetricsExtractor``.
        The list structure can be skiped when there is one
        element. For instance:

        >>> def metrics_extractors(self):
                return dict(
                    foo=foo_stdout_extractor(metrics=['rmax', 'efficiency']),
                    bar=[bar_extractor(), foobar_extractor()]
                )
        """
        raise NotImplementedError

    def plots(self):
        """Describe figures to generate

        :return: figure descriptions of every category
        :rtype: dictionary of string (category) -> list of dict (description)
        A figure description is a dictionary made of the following keys:

        name:
            string providing figure's name
        series:
            dictionary describing data required to draw the figure,
            made of 2 keys:
            metas:
                string list of meta to retrieve. Data series are sorted
                by metas by default. If meta's name starts with '-',
                then series are sorted in descending order.
            metrics:
               list of metrics to use.
        plotter:
            callable object that will be given metrics to plot
        """
