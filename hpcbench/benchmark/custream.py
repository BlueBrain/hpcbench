"""HPCBench benchmark driver for cuda STREAM
    https://github.com/bcumming/cuda-stream
"""
import re

from cached_property import cached_property

from hpcbench.api import (
    Benchmark,
    Metrics,
    MetricsExtractor,
)
from hpcbench.toolbox.process import (
    find_executable,
)


class CUDAStreamExtractor(MetricsExtractor):
    """Ignore stdout until this line"""
    STDOUT_IGNORE_PRIOR = set([
        '-----------------------------------------------------------------',
    ])
    KEEP_NUMBERS = re.compile('[^0-9.]')
    SECTIONS = ['copy', 'scale', 'add', 'triad']
    REGEX = dict(
        copy=re.compile('^Copy:[ \t]*([\\d.]+)[ \t]*([\\d.]+)'
                        '[ \t]*([\\d.]+)[ \t]*([\\d.]+)'),
        scale=re.compile('^Scale:[ \t]*([\\d.]+)[ \t]*([\\d.]+)'
                         '[ \t]*([\\d.]+)[ \t]*([\\d.]+)'),
        add=re.compile('^Add:[ \t]*([\\d.]+)[ \t]*([\\d.]+)'
                       '[ \t]*([\\d.]+)[ \t]*([\\d.]+)'),
        triad=re.compile('^Triad:[ \t]*([\\d.]+)[ \t]*([\\d.]+)'
                         '[ \t]*([\\d.]+)[ \t]*([\\d.]+)')
    )

    METRICS = dict(
        copy_min_time=Metrics.Second,
        copy_avg_time=Metrics.Second,
        copy_max_time=Metrics.Second,
        copy_bandwidth=Metrics.GigaBytesPerSecond,
        scale_min_time=Metrics.Second,
        scale_avg_time=Metrics.Second,
        scale_max_time=Metrics.Second,
        scale_bandwidth=Metrics.GigaBytesPerSecond,
        add_min_time=Metrics.Second,
        add_avg_time=Metrics.Second,
        add_max_time=Metrics.Second,
        add_bandwidth=Metrics.GigaBytesPerSecond,
        triad_min_time=Metrics.Second,
        triad_avg_time=Metrics.Second,
        triad_max_time=Metrics.Second,
        triad_bandwidth=Metrics.GigaBytesPerSecond,
    )

    METRICS_NAMES = set(METRICS)

    @property
    def metrics(self):
        """ The metrics to be extracted.
            This property can not be replaced, but can be mutated as required
        """
        return CUDAStreamExtractor.METRICS

    def extract_metrics(self, outdir, metas):
        metrics = {}
        # parse stdout and extract desired metrics
        with open(self.stdout(outdir)) as istr:
            for line in istr:
                if line.strip() in self.STDOUT_IGNORE_PRIOR:
                    break
            for line in istr:
                line = line.strip()
                CUDAStreamExtractor._parse_line(line, metrics)
        return metrics

    @classmethod
    def _parse_line(cls, line, metrics):
        for sect, regex in cls.REGEX.items():
            search = regex.search(line)
            if search:
                metrics[sect + "_bandwidth"] = float(search.group(1))
                metrics[sect + "_avg_time"] = float(search.group(2))
                metrics[sect + "_min_time"] = float(search.group(3))
                metrics[sect + "_max_time"] = float(search.group(4))
                return


class CUDAStream(Benchmark):
    """Benchmark wrapper for the cuda-stream utility
    """
    name = 'custream'

    description = "Provides memory bandwidth benchmarking for NVIDIA GPUs."

    DEFAULT_EXECUTABLE = 'stream'
    DEFAULT_THREADS_PER_BLOCK = [64, 128, 192, 256, 512, 1024]

    def __init__(self):
        super(CUDAStream, self).__init__(
            attributes=dict(
                blocksizes=CUDAStream.DEFAULT_THREADS_PER_BLOCK,
                executable=CUDAStream.DEFAULT_EXECUTABLE,
            )
        )

    @cached_property
    def executable(self):
        """Get path to cuda stream executable
        """
        return self.attributes['executable']

    @property
    def blocksizes(self):
        """List of threads per block the command is executed with"""
        return [
            str(e)
            for e in self.attributes['blocksizes']
        ]

    def execution_matrix(self, context):
        del context  # unused
        for nthreads in self.blocksizes:
            yield dict(
                category=CUDAStream.name,
                command=[find_executable(self.executable),
                         '-b', nthreads],
                metas=dict(blocksizes=nthreads),
            )

    @cached_property
    def metrics_extractors(self):
        return CUDAStreamExtractor()

    @property
    def plots(self):
        return {
            CUDAStream.name: [
                dict(
                    name="{hostname} {category} bandwidth",
                    series=dict(
                        metas=['blocksizes'],
                        metrics=[
                            'copy_bandwidth',
                            'scale_bandwidth',
                            'add_bandwidth',
                            'triad_bandwidth',
                            # 'copy_min_time', 'copy_avg_time',
                            # 'copy_max_time', 'scale_min_time',
                            # 'scale_avg_time', 'scale_max_time',
                            # 'add_min_time', 'add_avg_time',
                            # 'add_max_time', 'triad_min_time',
                            # 'triad_avg_time', 'triad_max_time',
                        ],

                    ),
                    plotter=CUDAStream.plot_bandwidth
                ),
            ]
        }

    @classmethod
    def plot_bandwidth(cls, plt, description, metas, metrics):
        """Generate timings plot
        """
        del description  # unused
        xpos = range(len(metas['blocksizes']))
        plt.bar([x - 0.3 for x in xpos], metrics['copy_bandwidth'], width=0.2,
                label='copy')
        plt.bar([x - 0.1 for x in xpos], metrics['scale_bandwidth'],
                width=0.2, label='scale')
        plt.bar([x + 0.1 for x in xpos], metrics['add_bandwidth'], width=0.2,
                label='add')
        plt.bar([x + 0.3 for x in xpos], metrics['triad_bandwidth'], width=0.2,
                label='triad')
        plt.legend(loc='upper right', frameon=False)
        plt.xticks(xpos, [str(t) for t in metas['blocksizes']])
        plt.xlabel('threads / block')
        plt.ylabel("time (s)")
