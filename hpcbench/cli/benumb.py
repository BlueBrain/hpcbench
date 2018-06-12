"""ben-umb - Rebuild metrics of an existing campaign

Usage:
  ben-umb [-v | -vv] [-l LOGFILE] CAMPAIGN-DIR
  ben-umb (-h | --help)
  ben-umb --version

Options:
  -h --help         Show this screen
  --version         Show version
  -l --log=LOGFILE  Specify an option logfile to write to
  -v -vv            Increase program verbosity
"""

from hpcbench.driver import CampaignDriver
from . import cli_common


def main(argv=None):
    """ben-umb entry point"""
    arguments = cli_common(__doc__, argv=argv)
    driver = CampaignDriver(arguments['CAMPAIGN-DIR'], expandcampvars=False)
    driver(no_exec=True)
    if argv is not None:
        return driver
