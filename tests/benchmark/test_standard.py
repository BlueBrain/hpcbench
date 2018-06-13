import copy
import inspect
import os.path as osp
import unittest

import yaml

from hpcbench.benchmark.standard import MetaFunctions, StdBenchmark
from .benchmark import AbstractBenchmarkTest


class TestMetaFunctions(unittest.TestCase):
    def test_invalid_func_name(self):
        with self.assertRaises(Exception):
            MetaFunctions.eval('_class', [], {})

    def test_linspace(self):
        self.assertEqual(
            MetaFunctions.eval('linspace', [0.0, 10, 5], {}), [0.0, 2.5, 5, 7.5, 10.0]
        )
        self.assertEqual(
            MetaFunctions.eval('linspace', [0.0, 10, 2], dict(endpoint=False)),
            [0.0, 5.0],
        )

    def test_range(self):
        self.assertEqual(MetaFunctions.eval('range', [0, 5], {}), [0, 1, 2, 3, 4])

    def test_correlate(self):
        series = [['arange', 0, 5, 1], ['arange', 0.0, 10.0, 2]]
        resp = list(MetaFunctions._func_correlate(*series))
        self.assertEqual(resp, [(0, 0), (1, 2), (2, 4), (3, 6), (4, 8)])

        resp = list(MetaFunctions._func_correlate(*series, explore=[[0, 1]]))
        self.assertEqual(
            resp,
            [(0, 0), (1, 2), (2, 4), (3, 6), (4, 8), (0, 2), (1, 4), (2, 6), (3, 8)],
        )

        resp = list(MetaFunctions._func_correlate(*series, explore=[[0, -1]]))
        self.assertEqual(
            resp,
            [(0, 0), (1, 2), (2, 4), (3, 6), (4, 8), (1, 0), (2, 2), (3, 4), (4, 6)],
        )

        resp = list(MetaFunctions._func_correlate(*series, explore=[[1, 0]]))
        self.assertEqual(
            resp,
            [(0, 0), (1, 2), (2, 4), (3, 6), (4, 8), (1, 0), (2, 2), (3, 4), (4, 6)],
        )

        resp = list(MetaFunctions._func_correlate(*series, explore=[[-1, 0]]))
        self.assertEqual(
            resp,
            [(0, 0), (1, 2), (2, 4), (3, 6), (4, 8), (0, 2), (1, 4), (2, 6), (3, 8)],
        )

        resp = list(
            MetaFunctions._func_correlate(
                ['arange', 0, 2, 1],
                ['arange', 2, 4, 1],
                ['arange', 4, 6, 1],
                explore=[[1, 0, 0]],
            )
        )
        self.assertEqual(resp, [(0, 2, 4), (1, 3, 5), (1, 2, 4)])


