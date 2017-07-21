# -*- coding: utf-8 -*-
"""API to declare benchmarks
"""

import os.path as osp


__all__ = [
    'metrics_extractor',
    'benchmark',
]


class metrics_extractor(object):
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

        :return: dictionary of ``metric_name: metric_value```
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


class BenchmarkLibrary(object):
    BENCHMARKS = dict()

    @classmethod
    def get(cls, name):
        clazz = cls.BENCHMARKS.get(name)
        if clazz is None:
            raise Exception('Unregistered Benchmark "%s"' % name)
        return clazz

    @classmethod
    def register_class(cls, clazz):
        if clazz.name in cls.BENCHMARKS:
            raise Exception('Benchmark %s is already registered' % clazz.name)
        cls.BENCHMARKS[clazz.name] = clazz


class LibraryRegistrar(type):
    def __new__(meta, name, bases, class_dict):
        cls = type.__new__(meta, name, bases, class_dict)
        BenchmarkLibrary.register_class(cls)
        return cls


class benchmark(object):
    """Declare benchmark utility
    """

    __metaclass__ = LibraryRegistrar

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

    def metrics_extractors(self):
        """Describe how to extract metrics from files written by
        benchmark commands.

        Provides metrics extractors for every categories specified
        in the execution_matrix member method.

        :return: metrics_extractors instances for each category
        :rtype: ``dict of list of hpcbench.api.metrics_extractor``.
        For instance:

        >>> def metrics_extractors(self):
                return dict(
                    foo=foo_stdout_extractor(metrics=['rmax',
                                                      'parallel_efficiency']),
                    bar=[bar_extractor(), foobar_extractor()]
                )
        """
        raise NotImplementedError
