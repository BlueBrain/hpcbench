"""Test basic functionality of BBP5
"""
from cached_property import cached_property

from hpcbench.api import (
    Benchmark,
    Metrics,
    MetricsExtractor,
)
from hpcbench.toolbox.process import find_executable


class BASICExtractor(MetricsExtractor):
    METRICS = dict(
        fs_local=Metrics.Bool,
        fs_gpfs=Metrics.Bool,
        in_network=Metrics.Bool,
        out_network=Metrics.Bool,
        hello=Metrics.Bool,
    )

    METRICS_NAMES = set(METRICS)

    @property
    def metrics(self):
        """ The metrics to be extracted.
            This property can not be replaced, but can be mutated as required
        """
        return BASICExtractor.METRICS

    def extract(self, outdir, metas):
        metrics = {}
        # parse stdout and extract desired metrics
        with open(self.stdout(outdir)) as istr:
            for line in istr:
                list_word = line.split()
                key = list_word[0]
                value = list_word[-1]
                metrics[key] = metrics.get(key, True) and (value == 'OK')
        return self.check_metrics(metrics)

    @classmethod
    def check_metrics(cls, metrics):
        # ensure all metrics have been extracted
        unset_attributes = cls.METRICS_NAMES - set(metrics)
        if any(unset_attributes):
            error = \
                'Could not extract some metrics: %s\n' \
                'metrics setted are: %s'
            raise Exception(error % (' ,'.join(unset_attributes),
                                     ' ,'.join(set(metrics))))
        return metrics


class BASIC(Benchmark):
    """Benchmark BASICbench utility
    """
    DEFAULT_EXECUTABLE = 'basic'
    DEFAULT_DEVICE = 'cpu'
    CATEGORY = 'cpu'

    def __init__(self):
        # locate `shocdriver` executable
        super(BASIC, self).__init__(
            attributes=dict(
                device=BASIC.DEFAULT_DEVICE,
                executable=BASIC.DEFAULT_EXECUTABLE
            )
        )
    name = 'basic'

    description = "Basic linux functionalities of BBP5."

    @cached_property
    def executable(self):
        """Get absolute path to executable
        """
        return find_executable(self.attributes['executable'])

    @property
    def execution_matrix(self):
        yield dict(
            category=BASIC.CATEGORY,
            command=[
                self.executable,
            ],
        )

    @cached_property
    def metrics_extractors(self):
        return BASICExtractor()
