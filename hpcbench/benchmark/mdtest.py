"""Wrapper for MDTest metadata benchmark utility
    See https://github.com/LLNL/mdtest
"""
import re

from cached_property import cached_property

from hpcbench.api import (
    Benchmark,
    Metrics,
    MetricsExtractor,
)
from hpcbench.toolbox.functools_ext import listify
from hpcbench.toolbox.process import find_executable


class MDTestExtractor(MetricsExtractor):
    """Extract metrics from mdtest output
    """
    STDOUT_IGNORE_PRIOR = 'SUMMARY:'

    FLOAT_RE = r'(\d*\.?\d+)'
    METRICS_RE = (r'\s+{float}' * 4).format(float=FLOAT_RE)
    METRIC_LINE_PREFIX = r'\s+(\w+) (\w+)\s*:'
    METRIC_LINE_EXTRACT = METRIC_LINE_PREFIX + METRICS_RE
    METRIC_LINE_EXTRACT_RE = re.compile(METRIC_LINE_EXTRACT)

    @cached_property
    def metrics(self):
        names = dict(
            directory={'creation', 'stat', 'removal'},
            file={'creation', 'stat', 'read', 'removal'},
            tree={'creation', 'removal'}
        )

        def _pairs():
            for kind in {'max', 'min', 'mean', 'stddev'}:
                for prefix, suffixes in names.items():
                    for suffix in suffixes:
                        yield kind + '_' + prefix + '_' + suffix, Metrics.Ops
        return dict(_pairs())

    def extract_metrics(self, outdir, metas):
        with open(self.stdout(outdir)) as istr:
            MDTestExtractor._seek_results(istr)
            return MDTestExtractor._extract_results(istr)

    @classmethod
    def _seek_results(cls, istr):
        while True:
            line = istr.readline()
            if line == '':
                raise Exception('Unexpected EOF')
            if line.startswith(cls.STDOUT_IGNORE_PRIOR):
                break
        istr.readline()
        istr.readline()

    @classmethod
    @listify(wrapper=dict)
    def _extract_results(cls, istr):
        for line in istr:
            line = line.rstrip()
            if not line:
                break
            match = cls.METRIC_LINE_EXTRACT_RE.match(line)
            if not match:
                raise Exception('Parse Error')
            fields = cls._match_to_dict(match)
            for kind, value in fields['data'].items():
                name = '{kind}_{prefix}_{suffix}'.format(
                    kind=kind,
                    prefix=fields['prefix'],
                    suffix=fields['suffix'],
                )
                yield name, value

    @classmethod
    def _match_to_dict(cls, match):
        return dict(
            prefix=match.group(1).lower(),
            suffix=match.group(2).lower(),
            data=dict(
                max=float(match.group(3)),
                min=float(match.group(4)),
                mean=float(match.group(5)),
                stddev=float(match.group(6)),
            )
        )


class MDTest(Benchmark):
    """Wrapper for mdtest utility
    """
    name = 'mdtest'
    description = 'Used for testing the metadata performance of a file system'

    DEFAULT_ATTRIBUTES = dict(
        executable='mdtest',
        path=None,
        options=['-n', '10000', '-i', '3'],
        srun_nodes=1,
    )

    def __init__(self):
        super(MDTest, self).__init__(attributes=MDTest.DEFAULT_ATTRIBUTES)

    @property
    def path(self):
        """Overwrite directory files are created in"""
        return self.attributes['path']

    @property
    def options(self):
        """List of arguments given to the mdtest command"""
        return [
            str(e)
            for e in self.attributes['options']
        ]

    @cached_property
    def executable(self):
        """get absolute path to mdtest utility
        """
        return self.attributes['executable']

    @property
    def command(self):
        """get command line to execute
        """
        return [find_executable(self.executable)] + self.options

    @property
    def srun_nodes(self):
        """Number of nodes the command is executed on.
        """
        return self.attributes['srun_nodes']

    def execution_matrix(self, context):
        del context  # unused
        yield dict(
            category='disk',
            command=self.command,
            srun_nodes=self.srun_nodes,
        )

    @property
    def metrics_extractors(self):
        return MDTestExtractor()
