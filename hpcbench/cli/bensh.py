"""ben-sh

Usage:
  ben-sh [-v | -vv ] [-n HOST] CAMPAIGN_FILE
  ben-sh (-h | --help)
  ben-sh --version

Options:
  -n HOST     Specify node name. Default is localhost
  -h --help   Show this screen
  --version   Show version
  -v -vv -vvv Increase program verbosity
"""

from hpcbench.driver import CampaignDriver
from . import cli_common


def main(argv=None):
    """ben-sh entry point"""
    arguments = cli_common(__doc__, argv=argv)
    node = arguments.get('-n')
    driver = CampaignDriver(campaign_file=arguments['CAMPAIGN_FILE'],
                            node=node)
    driver()
    if argv is not None:
        return driver


if __name__ == '__main__':
    main()
