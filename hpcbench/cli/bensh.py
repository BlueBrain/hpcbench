"""ben-sh

Usage:
  ben-sh [-v | -vv ] CAMPAIGN_FILE
  ben-sh (-h | --help)
  ben-sh --version

Options:
  -h --help   Show this screen
  --version   Show version
  -v -vv -vvv Increase program verbosity
"""

from hpcbench.driver import CampaignDriver
from . import cli_common


def main(argv=None):
    """ben-sh entry point"""
    arguments = cli_common(__doc__, argv=argv)
    driver = CampaignDriver(campaign_file=arguments['CAMPAIGN_FILE'])
    driver()
    if argv is not None:
        return driver


if __name__ == '__main__':
    main()
