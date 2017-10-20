"""ben-merge

Usage:
  ben-merge [-v | -vv ] CAMPAIGN-DIR CAMPAIGN-DIR [CAMPAIGN-DIR ...]
  ben-merge (-h | --help)
  ben-merge --version

Options:
  -h --help  Show this screen
  --version  Show version
  -v -vv     Increase program verbosity
"""

from hpcbench.campaign import merge_campaigns
from . import cli_common


def main(argv=None):
    """ben-merge entry point"""
    arguments = cli_common(__doc__, argv=argv)
    merge_campaigns(*arguments['CAMPAIGN-DIR'])
