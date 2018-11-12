from __future__ import division

from cached_property import cached_property
from hpcbench.api import (
    Benchmark,
    Metric,
    MetricsExtractor
)
from hpcbench.toolbox.process import find_executable


class {{ cookiecutter.benchmark | capitalize }}Extractor(MetricsExtractor):
    @cached_property
    def metrics(self):
        return dict(
            computation_time=Metric.Second
        )

    def extract_metrics(self, metas):
        LINE_PATTERN = 'computation time: '
        with open(self.stdout) as istr:
            for line in istr:
                line = line.rstrip()
                if LINE_PATTERN in line:
                    metric = line[len(LINE_PATTERN):]
                    return dict(computation_time=float(metric))
        raise Exception('Could not extract metric computation time '
                        'from standard output')


class {{ cookiecutter.benchmark | capitalize }}(Benchmark):
    """{{ cookiecutter.benchmark }} benchmark

    More detailed description of the benchmark class
    """
    name = "{{ cookiecutter.benchmark }}"

    DEFAULT_EXECUTABLE = "{{ cookiecutter.benchmark }}"
    CATEGORY = 'main'

    @cached_property
    def executable(self):
        """Get absolute path to the {{ cookiecutter.benchmark }} utility"""
        return find_executable(self.attributes['executable'])

    def execution_matrix(self, context):
        del context  # unused
        yield dict(
            category={{ cookiecutter.benchmark | capitalize }}.CATEGORY,
            command=[self.executable ]
        )

    @cached_property
    def metrics_extractors(self):
        return {{ cookiecutter.benchmark | capitalize }}Extractor()
