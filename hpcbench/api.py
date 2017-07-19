# -*- coding: utf-8 -*-


class metrics_extractor(object):
    """Extract data from a benchmark command outputs
    """
    def metrics(self):
        """List of exported metrics

        :return: exported metrics
        :rtype: dictionary of ``metric_name: dict('type'=python_type, 'unit'=string)``
        for instance:

        >>> def metrics(self):
            return dict(
                rmax=dict(type=float, unit='Gflops'),
                parallel_efficiency=dict(type='float', unit='percent')
            )
        """
        raise NotImplementedError


class benchmark(object):
    def name(self):
        """Get benchmark name

        :return: benchmark name
        :rtype: string
        """
        raise NotImplementedError

    def description(self):
        """Get benchmark long description 

        :return: benchmark long description
        :rtype: string
        """
        raise NotImplementedError

    def execution_matrix(self):
        """Describe benchmark commands

        Provides the list of commands to perform. Every returned command
        is a dict providing the following keys:

        command:
            list of string. It contains the command to execute.
        category:
            a string used to group commands together.
        meta:
            a dictionary providing relevant information regarding the 
            executed command that may be useful afterward. Typically, 
            those are  command's inputs.
        outputs:
            The kind of raw data written by the command.
            The values must match 
            Type can be a string or a list of string.

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
                    meta=dict(cores=cores),
                )
                yield dict(
                    category='bar',
                    command=['bar', '--cores', cores],
                    meta=dict(cores=cores),
                )
        """
        raise NotImplementedError

    def metrics_extractors(self):
        """Describe how to extract metrics from files written by
        benchmark commands.

        Provides metrics extractors for every categories specified
        in the execution_matrix member method.

        :return: metrics_extractors instances for each category
        :rtype: ``dict of list of hpcbench.api.metrics_extractor``. For instance:

        >>> def metrics_extractors(self):
                return dict(
                    foo=foo_stdout_extractor(metrics=['rmax', 'parallel_efficiency']),
                    bar=[bar_extractor(), foobar_extractor()]
                )
        """
        raise NotImplementedError
