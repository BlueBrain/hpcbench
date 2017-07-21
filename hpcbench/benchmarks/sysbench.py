from hpcbench.api import (
    Benchmark,
    MetricsExtractor,
)


class cpu_extractor(MetricsExtractor):
    """Ignore stdout until this line"""
    STDOUT_IGNORE_PRIOR = 'Test execution summary:'

    def metrics(self):
        return dict(
            mininum=dict(type=float, unit='ms'),
            average=dict(type=float, unit='ms'),
            maximum=dict(type=float, unit='ms'),
            percentile95=dict(type=float, unit='ms'),
            total_time=dict(type=float, unit='s'),
        )

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
            look_after_data = False
            for line in istr:
                line = line.strip()
                if not look_after_data:
                    if line == self.STDOUT_IGNORE_PRIOR:
                        look_after_data = True
                        continue
                else:
                    for attr, metric in mapping.items():
                        if line.startswith(attr + ':'):
                            value = line[len(attr + ':'):].lstrip()
                            value = filter(lambda e: not e.isalpha(), value)
                            metrics[metric] = float(value)
        # ensure all metrics have been extracted
        unset_attributes = set(mapping.values()) - set(metrics)
        if any(unset_attributes):
            raise Exception('Could not extract some metrics: %s',
                            ' '.join(unset_attributes))
        return metrics


class Sysbench(Benchmark):
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

    def execution_matrix(self):
        if Sysbench.FEATURE_CPU in self.attributes['features']:
            for thread in [1, 4, 16]:
                for max_prime in [10000, 20000]:
                    yield dict(
                        category='cpu',
                        command=[
                            'sysbench',
                            '--test=cpu',
                            '--num-threads=%s' % thread,
                            '--cpu-max-prime=%s' % max_prime,
                            'run'
                        ],
                        metas=dict(
                            thread=thread,
                            max_prime=max_prime
                        )
                    )

    def metrics_extractors(self):
        return {
            Sysbench.FEATURE_CPU: cpu_extractor(),
        }

    def plots(self):
        return {
            Sysbench.FEATURE_CPU: [
                dict(
                    name="{category} timing",
                    #for_each=['max_prime'],  TODO
                    select=dict(
                        metas__max_prime=10000
                    ),
                    series=dict(
                        metas=['-thread'],
                        metrics=['cpu__minimum', 'cpu__average',
                                 'cpu__maximum', 'cpu__percentile95'],
                    ),
                    plotter=self.plot_timing
                ),
            ]
        }

    def plot_timing(self, plt, description, metas, metrics):
        plt.plot(
            metas['thread'], metrics['cpu__minimum'], 'r--',
            metas['thread'], metrics['cpu__maximum'], 'bs',
            metas['thread'], metrics['cpu__average'], 'g^',
        )
