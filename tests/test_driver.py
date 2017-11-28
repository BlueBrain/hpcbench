from collections import namedtuple
from functools import reduce
import json
import logging
import os
import os.path as osp
import shutil
import tempfile
import unittest

from cached_property import cached_property
import yaml

from hpcbench.api import Benchmark
from hpcbench.cli import (
    bendoc,
    benelastic,
    benplot,
    benumb,
)
from hpcbench.driver import (
    BenchmarkCategoryDriver,
    BenchmarkDriver,
    BenchmarkTagDriver,
    CampaignDriver,
    FixedAttempts,
    HostDriver,
    SlurmExecutionDriver,
)
from hpcbench.toolbox.contextlib_ext import (
    capture_stdout,
)
from . import DriverTestCase, FakeBenchmark
from . benchmark.benchmark import AbstractBenchmarkTest


LOGGER = logging.getLogger('hpcbench')


class TestDriver(DriverTestCase, unittest.TestCase):
    def test_get_unknown_benchmark_class(self):
        with self.assertRaises(NameError) as exc:
            Benchmark.get_subclass('unkn0wnb3nchm4rk')
        self.assertEqual(
            str(exc.exception),
            "Not a valid Benchmark class: unkn0wnb3nchm4rk"
        )

    def test_run_01(self):
        self.assertTrue(osp.isdir(self.CAMPAIGN_PATH))
        # simply ensure metrics have been generated
        aggregated_metrics_f = osp.join(
            TestDriver.CAMPAIGN_PATH,
            TestDriver.driver.node,
            '*',
            'test01',
            'main',
            'metrics.json'
        )
        self.assertTrue(
            osp.isfile(aggregated_metrics_f),
            "Not file: " + aggregated_metrics_f
        )
        with open(aggregated_metrics_f) as istr:
            aggregated_metrics = json.load(istr)
        self.assertTrue(len(aggregated_metrics), 3)

    def test_02_number(self):
        self.assertIsNotNone(TestDriver.CAMPAIGN_PATH)
        benumb.main(TestDriver.CAMPAIGN_PATH)
        # FIXME add checks

    def test_03_plot(self):
        self.test_02_number()
        self.assertIsNotNone(TestDriver.CAMPAIGN_PATH)
        benplot.main(TestDriver.CAMPAIGN_PATH)
        plot_file_f = osp.join(
            TestDriver.CAMPAIGN_PATH,
            TestDriver.driver.node,
            '*',
            'test01',
            'main',
            '7b9d424b038a9c89bf48c0b183864e61b1'
            '724a109b8f2d9d756b594f8f29b861.png'
        )
        self.assertTrue(osp.isfile(plot_file_f))

    def test_04_report(self):
        self.assertIsNotNone(TestDriver.CAMPAIGN_PATH)
        with capture_stdout() as stdout:
            bendoc.main(TestDriver.CAMPAIGN_PATH)
        content = stdout.getvalue()
        self.assertTrue(content)

    @unittest.skipIf('UT_SKIP_ELASTICSEARCH' in os.environ,
                     'manually disabled from environment')
    def test_05_es_dump(self):
        # Push documents to Elasticsearch
        argv = [TestDriver.CAMPAIGN_PATH]
        if 'UT_ELASTICSEARCH_HOST' in os.environ:
            argv += ['--es', os.environ['UT_ELASTICSEARCH_HOST']]
        exporter = benelastic.main(TestDriver.CAMPAIGN_PATH)
        # Ensure they are searchable
        exporter.index_client.refresh(exporter.index_name)
        # Expect 3 documents in the index dedicated to the campaign
        resp = exporter.es_client.count(exporter.index_name)
        self.assertEqual(resp['count'], 3)
        if 'UT_KEEP_ELASTICSEARCH_INDEX' not in os.environ:
            # Cleanup
            exporter.remove_index()


class TestFakeBenchmark(AbstractBenchmarkTest, unittest.TestCase):
    def get_benchmark_clazz(self):
        return FakeBenchmark

    def get_expected_metrics(self, category):
        return dict(
            performance=10.0,
            standard_error=1.0
        )

    def get_benchmark_categories(self):
        return ['main']


