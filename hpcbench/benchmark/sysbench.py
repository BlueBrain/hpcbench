"""HPCBench benchmark driver for sysbench

    https://github.com/akopytov/sysbench
"""
import re

from cached_property import cached_property

from hpcbench.api import Benchmark, Metrics, MetricsExtractor


class CpuExtractor(MetricsExtractor):
    """Ignore stdout until this line"""

    STDOUT_IGNORE_PRIOR = 'Test execution summary:'
    KEEP_NUMBERS = re.compile('[^0-9.]')
    TEXT_TO_METRIC = {
        'min': 'minimum',
        'avg': 'average',
        'max': 'maximum',
        'approx.  95 percentile': 'percentile95',
        'total time': 'total_time',
    }

    def __init__(self):
        self._metrics = dict(
            minimum=Metrics.Millisecond,
            average=Metrics.Millisecond,
            maximum=Metrics.Millisecond,
            percentile95=Metrics.Millisecond,
            total_time=Metrics.Second,
        )

    @property
    def metrics(self):
        """ The metrics to be extracted.
            This property can not be replaced, but can be mutated as required
        """
        return self._metrics

    def extract_metrics(self, metas):
        metrics = {}
        # parse stdout and extract desired metrics
        with open(self.stdout) as istr:
            for line in istr:
                if line.strip() == self.STDOUT_IGNORE_PRIOR:
                    break
            for line in istr:
                CpuExtractor._parse_line(line, metrics)
        return metrics

    @classmethod
    def _parse_line(cls, line, metrics):
        line = line.strip()
        for attr, metric in cls.TEXT_TO_METRIC.items():
            if line.startswith(attr + ':'):
                value = line[len(attr + ':') :].lstrip()
                value = cls.KEEP_NUMBERS.sub('', value)
                metrics[metric] = float(value)
                return


class Sysbench(Benchmark):
    """Cross-platform and multi-threaded benchmark tool

    Current features allow to test the following system parameters:
      * file I/O performance
      * scheduler performance
      * memory allocation and transfer speed
      * POSIX threads implementation performance
      * database server performance (OLTP benchmark)
    """

    FEATURE_CPU = 'cpu'
    MAX_PRIMES = [30]
    THREADS = [1, 4, 16]

    def __init__(self):
        super(Sysbench, self).__init__(
            attributes=dict(
                features=[Sysbench.FEATURE_CPU],
                max_primes=Sysbench.MAX_PRIMES,
                threads=Sysbench.THREADS,
            )
        )

    name = 'sysbench'

    @property
    def features(self):
        """List of features to test"""
        return self.attributes['features']

    @property
    def max_primes(self):
        """List of complexities of the CPU benchmark to test
        """
        return self.attributes['max_primes']

    @property
    def threads(self):
        """List of threads sysbench is tested against
        """
        return self.attributes['threads']

    def execution_matrix(self, context):
        del context  # unused
        if Sysbench.FEATURE_CPU in self.attributes['features']:
            for thread in self.threads:
                for max_prime in self.max_primes:
                    yield dict(
                        category=Sysbench.FEATURE_CPU,
                        command=[
                            'sysbench',
                            '--test=cpu',
                            '--num-threads=%s' % thread,
                            '--cpu-max-prime=%s' % max_prime,
                            'run',
                        ],
                        metas=dict(threads=thread, max_prime=max_prime),
                    )

    @cached_property
    def metrics_extractors(self):
        return CpuExtractor()
