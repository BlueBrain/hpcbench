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

    def extract(self, outdir, metas):
        mapping = {
            'min': 'minimum',
            'avg': 'average',
            'max': 'maximum',
            'approx.  95 percentile': 'percentile95',
            'total time': 'total_time',
        }
        metrics = {}
        # parse stdout and extract desired metrics
        with open(self.stdout(outdir)) as istr:
            for line in istr:
                if line.strip() == self.STDOUT_IGNORE_PRIOR:
                    break
            for line in istr:
                line = line.strip()
                for attr, metric in mapping.items():
                    if line.startswith(attr + ':'):
                        value = line[len(attr + ':'):].lstrip()
                        value = self.KEEP_NUMBERS.sub('', value)
                        metrics[metric] = float(value)
        # ensure all metrics have been extracted
        unset_attributes = set(mapping.values()) - set(metrics)
        if any(unset_attributes):
            raise Exception('Could not extract some metrics: %s',
                            ' '.join(unset_attributes))
        return metrics


class Sysbench(Benchmark):
    """Benchmark wrapper for the sysbench utility
    """
    FEATURE_CPU = 'cpu'

    def __init__(self):
        super(Sysbench, self).__init__(
            attributes=dict(features=[Sysbench.FEATURE_CPU])
        )

    name = 'sysbench'

    description = """
        sysbench provides benchmarking capabilities for Linux.
        sysbench supports testing CPU, memory, file I/O, mutex
        performance, and even MySQL benchmarking.
        """

    @property
    def execution_matrix(self):
        if Sysbench.FEATURE_CPU in self.attributes['features']:
            for thread in [1, 4, 16]:
                for max_prime in [30]:
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
        plt.plot(metas['threads'], metrics['cpu__minimum'],
                 'r--', label='minimum')
        plt.plot(metas['threads'], metrics['cpu__maximum'],
                 'bs-', label='maximum')
        plt.plot(metas['threads'], metrics['cpu__average'],
                 'g^', label='average')
        plt.legend(loc='upper right', frameon=False)
        plt.xlabel('threads')
        plt.ylabel("t (sec)")
