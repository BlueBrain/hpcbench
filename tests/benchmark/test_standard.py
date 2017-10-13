import inspect
import os.path as osp
import unittest

import yaml

from hpcbench.benchmark.standard import StdBenchmark
from . benchmark import AbstractBenchmarkTest


class TestStandard(AbstractBenchmarkTest, unittest.TestCase):
    def get_benchmark_clazz(self):
        return StdBenchmark

    def get_benchmark_categories(self):
        return [
            StdBenchmark.DEFAULT_CATEGORY,
        ]

    def get_expected_metrics(self, category):
        return [
            dict(simulation_time=79.3729),
            dict(simulation_time=760.517),
        ]

    def execution_metrics_set(self, category):
        return [
            {},
            dict(branch='branch42', compiler='icc')
        ]

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
        return [
            {'category': 'standard',
             'command': [
                 ['spack install lengine@master +syn2 %gcc'],
                 ['spack load lengine@master +syn2 %gcc'],
                 ['bench_brunel', '--partition', '1', '1', '1', '1.syn2']
             ],
             'metas': {'branch': 'master',
                       'compiler': 'gcc',
                       'file': '1.syn2',
                       'partition': 1},
             'shell': True},
            {'category': 'standard',
             'command': [
                ['spack install lengine@branch42 +syn2 %gcc'],
                ['spack load lengine@branch42 +syn2 %gcc'],
                ['bench_brunel', '--partition', '1', '1', '1', '1.syn2']
             ],
             'metas': {'branch': 'branch42',
                       'compiler': 'gcc',
                       'file': '1.syn2',
                       'partition': 1},
             'shell': True},
            {'category': 'standard',
             'command': [
                 ['spack install lengine@master +syn2 %icc'],
                 ['spack load lengine@master +syn2 %icc'],
                 ['bench_brunel', '--partition', '1', '1', '1', '1.syn2']
             ],
             'metas': {'branch': 'master',
                       'compiler': 'gcc',
                       'file': '1.syn2',
                       'partition': 1},
             'shell': True},
            {'category': 'standard',
             'command': [
                 ['spack install lengine@master +syn2 %gcc'],
                 ['spack load lengine@master +syn2 %gcc'],
                 ['bench_brunel', '--partition', '2', '1', '1', '1.syn2']
             ],
             'metas': {'branch': 'master',
                       'compiler': 'gcc',
                       'file': '1.syn2',
                       'partition': 2},
             'shell': True},
            {'category': 'standard',
             'command': [
                 ['spack install lengine@branch42 +syn2 %gcc'],
                 ['spack load lengine@branch42 +syn2 %gcc'],
                 ['bench_brunel', '--partition', '2', '1', '1', '1.syn2']
             ],
             'metas': {'branch': 'branch42',
                       'compiler': 'gcc',
                       'file': '1.syn2',
                       'partition': 2},
             'shell': True},
            {'category': 'standard',
             'command': [
                 ['spack install lengine@master +syn2 %icc'],
                 ['spack load lengine@master +syn2 %icc'],
                 ['bench_brunel', '--partition', '2', '1', '1', '1.syn2']
             ],
             'metas': {'branch': 'master',
                       'compiler': 'gcc',
                       'file': '1.syn2',
                       'partition': 2},
             'shell': True},
            {'category': 'standard',
             'command': [
                 ['spack install lengine@master +syn2 %gcc'],
                 ['spack load lengine@master +syn2 %gcc'],
                 ['bench_brunel', '--partition', '3', '1', '1', '3.syn2']
             ],
             'metas': {'branch': 'master',
                       'compiler': 'gcc',
                       'file': '3.syn2',
                       'partition': 3},
             'shell': True},
            {'category': 'standard',
             'command': [
                 ['spack install lengine@branch42 +syn2 %gcc'],
                 ['spack load lengine@branch42 +syn2 %gcc'],
                 ['bench_brunel', '--partition', '3', '1', '1', '3.syn2']
             ],
             'metas': {'branch': 'branch42',
                       'compiler': 'gcc',
                       'file': '3.syn2',
                       'partition': 3},
             'shell': True},
            {'category': 'standard',
             'command': [
                 ['spack install lengine@master +syn2 %icc'],
                 ['spack load lengine@master +syn2 %icc'],
                 ['bench_brunel', '--partition', '3', '1', '1', '3.syn2']
             ],
             'metas': {'branch': 'master',
                       'compiler': 'gcc',
                       'file': '3.syn2',
                       'partition': 3},
             'shell': True}
        ]
