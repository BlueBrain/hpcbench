"""HPCBench benchmark driver for sysbench

    https://github.com/akopytov/sysbench
"""
import re

from cached_property import cached_property

from hpcbench.api import (
    Benchmark,
    Metrics,
    MetricsExtractor,
)


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
            minimum=Metrics.Milisecond,
            average=Metrics.Milisecond,
            maximum=Metrics.Milisecond,
            percentile95=Metrics.Milisecond,
            total_time=Metrics.Second
        )

    @property
    def metrics(self):
        """ The metrics to be extracted.
            This property can not be replaced, but can be mutated as required
        """
        return self._metrics

    def extract_metrics(self, outdir, metas):
        metrics = {}
        # parse stdout and extract desired metrics
        with open(self.stdout(outdir)) as istr:
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
                value = line[len(attr + ':'):].lstrip()
                value = cls.KEEP_NUMBERS.sub('', value)
                metrics[metric] = float(value)
                return


class Sysbench(Benchmark):
    """Benchmark wrapper for the sysbench utility
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

    description = """
        sysbench provides benchmarking capabilities for Linux.
        sysbench supports testing CPU, memory, file I/O, mutex
        performance, and even MySQL benchmarking.
        """

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
                            'run'
                        ],
                        metas=dict(
                            threads=thread,
                            max_prime=max_prime
                        )
                    )

    @cached_property
    def metrics_extractors(self):
        return CpuExtractor()

    @property
    def plots(self):
        return {
            Sysbench.FEATURE_CPU: [
                dict(
                    name="{hostname} {category} timing",
                    #  for_each=['max_prime'],  TODO
                    select=dict(
                        metas__max_prime=30
                    ),
                    series=dict(
                        metas=['-threads'],
                        metrics=['minimum', 'average',
                                 'maximum', 'percentile95'],
                    ),
                    plotter=Sysbench.plot_timing
                ),
            ]
        }

    @classmethod
    def plot_timing(cls, plt, description, metas, metrics):
        """Generate timings plot
        """
        del description  # unused
        plt.plot(metas['threads'], metrics['minimum'],
                 'r--', label='minimum')
        plt.plot(metas['threads'], metrics['maximum'],
                 'bs-', label='maximum')
        plt.plot(metas['threads'], metrics['average'],
                 'g^', label='average')
        plt.legend(loc='upper right', frameon=False)
        plt.xlabel('threads')
        plt.ylabel("t (sec)")
