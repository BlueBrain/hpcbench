from collections import namedtuple
import logging
import os
import os.path as osp
import re
import tempfile
import unittest

import yaml

from hpcbench.campaign import default_campaign, pip_installer_url
from hpcbench.cli import bensh
from hpcbench.driver import CampaignDriver
from hpcbench.driver.executor import ExecutionDriver, Command
from hpcbench.driver.campaign import HostDriver, BenchmarkTagDriver
from hpcbench.driver.benchmark import (
    BenchmarkDriver,
    BenchmarkCategoryDriver,
    FixedAttempts,
)
from hpcbench.driver.base import ConstraintTag
from hpcbench.toolbox.contextlib_ext import modified_environ

from . import FakeBenchmark


LOGGER = logging.getLogger()


class TestVersion(unittest.TestCase):
    def test_pip_version(self):
        self.assertEqual(pip_installer_url('1.2.3'), 'hpcbench==1.2.3')
        self.assertEqual(
            pip_installer_url('0.1.dev'),
            'git+http://github.com/BlueBrain/hpcbench@master#egg=hpcbench',
        )
        self.assertEqual(
            pip_installer_url('0.1.dev64+gff343d5.d20170803'),
            'git+http://github.com/BlueBrain/hpcbench@master#egg=hpcbench',
        )
        self.assertEqual(
            pip_installer_url('0.1.dev64+gff343d5'),
            'git+http://github.com/BlueBrain/hpcbench@master#egg=hpcbench',
        )
        self.assertEqual(
            pip_installer_url('0.1.dev'),
            'git+http://github.com/BlueBrain/hpcbench@master#egg=hpcbench',
        )


class TestCampaign(unittest.TestCase):
    @property
    def new_config(self):
        config = default_campaign(frozen=False)
        config['network']['tags'] = dict(
            by_node=dict(nodes=['node1', 'node2']),
            by_regex=dict(match='.*'),
            by_nodeset=dict(nodes='node[1-2]'),
        )
        return config

    def test_tags_re_conversion(self):
        RE_TYPE = type(re.compile('foo'))
        config = default_campaign(self.new_config)
        self.assertIsInstance(
            config['network']['tags']['by_regex'][0]['match'], RE_TYPE
        )

    def test_nodeset(self):
        config = default_campaign(self.new_config)
        self.assertEqual(
            config['network']['tags']['by_nodeset'][0]['nodes'], ['node1', 'node2']
        )

    def test_excluded_nodes(self):
        config = self.new_config
        config.network.nodes.extend(['node1'])
        config = default_campaign(config, exclude_nodes="node[2-3]")
        self.assertIn('node1', config.network.nodes)
        self.assertNotIn('node2', config.network.nodes)

    def test_constraint_tag(self):
        config = default_campaign(frozen=False)
        constraint = dict(constraint="skylake")
        config.network.tags['foo'] = constraint
        config = default_campaign(config)
        self.assertEqual(config.network.tags.foo, [constraint])

    def test_network_nodes_with_constraint_tag(self):
        config = default_campaign(frozen=False)
        config.network.tags['foo'] = [dict(constraint="skylake")]
        skylake = ConstraintTag('foo', 'skylake')
        driver = CampaignDriver(campaign=config)
        self.assertEqual(skylake, driver.network.nodes('foo'))
        with modified_environ(SLURM_JOB_NODELIST="foo[0-1]"):
            self.assertEqual(['foo0', 'foo1'], driver.network.nodes('foo'))

    def test_constraint_tag_is_a_string(self):
        for invalid_constraint in [["skylake"], dict(sky='lake')]:
            config = default_campaign(frozen=False)
            config.network.tags['foo'] = dict(constraint=invalid_constraint)
            with self.assertRaises(Exception) as exc:
                config = default_campaign(config)
            self.assertTrue(
                str(exc.exception).startswith(
                    "Constraint tag 'foo' may be a string, not: "
                )
            )

    def test_cannot_mix_constraint_and_node_tags(self):
        config = self.new_config
        config.network.tags['Cons'] = dict(constraint="skylake")
        config.network.tags['D'] = dict(tags=['by_node', 'Cons'])
        with self.assertRaises(Exception) as exc:
            config = default_campaign(config)
        self.assertEqual(str(exc.exception), "Tag 'D': cannot combine constraint tags")

    def test_tags_tag_as_string(self):
        config = self.new_config
        config.network.tags['A'] = dict(tags='by_node')
        filled_config = default_campaign(config)
        self.assertEqual(filled_config.network.tags.A, [dict(nodes=['node1', 'node2'])])

    def test_tag_multiple_decl(self):
        config = self.new_config
        config.network.tags['A'] = dict(tags='by_node', nodes=['node1'])
        with self.assertRaises(Exception) as exc:
            default_campaign(config)
        self.assertTrue(
            str(exc.exception).startswith(
                "Tag 'A' is based on more than one criterion: "
            )
        )

    def test_cyclic_tags(self):
        config = self.new_config
        config['network']['tags']['A'] = dict(tags=['B'])
        config['network']['tags']['B'] = dict(tags=['A'])
        with self.assertRaises(Exception):
            default_campaign(config)

    def test_recursive_tag_missing(self):
        config = self.new_config
        config['network']['tags']['atag'] = dict(tags=['dontexist'])
        with self.assertRaises(Exception):
            default_campaign(config)

    def test_tags_invalid_mode(self):
        config = self.new_config
        config['network']['tags']['invalid'] = dict(unknown='')
        with self.assertRaises(Exception):
            default_campaign(config)

    def test_envvars_expansion(self):
        with self.assertRaises(KeyError):
            config = self.new_config
            config['output_dir'] = "$OUTPUT_DIR"
            default_campaign(config)

        os.environ['OUTPUT_DIR'] = 'output-dir'
        try:
            config = self.new_config
            config['output_dir'] = "$OUTPUT_DIR"
            config = default_campaign(config)
            self.assertEqual(config['output_dir'], 'output-dir')
        finally:
            os.environ.pop('OUTPUT_DIR')


class TestBenchmark(unittest.TestCase):
    def _top(self, exec_prefix):
        return ExecutionDriver(
            FixedAttempts(
                BenchmarkCategoryDriver(
                    BenchmarkDriver(
                        BenchmarkTagDriver(
                            HostDriver(CampaignDriver(default_campaign()), 'n1')
                        ),
                        namedtuple('benchmark', ['name'])(name='benchmark'),
                        FakeBenchmark.DEFAULT_BENCHMARK_NAME,
                        dict(exec_prefix=exec_prefix),
                    ),
                    'category',
                ),
                Command(execution=dict(command=['ls', '-la'])),
            )
        )

    def test_exec_prefix_as_list(self):
        ed = self._top(['numactl', '--all'])
        self.assertEqual(['numactl', '--all', 'ls', '-la'], ed.command)

    def test_exec_prefix_as_string(self):
        ed = self._top('numactl --all')
        self.assertEqual(['numactl', '--all', 'ls', '-la'], ed.command)


class TestGenerator(unittest.TestCase):
    def setUp(self):
        fd, self.output_file = tempfile.mkstemp(prefix='hpcbench-ut', suffix='.yaml')
        os.close(fd)
        os.remove(self.output_file)

    def tearDown(self):
        if osp.exists(self.output_file):
            os.remove(self.output_file)

    def test_generator(self):
        bensh.main(argv=['-g', self.output_file])
        self.assertTrue(osp.isfile(self.output_file))
        with open(self.output_file) as istr:
            template = yaml.safe_load(istr)
        self.assertIsInstance(template, dict)
