"""ben-plot - Generate charts from campaign metrics

Usage:
  ben-plot [-v | -vv] CAMPAIGN-DIR
  ben-plot (-h | --help)
  ben-plot --version

Options:
  -h --help   Show this screen
  --version   Show version
  -v -vv -vvv Increase program verbosity
"""

from docopt import docopt

import matplotlib

from hpcbench import __version__
from hpcbench.driver import CampaignDriver
from hpcbench.toolbox.loader import load_components
from . import setup_logger


def main():
    matplotlib.use('PS')
    arguments = docopt(__doc__, version='hpcbench ' + __version__)
    setup_logger(arguments['-v'])
    load_components()
    campaign_path = arguments['CAMPAIGN-DIR']
    driver = CampaignDriver(campaign_path=campaign_path)
    driver(no_exec=True, plot=True)


if __name__ == '__main__':
    main()
