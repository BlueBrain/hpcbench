import re
import unittest

from hpcbench.campaign import (
    fill_default_campaign_values,
    pip_installer_url,
)
from hpcbench.toolbox.collections_ext import nameddict

class TestVersion(unittest.TestCase):
    def test_pip_version(self):
        self.assertTrue('github' in pip_installer_url('0.1-dev'))
        self.assertEqual(pip_installer_url('1.2.3'), 'hpcbench==1.2.3')


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
            )
        )
        return config

    def test_tags_re_conversion(self):
        RE_TYPE = type(re.compile('foo'))
        config = self.new_config
        fill_default_campaign_values(config)
        self.assertIsInstance(
            config['network']['tags']['by_regex'][0]['match'],
            RE_TYPE
        )

    def test_tags_invalid_nodes_list(self):
        config = self.new_config
        config['network']['tags']['invalid'] = dict(
            nodes='expecting list but got string'
        )
        with self.assertRaises(Exception) as exc:
            fill_default_campaign_values(config)

    def test_tags_invalid_mode(self):
        config = self.new_config
        config['network']['tags']['invalid'] = dict(
            unknown=''
        )
        with self.assertRaises(Exception) as exc:
            fill_default_campaign_values(config)
