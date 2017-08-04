"""HPCBench benchmark driver for STREAM
    https://www.cs.virginia.edu/stream/FTP/Code/
"""
import re

from cached_property import cached_property

from hpcbench.api import (
    Benchmark,
    Metrics,
    MetricsExtractor,
)
from hpcbench.toolbox.process import find_executable


class StreamExtractor(MetricsExtractor):
    """Ignore stdout until this line"""
    STDOUT_IGNORE_PRIOR = set([
        'Function      Rate (MB/s)   Avg time     Min time     Max time',
        'Function    Best Rate MB/s  Avg time     Min time     Max time',
    ])
    KEEP_NUMBERS = re.compile('[^0-9.]')
    SECTIONS = ['copy', 'scale', 'add', 'triad']
    regex = dict(
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
        copy_min_time=Metrics.Milisecond,
        copy_avg_time=Metrics.Milisecond,
        copy_max_time=Metrics.Milisecond,
        copy_bandwidth=Metrics.MegaBytesPerSecond,
        scale_min_time=Metrics.Milisecond,
        scale_avg_time=Metrics.Milisecond,
        scale_max_time=Metrics.Milisecond,
        scale_bandwidth=Metrics.MegaBytesPerSecond,
        add_min_time=Metrics.Milisecond,
        add_avg_time=Metrics.Milisecond,
        add_max_time=Metrics.Milisecond,
        add_bandwidth=Metrics.MegaBytesPerSecond,
        triad_min_time=Metrics.Milisecond,
        triad_avg_time=Metrics.Milisecond,
        triad_max_time=Metrics.Milisecond,
        triad_bandwidth=Metrics.MegaBytesPerSecond,
    )

    METRICS_NAMES = set(METRICS)

    @property
    def metrics(self):
        """ The metrics to be extracted.
            This property can not be replaced, but can be mutated as required
        """
        return StreamExtractor.METRICS

    def extract(self, outdir, metas):
        metrics = {}
        # parse stdout and extract desired metrics
        with open(self.stdout(outdir)) as istr:
            for line in istr:
                if line.strip() in self.STDOUT_IGNORE_PRIOR:
                    break
            for line in istr:
                line = line.strip()

                for sect in self.SECTIONS:
                    search = self.regex[sect].search(line)
                    if search:
                        metrics[sect + "_bandwidth"] = float(search.group(1))
                        metrics[sect + "_avg_time"] = float(search.group(2))
                        metrics[sect + "_min_time"] = float(search.group(3))
                        metrics[sect + "_max_time"] = float(search.group(4))

        # ensure all metrics have been extracted
        unset_attributes = StreamExtractor.METRICS_NAMES - set(metrics)
        if any(unset_attributes):
            error = \
                'Could not extract some metrics: %s\n' \
                'metrics setted are: %s'
            raise Exception(error % (' ,'.join(unset_attributes),
                                     ' ,'.join(set(metrics))))
        return metrics


class Stream(Benchmark):
    """Benchmark wrapper for the streambench utility
    """
    DEFAULT_THREADS = [1, 4, 16, 26, 52, 104]
    DEFAULT_FEATURES = ["cache", "mcdram", "cpu"]

    FEATURE_CPU = 'cpu'
    FEATURES = dict(
        cache=[dict(args=["--all"], name="all")],
        mcdram=[
            dict(
                args=["-m", "0"],
                name="numa_0"
            ),
            dict(
                args=["-m", "1"],
                name="numa_1"
            )
        ],
        cpu=[
            dict(
                args=["--all"],
                name="all"
            )
        ],
    )

    def __init__(self):
        # locate `stream_c` executable
        stream_c = find_executable('stream_c', required=False) or 'stream_c'
        super(Stream, self).__init__(
            attributes=dict(
                features=Stream.DEFAULT_FEATURES,
                threads=Stream.DEFAULT_THREADS,
                stream_c=stream_c,
            )
        )
    name = 'stream'

    description = "Provides memory bandwidth benchmarking capabilities."

    @property
    def execution_matrix(self):
        stream_c = self.attributes['stream_c']
        for feature in self.attributes['features']:
            if feature in self.FEATURES.keys():
                for numa_policy in self.FEATURES[feature]:
                    for thread in self.attributes['threads']:
                        yield dict(
                            category=Stream.FEATURE_CPU,
                            command=[
                                'numactl',
                                " ".join(numa_policy['args']),
                                stream_c,
                            ],
                            metas=dict(
                                threads=thread,
                                numa_policy=numa_policy['name'],
                                memory_type=feature,
                            ),
                            environment=dict(
                                OMP_NUM_THREADS=str(thread),
                                KMP_AFFINITY='scatter'
                            ),
                        )

    @cached_property
    def metrics_extractors(self):
        return {
            Stream.FEATURE_CPU: StreamExtractor(),
        }

    @property
    def plots(self):
        return {
            Stream.FEATURE_CPU: [
                dict(
                    name="{hostname} {category} timing",
                    series=dict(
                        metas=['thread'],
                        metrics=[
                            'cpu__copy_min_time', 'cpu__copy_avg_time',
                            'cpu__copy_max_time', 'cpu__scale_min_time',
                            'cpu__scale_avg_time', 'cpu__scale_max_time',
                            'cpu__add_min_time', 'cpu__add_avg_time',
                            'cpu__add_max_time', 'cpu__triad_min_time',
                            'cpu__triad_avg_time', 'cpu__triad_max_time',
                        ],

                    ),
                    plotter=Stream.plot_timing
                ),
            ]
        }

    @classmethod
    def plot_timing(cls, plt, description, metas, metrics):
        """Generate timings plot
        """
        del description  # unused
        plt.plot(metas['thread'], metrics['cpu__copy_min_time'],
                 'bs-', label='minimum')
        plt.plot(metas['thread'], metrics['cpu__copy_avg_time'],
                 'g^', label='average')
        plt.plot(metas['thread'], metrics['cpu__copy_max_time'],
                 'g^', label='maximum')
        plt.legend(loc='upper right', frameon=False)
        plt.xlabel('thread')
        plt.ylabel("t (sec)")
