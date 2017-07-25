import inspect
import os
import os.path as osp
import shutil
import yaml

from hpcbench.api import (
    Benchmark,
    MetricsExtractor,
)
from hpcbench.driver import YAML_REPORT_FILE, MetricsDriver
from hpcbench.toolbox.contextlib_ext import (
    mkdtemp,
    pushd,
)


class AbstractBenchmark(object):
    def get_benchmark_clazz(self):
        """
        :return: Benchmark class to test
        :rtype: subclass of ``hpcbench.api.Benchmark``
        """
        raise NotImplementedError

    def get_benchmark_categories(self):
        """
        :return: List of categories to tests
        :rtype: string list
        """
        raise NotImplementedError

    def get_expected_metrics(self, category):
        """
        :return: extract metrics from sample output for the given category
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
        clazz = self.get_benchmark_clazz()
        name = clazz.name
        self.assertIsInstance(name, str)
        self.assertTrue(len(name))

    def test_class_is_registered(self):
        clazz = self.get_benchmark_clazz()
        self.assertEqual(
            Benchmark.get_subclass(clazz.name),
            clazz
        )

    def test_metrics_extraction(self):
        for category in self.get_benchmark_categories():
            self.check_category_metrics(category)

    def check_category_metrics(self, category):
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
                expected_metrics = {
                        category: [
                            self.get_expected_metrics(category)
                        ]
                }
                self.assertEqual(
                    parsed_metrics,
                    expected_metrics
                )

    def test_has_description(self):
        clazz = self.get_benchmark_clazz()
        self.assertIsInstance(clazz.description, str)

    def test_execution_matrix(self):
        clazz = self.get_benchmark_clazz()
        benchmark = clazz()
        exec_matrix = benchmark.execution_matrix()
        exec_matrix = list(exec_matrix)
        self.assertIsInstance(exec_matrix, list)
        run_keys = set(['category', 'command', 'metas'])
        for runs in exec_matrix:
            self.assertIsInstance(runs, dict)
            self.assertTrue('category' in runs)
            self.assertIsInstance(runs['category'], str)
            self.assertTrue(runs['category'])
            self.assertTrue('command' in runs)
            self.assertIsInstance(runs['command'], list)
            self.assertTrue(runs['command'])
            for arg in runs['command']:
                self.assertIsInstance(arg, str)
            keys = set(runs.keys())
            self.assertTrue(keys.issubset(run_keys))

    def test_metrics_extractors(self):
        clazz = self.get_benchmark_clazz()
        benchmark = clazz()
        all_extractors = benchmark.metrics_extractors()
        self.assertIsInstance(all_extractors, dict)
        for name, extractors in all_extractors.items():
            self.assertIsInstance(name, str)
            self.assertTrue(name)
            if not isinstance(extractors, list):
                extractors = [extractors]
            for extractor in extractors:
                self.assertIsInstance(extractor, MetricsExtractor)
