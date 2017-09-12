"""The Scalable HeterOgeneous Computing (SHOC) Benchmark Suite
   https://github.com/vetter/shoc
"""
import os.path as osp
import re
import shutil

from cached_property import cached_property

from hpcbench.api import (
    Benchmark,
    Metric,
    Metrics,
    MetricsExtractor,
)
from hpcbench.toolbox.process import find_executable

class SHOCExtractor(MetricsExtractor):
    REGEX = dict(
        # this regex extract flops/bandwidth
        result=re.compile(
            r'^\s+[\w]+\:\s+(\d*\.?\d+)'
        ),
    )

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

    @property
    def metrics(self):
        """ The metrics to be extracted.
            This property can not be replaced, but can be mutated as required
        """
        return SHOCExtractor.METRICS

    def extract_value(self, line):
        expr = re.compile(r'[\w]+\:\s+(\d*\.?\d+)')
        value = expr.search(line).group(1)
        return float(value)

    def extract(self, outdir, metas):
        metrics = {}
        # parse stdout and extract desired metrics
        with open(self.stdout(outdir)) as istr:
            for line in istr:
                line = line.strip()
                if line.find('result for bspeed_download:') != -1:
                    metrics["h2d_bw"] = self.extract_value(line)
                elif line.find('result for bspeed_readback:') != -1:
                    metrics["d2h_bw"] =  self.extract_value(line)
                elif line.find('result for maxspflops:') != -1:
                    metrics["flops_sp"] = self.extract_value(line)
                elif line.find('result for maxdpflops:') != -1:
                    metrics["flops_dp"] = self.extract_value(line)
                elif line.find('result for gmem_readbw:') != -1:
                    metrics["gmem_readbw"] = self.extract_value(line)
                elif line.find('result for gmem_writebw:') != -1:
                    metrics["gmem_writebw"] = self.extract_value(line)
                elif line.find('result for lmem_readbw:') != -1:
                    metrics["lmem_readbw"] = self.extract_value(line)
                elif line.find('result for lmem_writebw:') != -1:
                    metrics["lmem_writebw"] = self.extract_value(line)

        # ensure all metrics have been extracted
        unset_attributes = SHOCExtractor.METRICS_NAMES - set(metrics)
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
    DEFAULT_DEVICE = 'gpu'
    DEFAULT_EXECUTABLE = 'shocdriver'

    def __init__(self):
        # locate `stream_c` executable
        super(SHOC, self).__init__(
            attributes=dict(
                data="",
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
            category=SHOC.DEFAULT_DEVICE,
            command=[
                './' + osp.basename(self.executable),
            ],
            environment=dict(
                CUDA_VISIBLE_DEVICES=str(self.attributes['device'][0]),
            ),
        )

    @cached_property
    def metrics_extractors(self):
        return SHOCExtractor()

    def pre_execute(self, execution):
        data = self.attributes['data']
        with open('SHOC.dat', 'w') as ostr:
            ostr.write(data)
        shutil.copy(self.executable, '.')
