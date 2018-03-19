"""ben-plot - Generate charts from campaign metrics

Usage:
  ben-plot [-v | -vv] [-l LOGFILE] CAMPAIGN-DIR
  ben-plot (-h | --help)
  ben-plot --version

Options:
  -h --help         Show this screen
  -l --log=LOGFILE  Specify an option logfile to write to
  --version         Show version
  -v -vv            Increase program verbosity
"""

from hpcbench.driver import CampaignDriver
from . import cli_common


def main(argv=None):
    """ben-plot entry point"""
    arguments = cli_common(__doc__, argv=argv)
    driver = CampaignDriver(campaign_path=arguments['CAMPAIGN-DIR'],
                            expandcampvars=False)
    driver(no_exec=True, plot=True)
    if argv is not None:
        return driver
