"""ben-doc - Generate a campaign report

Usage:
  ben-doc [-t TEMPLATE] [-o FILE] [-v | -vv] [-l LOGFILE] CAMPAIGN-DIR
  ben-doc (-h | --help)
  ben-doc --version

Options:
  -o, --output FILE       Write report to specified file
                          instead of standard output
  -t, --template TEMPLATE Specify a custom Jinja template
  -l --log=LOGFILE        Specify an option logfile to write to
  -h, --help              Show this screen
  --version               Show version
  -v -vv                  Increase program verbosity
"""

from hpcbench.driver import CampaignDriver
from hpcbench.report import render
from hpcbench.toolbox.contextlib_ext import pushd
from . import cli_common


def main(argv=None):
    """ben-doc entry point"""
    arguments = cli_common(__doc__, argv=argv)
    campaign_path = arguments['CAMPAIGN-DIR']
    driver = CampaignDriver(campaign_path, expandcampvars=False)
    with pushd(campaign_path):
        render(
            template=arguments['--template'],
            ostr=arguments['--output'],
            campaign=driver,
        )
    if argv is not None:
        return driver
