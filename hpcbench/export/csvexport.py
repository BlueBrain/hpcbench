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

    def export(self, fields=None):
        """Export campaign data to csv
        :param fields: a comma-seperated string of columns to be
                       used for exporting
        """
        if fields:
            self._push_data_filtered(fields)
        else:
            self._push_data()

    def peek(self):
        """Print the Campaign data columns"""
        for col in self._headers:
            print('- '+col)

    def _push_data(self):
        with write_wherever(self.ofile) as ofo:
            csvf = csv.DictWriter(ofo, fieldnames=self._headers)
            csvf.writeheader()
            for run in self._get_runs(self.campaign):
                csvf.writerow(run)

    def _push_data_filtered(self, fieldstr):
        fields = fieldstr.split(',')
        if len(set(fields) - self._headers):
            raise ValueError('The provided list of fields contains an element '
                             + 'that could not be found in this campaign\n'
                             + str(set(fields) - self._headers))
        with write_wherever(self.ofile) as ofo:
            csvf = csv.DictWriter(ofo, fieldnames=fields)
            csvf.writeheader()
            for run in self._get_runs(self.campaign):
                run_f = {k: v for k, v in run.items() if k in fields}
                csvf.writerow(run_f)

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