class TestHostDriver(unittest.TestCase):
    CAMPAIGN = dict(
        network=dict(
            nodes=[
                'node{0:02}'.format(id_)
                for id_ in range(1, 11)
            ],
            tags=reduce(
                lambda x, y: dict(x, **y),
                (
                    dict(
                        (
                            'n{0:02}'.format(id_),
                            dict(nodes=['node{0:02}'.format(id_)])
                        )
                        for id_ in range(1, 11)

                    ),
                    dict(
                        group_nodes=[
                            dict(
                                nodes=[
                                    "node01",
                                    "node02",
                                ],
                            ),
                            dict(
                                nodes=[
                                    "node03",
                                ],
                            ),
                        ],
                        group_match=dict(
                            match="node1.*"
                        ),
                    )
                )
            )
        )
    )

    @classmethod
    def setUpClass(cls):
        cls.TEST_DIR = tempfile.mkdtemp(prefix='hpcbench-ut')
        cls.CAMPAIGN_FILE = osp.join(cls.TEST_DIR, 'campaign.yaml')
        with open(cls.CAMPAIGN_FILE, 'w') as ostr:
            yaml.dump(cls.CAMPAIGN, ostr, default_flow_style=False)
        cls.DRIVER = CampaignDriver(campaign_file=cls.CAMPAIGN_FILE)

    def host_driver(self, node):
        return HostDriver(
            CampaignDriver(
                campaign_file=TestHostDriver.CAMPAIGN_FILE,
                node=node
            ),
            node
        )

    def test_host_driver_children(self):
        self.assertEqual(
            self.host_driver('node01').children,
            {'*', 'n01', 'group_nodes'}
        )
        self.assertEqual(
            self.host_driver('node10').children,
            {'*', 'n10', 'group_match'}
        )

    def slurm(self, node='node01', tag='group_nodes', srun_nodes=1):
        execution = dict(
            command=['ls', '-la']
        )
        campaign_file = TestHostDriver.CAMPAIGN_FILE
        if srun_nodes is not None:
            execution.update(srun_nodes=srun_nodes)
        return SlurmExecutionDriver(
           FixedAttempts(
                BenchmarkCategoryDriver(
                    BenchmarkDriver(
                        BenchmarkTagDriver(
                            HostDriver(
                                CampaignDriver(
                                    campaign_file=campaign_file,
                                    node=node
                                ),
                                node
                            ),
                            tag
                        ),
                        namedtuple('benchmark', ['name'])(name='benchmark'),
                        dict(),
                    ),
                    'category'
                ),
                execution
            )
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.TEST_DIR)

    @cached_property
    def network(self):
        return TestHostDriver.DRIVER.network

    def test_srun_nodes_method(self):
        self.assertEqual(
            self.slurm(node='node03', srun_nodes=0).srun_nodes,
            ['node01', 'node02', 'node03']
        )
        self.assertEqual(
            self.slurm(node='node01', srun_nodes=1).srun_nodes,
            ['node01']
        )
        self.assertEqual(
            self.slurm(node='node02', srun_nodes=1).srun_nodes,
            ['node02']
        )
        self.assertEqual(
            self.slurm(node='node01', srun_nodes=2).srun_nodes,
            ['node01', 'node02']
        )
        self.assertEqual(
            self.slurm(node='node02', srun_nodes=2).srun_nodes,
            ['node02', 'node03']
        )
        self.assertEqual(
            self.slurm(node='node03', srun_nodes=2).srun_nodes,
            ['node03', 'node01']
        )
        self.assertEqual(
            self.slurm(node='node03', srun_nodes='group_match').srun_nodes,
            ['node10']
        )
        self.assertEqual(
            self.slurm(srun_nodes='*').srun_nodes,
            [
                'node{0:02}'.format(id_)
                for id_ in range(1, 11)
            ]
        )

    def test_srun_nodes_method_errors(self):
        negative_srun_nodes = self.slurm(node='node03', srun_nodes=-1)
        with self.assertRaises(AssertionError):
            self.assertIsNotNone(negative_srun_nodes.srun_nodes)

        host_not_in_tag = self.slurm(node='node04')
        with self.assertRaises(ValueError):
            self.assertIsNotNone(host_not_in_tag.srun_nodes)

        unknown_tag = self.slurm(srun_nodes='unknown_tag')
        with self.assertRaises(ValueError):
            self.assertIsNotNone(unknown_tag.srun_nodes)

        too_many_nodes = self.slurm(srun_nodes=4)
        with self.assertRaises(AssertionError):
            self.assertIsNotNone(too_many_nodes.srun_nodes)

    def test_nodes_method(self):
        self.assertEqual(
            self.network.nodes('group_nodes'),
            [
                'node01',
                'node02',
                'node03'
            ]
        )
        self.assertEqual(
            self.network.nodes('group_match'),
            [
                'node10',
            ]
        )
        self.assertEqual(
            self.network.nodes('n01'),
            [
                'node01',
            ]
        )
        self.assertEqual(
            self.network.nodes('*'),
            [
                'node{0:02}'.format(id_)
                for id_ in range(1, 11)
            ]
        )
        self.assertEqual(self.network.nodes('unknown_group'), [])
