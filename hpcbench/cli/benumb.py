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

from docopt import docopt

from hpcbench import __version__
from hpcbench.driver import CampaignDriver
from hpcbench.toolbox.loader import load_components
from . import setup_logger


def main():
    arguments = docopt(__doc__, version='hpcbench ' + __version__)
    setup_logger(arguments['-v'])
    load_components()
    campaign_path = arguments['CAMPAIGN-DIR']
    driver = CampaignDriver(campaign_path=campaign_path)
    driver(no_exec=True)


if __name__ == '__main__':
    main()
