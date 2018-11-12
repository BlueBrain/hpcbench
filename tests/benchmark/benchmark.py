from abc import ABCMeta, abstractmethod
from collections import Mapping, namedtuple
import inspect
import itertools
import logging
import os
import os.path as osp
import shutil

from cached_property import cached_property
from six import assertCountEqual, string_types, with_metaclass
import yaml

from hpcbench.api import Benchmark, ExecutionContext, MetricsExtractor
from hpcbench.campaign import YAML_REPORT_FILE
from hpcbench.driver.base import Top
from hpcbench.driver.benchmark import (
    MetricsDriver,
    BenchmarkCategoryDriver,
    BenchmarkDriver,
)
from hpcbench.toolbox.collections_ext import dict_merge
from hpcbench.toolbox.contextlib_ext import mkdtemp, pushd
from .. import FakeBenchmark, FakeCluster

LOGGER = logging.getLogger(__name__)


class AbstractBenchmarkTest(with_metaclass(ABCMeta, object)):
    exposed_benchmark = True

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

    @property
    def attributes(self):
        """
        :return: attributes to merge on the Benchmark instance
        :rtype: dictionary
        """
        return {}

    @property
    def check_executable_availability(self):
        """
        :return: True if executables used in execution matrix should
        be checked, False otherwise.
        """
        return False

    @cached_property
    def logger(self):
        return LOGGER.getChild(self.get_benchmark_clazz().name)

    def create_sample_run(self, category):
        pyfile = inspect.getfile(self.__class__)
        prefix = osp.splitext(osp.basename(pyfile))[0] + '.' + category + '.'
        test_dir = osp.dirname(pyfile)
        for file_ in os.listdir(test_dir):
            if file_.startswith(prefix):
                src_file = osp.join(test_dir, file_)
                dest = file_[len(prefix) :]
                if osp.isfile(src_file):
                    self.logger.info('using file: %s', src_file)
                    shutil.copy(src_file, dest)

    def test_executable_availability(self):
        if not self.check_executable_availability:
            return
        for execution in self.execution_matrix:
            command = execution['command']
            executable = command[0]
            self.assertTrue(osp.isfile(executable), executable + ' is a file')
            self.assertTrue(
                os.access(executable, os.X_OK), executable + ' is executable'
            )

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
        self.logger.info('testing metrics of category %s', category)
        self.maxDiff = None
        with mkdtemp() as top_dir, pushd(top_dir):
            with open(YAML_REPORT_FILE, 'w') as ostr:
                yaml.dump(dict(children=['sample-run'], category=category), ostr)
            with pushd('sample-run'):
                self.create_sample_run(category)
                clazz = self.get_benchmark_clazz()
                benchmark = clazz()
                dict_merge(benchmark.attributes, self.attributes)
                expected_metrics = self.get_expected_metrics(category)
                if not isinstance(expected_metrics, list):
                    expected_metrics = itertools.repeat(expected_metrics)
                else:
                    expected_metrics = iter(expected_metrics)
                for metas in self.execution_metrics_set(category):
                    with open(YAML_REPORT_FILE, 'w') as ostr:
                        yaml.dump(
                            dict(category=category, metas=metas, executor='local'), ostr
                        )

                    md = MetricsDriver(
                        BenchmarkCategoryDriver(
                            BenchmarkDriver(
                                Top(
                                    logger=LOGGER, root=namedtuple('root', ['network'])
                                ),
                                benchmark,
                                'bench',
                                dict(),
                            ),
                            'test-category',
                        ),
                        benchmark,
                    )
                    report = md()
                    parsed_metrics = report['metrics'][0]['measurement']
                    self.assertEqual(parsed_metrics, next(expected_metrics))

    def test_has_description(self):
        clazz = self.get_benchmark_clazz()
        doc = clazz.__doc__
        assert doc is not None, "Missing class docstring"
        with self.assertRaises(AttributeError):
            getattr(clazz, 'description')

    def test_attr_doc(self):
        clazz = self.get_benchmark_clazz()
        benchmark = clazz()
        for attr in benchmark.attributes:
            doc = getattr(clazz, attr).__doc__
            msg = "%s: missing docstring for attribute: %s"
            msg = msg % (benchmark.name, attr)
            assert doc is not None, msg

    def execution_metrics_set(self, category):
        del category  # unused
        return [{}]

    @property
    def execution_matrix(self):
        clazz = self.get_benchmark_clazz()
        benchmark = clazz()
        dict_merge(benchmark.attributes, self.attributes)
        return list(benchmark.execution_matrix(self.exec_context))

    @property
    def exec_context(self):
        tag = '*'
        node = 'localhost'
        return ExecutionContext(
            cluster=FakeCluster(tag, [node], node),
            logger=self.logger,
            benchmark=FakeBenchmark.DEFAULT_BENCHMARK_NAME,
            node=node,
            srun_options=[],
            tag=tag,
        )

    @property
    def expected_execution_matrix(self):
        pass

    def test_execution_matrix(self):
        self.maxDiff = None
        exec_matrix = self.execution_matrix
        assert isinstance(exec_matrix, list)

        expected_exec_matrix = self.expected_execution_matrix
        if expected_exec_matrix is not None:
            assertCountEqual(self, expected_exec_matrix, exec_matrix)

        run_keys = {
            'category',
            'command',
            'environment',
            'metas',
            'shell',
            'srun_nodes',
        }
        for runs in exec_matrix:
            self.assertIsInstance(runs, dict)
            self.assertIn('category', runs)
            self.assertIsInstance(runs['category'], string_types)
            assert runs['category']
            self.assertIn('command', runs)
            self.assertIsInstance(runs['command'], list)
            assert runs['command']
            if runs.get('shell', False):
                for cmd in runs['command']:
                    self.assertIsInstance(cmd, list)
                    for arg in cmd:
                        self.assertIsInstance(arg, string_types)
            else:
                for arg in runs['command']:
                    assert isinstance(arg, str)
            keys = set(runs.keys())
            assert keys.issubset(run_keys)

    def test_metrics_extractors(self):
        clazz = self.get_benchmark_clazz()
        benchmark = clazz()
        dict_merge(benchmark.attributes, self.attributes)
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

    def assertExecutionMatrix(self, attributes, exec_matrix):
        """Helper function to test execution matrix of a benchmark
        initialized with the given attributes
        """
        clazz = self.get_benchmark_clazz()
        benchmark = clazz()
        dict_merge(benchmark.attributes, attributes)
        assertCountEqual(
            self, list(benchmark.execution_matrix(self.exec_context)), exec_matrix
        )

    def test_has_entrypoint(self):
        """Benchmark must be specified in setup.py"""
        if self.exposed_benchmark:
            expected_module = inspect.getfile(self.get_benchmark_clazz())
            expected_module = expected_module[len(os.getcwd()) + 1 :]
            expected_module = osp.splitext(expected_module)[0]
            expected_module = expected_module.replace('/', '.')
            with open('setup.py') as istr:
                in_entrypoints_decl = False
                module_found = False
                for line in istr:
                    if '[hpcbench.benchmarks]' in line:
                        in_entrypoints_decl = True
                    else:
                        if in_entrypoints_decl:
                            line = line.strip()
                            module = line.split('=', 1)[-1].strip()
                            if module == expected_module:
                                module_found = True
                message = "module '%s' is not declared" % expected_module
                self.assertTrue(module_found, msg=message)
