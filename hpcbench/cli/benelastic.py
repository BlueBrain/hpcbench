"""ben-elastic - Export campaign in Elasticsearch

Usage:
  ben-elastic [-v | -vv] [--es=<host>] CAMPAIGN-DIR
  ben-elastic (-h | --help)
  ben-elastic --version

Options:
  --es=<host>  Elasticsearch host [default: localhost]
  -h, --help   Show this screen
  --version    Show version
  -v -vv       Increase program verbosity
"""

from hpcbench.driver import CampaignDriver
from hpcbench.export import ESExporter
from hpcbench.toolbox.contextlib_ext import pushd
from . import cli_common


def main(argv=None):
    """ben-elastic entry point"""
    arguments = cli_common(__doc__, argv=argv)
    campaign_path = arguments['CAMPAIGN-DIR']
    driver = CampaignDriver(campaign_path=campaign_path)
    es_host = arguments['--es']
    if es_host:
        es_conf = driver.campaign.export.elasticsearch
        es_conf.host = es_host
    driver.campaign.export.elasticsearch.hosts = es_host
    es_export = ESExporter(driver)
    with pushd(campaign_path):
        es_export.export()
    if argv is not None:
        return es_export
