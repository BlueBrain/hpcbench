"""ben-umb - Rebuild metrics of an existing campaign

Usage:
  ben-umb [-v | -vv] CAMPAIGN-DIR
  ben-umb (-h | --help)
  ben-umb --version

Options:
  -h --help   Show this screen
  --version   Show version
  -v -vv -vvv Increase program verbosity
"""

from hpcbench.driver import CampaignDriver
from . import cli_common


def main(argv=None):
    """ben-umb entry point"""
    arguments = cli_common(__doc__, argv=argv)
    driver = CampaignDriver(campaign_path=arguments['CAMPAIGN-DIR'])
    driver(no_exec=True)
    return driver


if __name__ == '__main__':
    main()
