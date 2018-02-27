"""Export campaign data to CSV
"""

import csv

from cached_property import cached_property

from hpcbench.campaign import (
    get_metrics,
)
from hpcbench.toolbox.collections_ext import flatten_dict
from hpcbench.toolbox.contextlib_ext import write_wherever


class CSVExporter(object):
    """Export a campaign to CSV
    """

    def __init__(self, campaign, ofile=None):
        """
        :param campaign: instance of ``hpcbench.driver.CampaignDriver``
        :param ofile: a filename or None if stdout should be used
        """
        self.campaign = campaign
        self.ofile = ofile

    def export(self):
        """Create export campaign data to csv
        """
        self._push_data()

    def _push_data(self):
        with write_wherever(self.ofile) as ofo:
            csvf = csv.DictWriter(ofo, fieldnames=list(self._headers))
            csvf.writeheader()
            for run in self._get_runs(self.campaign):
                csvf.writerow(run)

    @cached_property
    def _headers(self):
        headers = {}
        for run in self._get_runs(self.campaign):
            headers = headers | run.keys()
        return headers

    @classmethod
    def _get_runs(cls, campaign):
        for attrs, metrics in get_metrics(campaign):
            for run in metrics:
                run_flat = flatten_dict(run)
                eax = dict()
                eax.update(attrs)
                eax.update(run_flat)
                yield eax

    @classmethod
    def _get_benchmark_runs(cls, campaign, benchmark):
        for attrs, metrics in get_metrics(campaign):
            for run in metrics:
                if run['benchmark'] == benchmark:
                    run_flat = flatten_dict(run)
                    eax = dict()
                    eax.update(attrs)
                    eax.update(run_flat)
                    yield eax
