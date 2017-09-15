"""Test basic functionality of BB5
"""
from __future__ import print_function

import os.path as osp

from cached_property import cached_property

from hpcbench.api import (
    Benchmark,
    Metrics,
    MetricsExtractor,
)


class BasicExtractor(MetricsExtractor):
    MANDATORY_METRICS = dict(
        fs_network=Metrics.Bool,
        fs_local=Metrics.Bool,
        outside_network=Metrics.Bool,
        hello_world=Metrics.Bool,
    )
    MANDATORY_METRICS_NAMES = set(MANDATORY_METRICS)

    def __init__(self):
        super(BasicExtractor, self).__init__()
        self._metrics = {}

    @property
    def metrics(self):
        """ The metrics to be extracted.
            This property can not be replaced, but can be mutated as required
        """
        return self._metrics

    def extract(self, outdir, metas):
        metrics = {}
        # parse stdout and extract desired metrics
        with open(self.stdout(outdir)) as istr:
            for line in istr:
                list_word = line.split()
                key = list_word[0]
                value = list_word[-1]
                metrics[key] = metrics.get(key, True) and (value == 'OK')
                self._metrics[key] = Metrics.Bool
        return self.check_metrics(metrics)

    @classmethod
    def check_metrics(cls, metrics):
        # ensure all metrics have been extracted
        unset_attributes = cls.MANDATORY_METRICS_NAMES - set(metrics)
        if any(unset_attributes):
            error = \
                'Could not extract some metrics: %s\n' \
                'metrics setted are: %s'
            raise Exception(error % (' ,'.join(unset_attributes),
                                     ' ,'.join(set(metrics))))
        return metrics


class Basic(Benchmark):
    """Basic shell script

    Environment variable:
        - LOCAL_PATH: perform tests on local disk
        - NETWORK_PATH: perform tests on network path (nfs, gpfs, ...)
        - OUTSIDE_URL: test URL (ping, download)
    """
    EXECUTABLE = osp.join(osp.dirname(osp.abspath(__file__)), 'basic.bash')
    CATEGORY = 'canary'
    PING_IPS_FILE = 'ping-ips.txt'
    PING_IPS = ['localhost']

    def __init__(self):
        super(Basic, self).__init__(
            attributes=dict(
                ping_ips=Basic.PING_IPS
            )
        )
    name = 'basic'

    description = "Basic linux functionalities of BB5."

    @property
    def execution_matrix(self):
        yield dict(
            category=Basic.CATEGORY,
            command=[Basic.EXECUTABLE]
        )

    def pre_execute(self, execution):
        del execution  # unused
        with open(Basic.PING_IPS_FILE, 'w') as ostr:
            for ip in self.attributes['ping_ips']:
                print(ip, file=ostr)

    @cached_property
    def metrics_extractors(self):
        return BasicExtractor()
