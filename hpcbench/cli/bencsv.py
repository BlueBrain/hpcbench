"""ben-csv - Export campaign CSV

Usage:
  ben-csv [-v | -vv] [-l LOGFILE] [-o CSVFILE] [-f FIELDS] CAMPAIGN-DIR
  ben-csv [-v | -vv] -p  CAMPAIGN-DIR
  ben-csv (-h | --help)
  ben-csv --version

Options:
  -o --output=CSVFILE  CSV file
  -f --fields=FIELDS   comma-separated list of fields that should be output
                       in CSV
  -p --peek            peek into campaign and print out all CSV column names
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
    """ben-csv entry point"""
    arguments = cli_common(__doc__, argv=argv)
    campaign_path = arguments['CAMPAIGN-DIR']
    driver = CampaignDriver(campaign_path, expandcampvars=False)
    with pushd(campaign_path):
        csv_export = CSVExporter(driver, arguments['--output'])
        if arguments['--peek']:
            csv_export.peek()
        else:
            fieldsstr = arguments.get('--fields')
            fields = fieldsstr.split(',') if fieldsstr else None
            csv_export.export(fields)
        if argv is not None:
            return csv_export
