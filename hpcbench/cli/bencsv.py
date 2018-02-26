"""ben-csv - Export campaign CSV

Usage:
  ben-csv [-v | -vv] [-l LOGFILE] [-o CSVFILE] CAMPAIGN-DIR
  ben-csv (-h | --help)
  ben-csv --version

Options:
  -o --output=CSVFILE  CSV file
  -l --log=LOGFILE     Specify an option logfile to write to
  -h, --help           Show this screen
  --version            Show version
  -v -vv               Increase program verbosity
"""

from hpcbench.driver import CampaignDriver
from hpcbench.export import CSVExporter
from hpcbench.toolbox.contextlib_ext import pushd
from . import cli_common


def main(argv=None):
    """ben-elastic entry point"""
    arguments = cli_common(__doc__, argv=argv)
    campaign_path = arguments['CAMPAIGN-DIR']
    driver = CampaignDriver(campaign_path=campaign_path)
    csv_export = CSVExporter(driver, arguments['--output'])
    with pushd(campaign_path):
        csv_export.export()
    if argv is not None:
        return csv_export
