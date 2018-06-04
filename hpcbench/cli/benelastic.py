"""ben-elastic - Export campaign in Elasticsearch

Usage:
  ben-elastic [-v | -vv] [-l LOGFILE] [--es=<host>] CAMPAIGN-DIR
  ben-elastic (-h | --help)
  ben-elastic --version

Options:
  --es=<host>       Elasticsearch host [default: localhost]
  -l --log=LOGFILE  Specify an option logfile to write to
  -h, --help        Show this screen
  --version         Show version
  -v -vv            Increase program verbosity
"""

from hpcbench.export import ESExporter
from . import cli_common


def main(argv=None):
    """ben-elastic entry point"""
    arguments = cli_common(__doc__, argv=argv)
    es_export = ESExporter(arguments['CAMPAIGN-DIR'], arguments['--es'])
    es_export.export()
    if argv is not None:
        return es_export
