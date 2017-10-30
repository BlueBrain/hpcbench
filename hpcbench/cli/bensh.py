"""ben-sh - Execute a campaign

Usage:
  ben-sh [-v | -vv] [-n HOST] [-g] CAMPAIGN_FILE
  ben-sh (-h | --help)
  ben-sh --version

Options:
  -n HOST    Specify node name. Default is localhost
  -h --help  Show this screen
  -g         Generate a default YAML campaign file
  --version  Show version
  -v -vv     Increase program verbosity
"""

import os.path as osp

from hpcbench.campaign import Generator
from hpcbench.driver import CampaignDriver
from . import cli_common


def main(argv=None):
    """ben-sh entry point"""
    arguments = cli_common(__doc__, argv=argv)
    campaign_file = arguments['CAMPAIGN_FILE']
    if arguments['-g']:
        if osp.exists(campaign_file):
            raise Exception('Campaign file already exists')
        with open(campaign_file, 'w') as ostr:
            Generator().write(ostr)
    else:
        node = arguments.get('-n')
        driver = CampaignDriver(campaign_file=campaign_file,
                                node=node)
        driver()
        if argv is not None:
            return driver