class TestStandard(AbstractBenchmarkTest, unittest.TestCase):
    def get_benchmark_clazz(self):
        return StdBenchmark

    def get_benchmark_categories(self):
        return [StdBenchmark.DEFAULT_CATEGORY]

    def get_expected_metrics(self, category):
        return [dict(simulation_time=79.3729), dict(simulation_time=760.517)]

    def execution_metrics_set(self, category):
        return [{}, dict(branch='branch42', compiler='icc')]

    @property
    def attributes(self):
        category = StdBenchmark.DEFAULT_CATEGORY
        pyfile = inspect.getfile(self.__class__)
        data = osp.splitext(osp.basename(pyfile))[0] + '.' + category + '.yaml'
        test_dir = osp.dirname(pyfile)
        with open(osp.join(test_dir, data)) as istr:
            return yaml.load(istr)

    @property
    def expected_execution_matrix(self):
        # noqa: ignore=E501
        correlated_base = [
            {
                'category': 'standard',
                'command': [
                    ['spack install lengine@master +syn2 %gcc'],
                    ['spack load lengine@master +syn2 %gcc'],
                    ['bench_brunel', '--partition', '1', '1', '1', '1.syn2'],
                ],
                'metas': {
                    'branch': 'master',
                    'compiler': 'gcc',
                    'file': '1.syn2',
                    'partition': 1,
                },
                'shell': True,
            },
            {
                'category': 'standard',
                'command': [
                    ['spack install lengine@branch42 +syn2 %gcc'],
                    ['spack load lengine@branch42 +syn2 %gcc'],
                    ['bench_brunel', '--partition', '1', '1', '1', '1.syn2'],
                ],
                'metas': {
                    'branch': 'branch42',
                    'compiler': 'gcc',
                    'file': '1.syn2',
                    'partition': 1,
                },
                'shell': True,
            },
            {
                'category': 'standard',
                'command': [
                    ['spack install lengine@master +syn2 %icc'],
                    ['spack load lengine@master +syn2 %icc'],
                    ['bench_brunel', '--partition', '1', '1', '1', '1.syn2'],
                ],
                'metas': {
                    'branch': 'master',
                    'compiler': 'gcc',
                    'file': '1.syn2',
                    'partition': 1,
                },
                'shell': True,
            },
            {
                'category': 'standard',
                'command': [
                    ['spack install lengine@master +syn2 %gcc'],
                    ['spack load lengine@master +syn2 %gcc'],
                    ['bench_brunel', '--partition', '2', '1', '1', '1.syn2'],
                ],
                'metas': {
                    'branch': 'master',
                    'compiler': 'gcc',
                    'file': '1.syn2',
                    'partition': 2,
                },
                'shell': True,
            },
            {
                'category': 'standard',
                'command': [
                    ['spack install lengine@branch42 +syn2 %gcc'],
                    ['spack load lengine@branch42 +syn2 %gcc'],
                    ['bench_brunel', '--partition', '2', '1', '1', '1.syn2'],
                ],
                'metas': {
                    'branch': 'branch42',
                    'compiler': 'gcc',
                    'file': '1.syn2',
                    'partition': 2,
                },
                'shell': True,
            },
            {
                'category': 'standard',
                'command': [
                    ['spack install lengine@master +syn2 %icc'],
                    ['spack load lengine@master +syn2 %icc'],
                    ['bench_brunel', '--partition', '2', '1', '1', '1.syn2'],
                ],
                'metas': {
                    'branch': 'master',
                    'compiler': 'gcc',
                    'file': '1.syn2',
                    'partition': 2,
                },
                'shell': True,
            },
        ]
        correlated = []
        for i in range(6):
            processes = 32 / pow(2, i)
            threads = pow(2, i)
            runs = copy.deepcopy(correlated_base)
            for run in runs:
                run['metas']['processes'] = processes
                run['metas']['threads'] = threads
                correlated.append(run)

        partition3 = [
            {
                'category': 'standard',
                'command': [
                    ['spack install lengine@master +syn2 %gcc'],
                    ['spack load lengine@master +syn2 %gcc'],
                    ['bench_brunel', '--partition', '3', '1', '1', '3.syn2'],
                ],
                'metas': {
                    'branch': 'master',
                    'compiler': 'gcc',
                    'file': '3.syn2',
                    'partition': 3,
                },
                'shell': True,
            },
            {
                'category': 'standard',
                'command': [
                    ['spack install lengine@branch42 +syn2 %gcc'],
                    ['spack load lengine@branch42 +syn2 %gcc'],
                    ['bench_brunel', '--partition', '3', '1', '1', '3.syn2'],
                ],
                'metas': {
                    'branch': 'branch42',
                    'compiler': 'gcc',
                    'file': '3.syn2',
                    'partition': 3,
                },
                'shell': True,
            },
            {
                'category': 'standard',
                'command': [
                    ['spack install lengine@master +syn2 %icc'],
                    ['spack load lengine@master +syn2 %icc'],
                    ['bench_brunel', '--partition', '3', '1', '1', '3.syn2'],
                ],
                'metas': {
                    'branch': 'master',
                    'compiler': 'gcc',
                    'file': '3.syn2',
                    'partition': 3,
                },
                'shell': True,
            },
        ]

        expected = correlated + partition3
        return expected
