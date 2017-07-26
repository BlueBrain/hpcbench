"""ben-doc - Generate a campaign report

Usage:
  ben-doc [-t TEMPLATE] [-o FILE] [-v | -vv] CAMPAIGN-DIR
  ben-doc (-h | --help)
  ben-doc --version

Options:
  -o, --output FILE  Write report to specified file
                     instead of standard output
  -t, --template FILE Specify a custom Jinja template
  -h, --help   Show this screen
  --version   Show version
  -v -vv -vvv Increase program verbosity
"""

from hpcbench.driver import CampaignDriver
from hpcbench.report import render
from hpcbench.toolbox.contextlib_ext import pushd
from . import cli_common


def main(argv=None):
    """ben-doc entry point"""
    arguments = cli_common(__doc__, argv=argv)
    campaign_path = arguments['CAMPAIGN-DIR']
    driver = CampaignDriver(campaign_path=campaign_path)
    with pushd(campaign_path):
        render(driver,
               template=arguments['--template'],
               ostr=arguments['--output'])


if __name__ == '__main__':
    main()
