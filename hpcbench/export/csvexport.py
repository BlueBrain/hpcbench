"""Export campaign data to CSV
"""

import csv

from cached_property import cached_property

from hpcbench.campaign import (
    get_benchmark_types,
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

    @property
    def _documents(self):
        for run in CSVExporter._get_runs(self.campaign):
            yield dict(
                index=dict(
                    _type=run['benchmark'],
                    _id=run['id']
                )
            )
            yield run

    @cached_property
    def _headers(self):
        headers = {}
        for run in self._get_runs(self.campaign):
            headers = headers | run.keys()
        return headers

    @cached_property
    def _document_types(self):
        return [
            benchmark
            for benchmark in get_benchmark_types(self.campaign.campaign)
        ]

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
                    eax = dict()
                    eax.update(attrs)
                    eax.update(run)
                    yield eax
