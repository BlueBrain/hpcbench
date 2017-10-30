from collections import namedtuple
import logging
import os
import os.path as osp
import re
import tempfile
import unittest

import yaml

from hpcbench.campaign import (
    fill_default_campaign_values,
    pip_installer_url,
)
from hpcbench.cli import bensh
from hpcbench.driver import (
    BenchmarkCategoryDriver,
    BenchmarkDriver,
    ExecutionDriver,
    FixedAttempts,
    Top,
)
from hpcbench.toolbox.collections_ext import nameddict


LOGGER = logging.getLogger()


class TestVersion(unittest.TestCase):
    def test_pip_version(self):
        self.assertEqual(pip_installer_url('1.2.3'), 'hpcbench==1.2.3')
        self.assertEqual(
            pip_installer_url('0.1.dev'),
            'git+http://github.com/tristan0x/hpcbench@master#egg=hpcbench'
        )
        self.assertEqual(
            pip_installer_url('0.1.dev64+gff343d5.d20170803'),
            'git+http://github.com/tristan0x/hpcbench@master#egg=hpcbench'
        )
        self.assertEqual(
            pip_installer_url('0.1.dev64+gff343d5'),
            'git+http://github.com/tristan0x/hpcbench@master#egg=hpcbench'
        )
        self.assertEqual(
            pip_installer_url('0.1.dev'),
            'git+http://github.com/tristan0x/hpcbench@master#egg=hpcbench'
        )


class TestCampaign(unittest.TestCase):
    @property
    def new_config(self):
        config = fill_default_campaign_values(nameddict())
        config['network']['tags'] = dict(
            by_node=dict(
                nodes=['node1', 'node2']
            ),
            by_regex=dict(
                match='.*'
            ),
            by_nodeset=dict(
                nodes='node[1-2]'
            )
        )
        return config

    def test_tags_re_conversion(self):
        RE_TYPE = type(re.compile('foo'))
        config = fill_default_campaign_values(self.new_config)
        self.assertIsInstance(
            config['network']['tags']['by_regex'][0]['match'],
            RE_TYPE
        )

    def test_nodeset(self):
        config = fill_default_campaign_values(self.new_config)
        self.assertEqual(
            config['network']['tags']['by_nodeset'][0]['nodes'],
            [
                'node1',
                'node2',
            ]
        )

    def test_tags_invalid_mode(self):
        config = self.new_config
        config['network']['tags']['invalid'] = dict(
            unknown=''
        )
        with self.assertRaises(Exception):
            fill_default_campaign_values(config)

    def test_envvars_expansion(self):
        with self.assertRaises(KeyError):
            config = self.new_config
            config['output_dir'] = "$OUTPUT_DIR"
            fill_default_campaign_values(config)

        os.environ['OUTPUT_DIR'] = 'output-dir'
        try:
            config = self.new_config
            config['output_dir'] = "$OUTPUT_DIR"
            config = fill_default_campaign_values(config)
            self.assertEqual(config['output_dir'], 'output-dir')
        finally:
            os.environ.pop('OUTPUT_DIR')


class TestBenchmark(unittest.TestCase):
    def _top(self, exec_prefix):
        return ExecutionDriver(
            FixedAttempts(
                BenchmarkCategoryDriver(
                    BenchmarkDriver(
                        Top(logger=LOGGER),
                        namedtuple('benchmark', ['name'])(name='benchmark'),
                        dict(exec_prefix=exec_prefix),
                    ),
                    'category'
                ),
                dict(command=['ls', '-la'])
            )
        )

    def test_exec_prefix_as_list(self):
        ed = self._top(['numactl', '--all'])
        self.assertEqual(
            ['numactl', '--all', 'ls', '-la'],
            ed.command
        )

    def test_exec_prefix_as_string(self):
        ed = self._top('numactl --all')
        self.assertEqual(
            ['numactl', '--all', 'ls', '-la'],
            ed.command
        )


class TestGenerator(unittest.TestCase):
    def setUp(self):
        fd, self.output_file = tempfile.mkstemp(prefix='hpcbench-ut',
                                                suffix='.yaml')
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
