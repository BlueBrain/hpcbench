from collections import Mapping
import inspect
import os
import os.path as osp
import shutil
import yaml
from six import with_metaclass
from abc import ABCMeta, abstractmethod

from hpcbench.api import (
    Benchmark,
    MetricsExtractor,
)
from hpcbench.driver import YAML_REPORT_FILE, MetricsDriver
from hpcbench.toolbox.contextlib_ext import (
    mkdtemp,
    pushd,
)


class AbstractBenchmarkTest(with_metaclass(ABCMeta, object)):
    @abstractmethod
    def get_benchmark_clazz(self):
        """
        :return: Benchmark class to test
        :rtype: subclass of ``hpcbench.api.Benchmark``
        """
        raise NotImplementedError

    @abstractmethod
    def get_benchmark_categories(self):
        """
        :return: List of categories to tests
        :rtype: string list
        """
        raise NotImplementedError

    @abstractmethod
    def get_expected_metrics(self, category):
        """
        :return: metrics extracted from the sample output
        :rtype: dictionary name -> value
        """
        raise NotImplementedError

    def create_sample_run(self, category):
        pyfile = inspect.getfile(self.__class__)
        for output in ['stdout', 'stderr']:
            out = osp.splitext(pyfile)[0] + '.' + category + '.' + output
            if osp.isfile(out):
                shutil.copy(out, output + '.txt')

    def test_class_has_name(self):
        clazz_name = self.get_benchmark_clazz().name
        assert isinstance(clazz_name, str)
        assert clazz_name  # Not None or empty

    def test_class_is_registered(self):
        clazz = self.get_benchmark_clazz()
        assert issubclass(clazz, Benchmark)
        # We could access the list of subclasses, but bit horrible
        # clazz in Benchmark.__subclasses__

    def test_metrics_extraction(self):
        for category in self.get_benchmark_categories():
            self.check_category_metrics(category)

    def check_category_metrics(self, category):
        self.maxDiff = None
        with mkdtemp() as top_dir, pushd(top_dir):
            with open(YAML_REPORT_FILE, 'w') as ostr:
                yaml.dump(
                    dict(
                        children=['sample-run'],
                        category=category
                    ),
                    ostr
                )
            with pushd('sample-run'):
                self.create_sample_run(category)
                clazz = self.get_benchmark_clazz()
                benchmark = clazz()
                with open(YAML_REPORT_FILE, 'w') as ostr:
                    yaml.dump(dict(category=category), ostr)
                md = MetricsDriver('test-category', benchmark)
                report = md()
                parsed_metrics = report.get('metrics', {})
                expected_metrics = self.get_expected_metrics(category)
                assert parsed_metrics == expected_metrics

    def test_has_description(self):
        clazz = self.get_benchmark_clazz()
        assert isinstance(clazz.description, str)

    def test_execution_matrix(self):
        clazz = self.get_benchmark_clazz()
        benchmark = clazz()
        exec_matrix = benchmark.execution_matrix
        exec_matrix = list(exec_matrix)
        assert isinstance(exec_matrix, list)

        run_keys = {'category', 'command', 'metas', 'environment'}
        for runs in exec_matrix:
            assert isinstance(runs, dict)
            assert 'category' in runs
            assert isinstance(runs['category'], str)
            assert runs['category']
            assert 'command' in runs
            assert isinstance(runs['command'], list)
            assert runs['command']
            for arg in runs['command']:
                assert isinstance(arg, str)
            keys = set(runs.keys())
            assert keys.issubset(run_keys)

    def test_metrics_extractors(self):
        clazz = self.get_benchmark_clazz()
        benchmark = clazz()
        all_extractors = benchmark.metrics_extractors
        assert isinstance(all_extractors, (Mapping, list, MetricsExtractor))
        def _check_extractor(exts):
            if not isinstance(exts, list):
                exts = [exts]
            for ext in exts:
                assert isinstance(ext, MetricsExtractor)

        if isinstance(all_extractors, Mapping):
            for name, extractors in all_extractors.items():
                assert isinstance(name, str)
                assert name
                _check_extractor(extractors)
        else:
            _check_extractor(all_extractors)
