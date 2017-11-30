"""ben-nett

Usage:
  ben-nett [-v | -vv ] CAMPAIGN_FILE
  ben-nett (-h | --help)
  ben-nett --version

Options:
  -h --help  Show this screen
  --version  Show version
  -v -vv     Increase program verbosity
"""

from hpcbench.net import BeNet
from . import cli_common


def main(argv=None):
    """ben-nett entry point"""
    arguments = cli_common(__doc__, argv=argv)
    benet = BeNet(arguments['CAMPAIGN_FILE'])
    benet.run()
    if argv is not None:
        return benet
