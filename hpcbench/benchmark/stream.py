"""HPCBench benchmark driver for STREAM
    https://www.cs.virginia.edu/stream/FTP/Code/
"""
import re

from cached_property import cached_property

from hpcbench.api import Benchmark, Metrics, MetricsExtractor
from hpcbench.toolbox.process import find_executable


class StreamExtractor(MetricsExtractor):
    """Ignore stdout until this line"""

    STDOUT_IGNORE_PRIOR = set(
        [
            'Function      Rate (MB/s)   Avg time     Min time     Max time',
            'Function    Best Rate MB/s  Avg time     Min time     Max time',
        ]
    )
    KEEP_NUMBERS = re.compile('[^0-9.]')
    SECTIONS = ['copy', 'scale', 'add', 'triad']
    REGEX = dict(
        copy=re.compile(
            '^Copy:[ \t]*([\\d.]+)[ \t]*([\\d.]+)' '[ \t]*([\\d.]+)[ \t]*([\\d.]+)'
        ),
        scale=re.compile(
            '^Scale:[ \t]*([\\d.]+)[ \t]*([\\d.]+)' '[ \t]*([\\d.]+)[ \t]*([\\d.]+)'
        ),
        add=re.compile(
            '^Add:[ \t]*([\\d.]+)[ \t]*([\\d.]+)' '[ \t]*([\\d.]+)[ \t]*([\\d.]+)'
        ),
        triad=re.compile(
            '^Triad:[ \t]*([\\d.]+)[ \t]*([\\d.]+)' '[ \t]*([\\d.]+)[ \t]*([\\d.]+)'
        ),
    )

    METRICS = dict(
        copy_min_time=Metrics.Millisecond,
        copy_avg_time=Metrics.Millisecond,
        copy_max_time=Metrics.Millisecond,
        copy_bandwidth=Metrics.MegaBytesPerSecond,
        scale_min_time=Metrics.Millisecond,
        scale_avg_time=Metrics.Millisecond,
        scale_max_time=Metrics.Millisecond,
        scale_bandwidth=Metrics.MegaBytesPerSecond,
        add_min_time=Metrics.Millisecond,
        add_avg_time=Metrics.Millisecond,
        add_max_time=Metrics.Millisecond,
        add_bandwidth=Metrics.MegaBytesPerSecond,
        triad_min_time=Metrics.Millisecond,
        triad_avg_time=Metrics.Millisecond,
        triad_max_time=Metrics.Millisecond,
        triad_bandwidth=Metrics.MegaBytesPerSecond,
    )

    METRICS_NAMES = set(METRICS)

    @property
    def metrics(self):
        """ The metrics to be extracted.
            This property can not be replaced, but can be mutated as required
        """
        return StreamExtractor.METRICS

    def extract_metrics(self, metas):
        metrics = {}
        # parse stdout and extract desired metrics
        with open(self.stdout) as istr:
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
    """memory bandwidth benchmark
    """

    name = 'stream'

    DEFAULT_EXECUTABLE = 'stream_c'
    DEFAULT_THREADS = [1, 4, 16, 26, 52, 104]

    def __init__(self):
        super(Stream, self).__init__(
            attributes=dict(
                threads=Stream.DEFAULT_THREADS, executable=Stream.DEFAULT_EXECUTABLE
            )
        )

    @cached_property
    def executable(self):
        """Get path to stream executable
        """
        return self.attributes['executable']

    @property
    def threads(self):
        """List of possible threads the command is executed with"""
        return [str(e) for e in self.attributes['threads']]

    def execution_matrix(self, context):
        del context  # unused
        for thread in self.threads:
            yield dict(
                category=Stream.name,
                command=[find_executable(self.executable, required=False)],
                metas=dict(threads=thread),
                environment=dict(OMP_NUM_THREADS=thread, KMP_AFFINITY='scatter'),
            )

    @cached_property
    def metrics_extractors(self):
        return StreamExtractor()
