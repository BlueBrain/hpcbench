"""The Scalable HeterOgeneous Computing (SHOC) Benchmark Suite
   https://github.com/vetter/shoc
"""
import re

from cached_property import cached_property

from hpcbench.api import (
    Benchmark,
    Metrics,
    MetricsExtractor,
)
from hpcbench.toolbox.process import find_executable


class SHOCExtractor(MetricsExtractor):
    METRICS = dict(
        h2d_bw=Metrics.MegaBytesPerSecond,
        d2h_bw=Metrics.MegaBytesPerSecond,
        flops_dp=Metrics.Flops,
        flops_sp=Metrics.Flops,
        gmem_readbw=Metrics.MegaBytesPerSecond,
        gmem_writebw=Metrics.MegaBytesPerSecond,
        lmem_readbw=Metrics.MegaBytesPerSecond,
        lmem_writebw=Metrics.MegaBytesPerSecond,
    )
    METRICS_NAMES = set(METRICS)
    EXPR = re.compile(r'[\w]+\:\s+(\d*\.?\d+)')
    MATCHING_LINES = {
        'result for bspeed_download:': 'h2d_bw',
        'result for bspeed_readback:': 'd2h_bw',
        'result for maxspflops:': 'flops_sp',
        'result for maxdpflops:': 'flops_dp',
        'result for gmem_readbw:': 'gmem_readbw',
        'result for gmem_writebw:': 'gmem_writebw',
        'result for lmem_readbw:': 'lmem_readbw',
        'result for lmem_writebw:': 'lmem_writebw'
    }

    @property
    def metrics(self):
        """ The metrics to be extracted.
            This property can not be replaced, but can be mutated as required
        """
        return SHOCExtractor.METRICS

    @classmethod
    def extract_value(cls, line):
        value = cls.EXPR.search(line).group(1)
        return float(value)

    def extract(self, outdir, metas):
        metrics = {}
        # parse stdout and extract desired metrics
        with open(self.stdout(outdir)) as istr:
            for line in istr:
                for match, attr in SHOCExtractor.MATCHING_LINES.items():
                    if line.find(match) != -1:
                        metrics[attr] = self.extract_value(line)
                        break
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


class SHOC(Benchmark):
    """Benchmark wrapper for the SHOCbench utility
    """
    DEFAULT_DEVICE = '0'
    DEFAULT_EXECUTABLE = 'shocdriver'
    CATEGORY = 'gpu'

    def __init__(self):
        # locate `shocdriver` executable
        super(SHOC, self).__init__(
            attributes=dict(
                device=SHOC.DEFAULT_DEVICE,
                executable=SHOC.DEFAULT_EXECUTABLE
            )
        )
    name = 'shoc'

    description = "Multiple benchmark of the GPU."

    @cached_property
    def executable(self):
        """Get absolute path to executable
        """
        return find_executable(self.attributes['executable'])

    @property
    def execution_matrix(self):
        yield dict(
            category=SHOC.CATEGORY,
            command=[
                self.executable,
                '-cuda',
            ],
            environment=dict(
                CUDA_VISIBLE_DEVICES=str(self.attributes['device']),
            ),
        )

    @cached_property
    def metrics_extractors(self):
        return SHOCExtractor()
