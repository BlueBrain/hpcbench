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
from hpcbench.toolbox.process import (
    find_executable,
    physical_cpus,
)


class StreamExtractor(MetricsExtractor):
    """Ignore stdout until this line"""
    STDOUT_IGNORE_PRIOR = set([
        'Function      Rate (MB/s)   Avg time     Min time     Max time',
        'Function    Best Rate MB/s  Avg time     Min time     Max time',
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

    def extract_metrics(self, outdir, metas):
        metrics = {}
        # parse stdout and extract desired metrics
        with open(self.stdout(outdir)) as istr:
            for line in istr:
                if line.strip() in self.STDOUT_IGNORE_PRIOR:
                    break
            for line in istr:
                line = line.strip()
                StreamExtractor._parse_line(line, metrics)
        return metrics

    @classmethod
    def _parse_line(cls, line, metrics):
        for sect in cls.SECTIONS:
            search = cls.REGEX[sect].search(line)
            if search:
                metrics[sect + "_bandwidth"] = float(search.group(1))
                metrics[sect + "_avg_time"] = float(search.group(2))
                metrics[sect + "_min_time"] = float(search.group(3))
                metrics[sect + "_max_time"] = float(search.group(4))
                return


class Stream(Benchmark):
    """Benchmark wrapper for the streambench utility
    """
    name = 'stream'

    description = "Provides memory bandwidth benchmarking capabilities."

    DEFAULT_EXECUTABLE = 'stream_c'
    DEFAULT_THREADS = [1, 4, 16, 26, 52, 104]
    DEFAULT_FEATURES = {"cache", "mcdram", "cpu"}

    FEATURE_CPU = 'cpu'

    @cached_property
    def features_config(self):
        return dict(
            cache=[dict(args=["--all"], name="all")],
            mcdram=[
                dict(
                    args=['-m', str(socket)],
                    name='numa_' + str(socket)
                )
                for socket in range(physical_cpus())
            ],
            cpu=[
                dict(
                    args=["--all"],
                    name="all"
                )
            ],
        )

    def __init__(self):
        super(Stream, self).__init__(
            attributes=dict(
                features=Stream.DEFAULT_FEATURES,
                threads=Stream.DEFAULT_THREADS,
                executable=Stream.DEFAULT_EXECUTABLE,
            )
        )

    @cached_property
    def executable(self):
        """Get path to iperf executable
        """
        return self.attributes['executable']

    @property
    def features(self):
        """List of tested features among "cache", "mcdram", and "cpu"
        """
        return Stream.DEFAULT_FEATURES & set(self.attributes['features'])

    @property
    def threads(self):
        """List of possible threads the command is executed with"""
        return [
            str(e)
            for e in self.attributes['threads']
        ]

    def execution_matrix(self, context):
        del context  # unused
        for feature in self.features:
            for numa_policy in self.features_config[feature]:
                for thread in self.threads:
                    yield dict(
                        category=Stream.FEATURE_CPU,
                        command=[
                            'numactl',
                            " ".join(numa_policy['args']),
                            find_executable(self.executable),
                        ],
                        metas=dict(
                            threads=thread,
                            numa_policy=numa_policy['name'],
                            memory_type=feature,
                        ),
                        environment=dict(
                            OMP_NUM_THREADS=thread,
                            KMP_AFFINITY='scatter'
                        ),
                    )

    @cached_property
    def metrics_extractors(self):
        return StreamExtractor()

    @property
    def plots(self):
        return {
            Stream.FEATURE_CPU: [
                dict(
                    name="{hostname} {category} timing",
                    series=dict(
                        metas=['thread'],
                        metrics=[
                            'copy_min_time', 'copy_avg_time',
                            'copy_max_time', 'scale_min_time',
                            'scale_avg_time', 'scale_max_time',
                            'add_min_time', 'add_avg_time',
                            'add_max_time', 'triad_min_time',
                            'triad_avg_time', 'triad_max_time',
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
        plt.plot(metas['threads'], metrics['copy_min_time'],
                 'bs-', label='minimum')
        plt.plot(metas['threads'], metrics['copy_avg_time'],
                 'g^', label='average')
        plt.plot(metas['threads'], metrics['copy_max_time'],
                 'g^', label='maximum')
        plt.legend(loc='upper right', frameon=False)
        plt.xlabel('thread')
        plt.ylabel("t (sec)")
