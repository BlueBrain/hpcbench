"""Export campaign data to CSV
"""

import csv

from cached_property import cached_property

from hpcbench.campaign import from_file, get_metrics, ReportNode
from hpcbench.toolbox.collections_ext import flatten_dict
from hpcbench.toolbox.contextlib_ext import write_wherever
from hpcbench.toolbox.functools_ext import listify


class CSVExporter(object):
    """Export a campaign to CSV
    """

    def __init__(self, path, ofile=None):
        """
        :param path: path to existing campaign
        :param ofile: a filename or None if stdout should be used
        """
        self.report = ReportNode(path)
        self.campaign = from_file(path, expandcampvars=False)
        self.ofile = ofile

    def export(self, fields=None):
        """Export campaign data to csv
        :param fields: list of columns to export. If None, all columns are.
        """
        if fields:
            self._push_data_filtered(fields)
        else:
            self._push_data()

    def peek(self):
        """Print the Campaign data columns"""
        for col in self._headers:
            print('- ' + col)

    def _push_data(self):
        with write_wherever(self.ofile) as ofo:
            csvf = csv.DictWriter(ofo, fieldnames=self._headers)
            csvf.writeheader()
            for run in self.runs:
                csvf.writerow(run)

    def _push_data_filtered(self, fields):
        if len(set(fields) - self._headers):
            raise ValueError(
                'The provided list of fields contains an element '
                + 'that could not be found in this campaign\n'
                + str(set(fields) - self._headers)
            )
        with write_wherever(self.ofile) as ofo:
            csvf = csv.DictWriter(ofo, fieldnames=fields)
            csvf.writeheader()
            for run in self.runs:
                run_f = {k: v for k, v in run.items() if k in fields}
                csvf.writerow(run_f)

    @cached_property
    def _headers(self):
        headers = set()
        for run in self.runs:
            headers = headers | set(run.keys())
        return headers

    @cached_property
    @listify
    def runs(self):
        for attrs, metrics in get_metrics(self.campaign, self.report):
            for run in metrics:
                run_flat = flatten_dict(run)
                eax = dict()
                eax.update(attrs)
                eax.update(run_flat)
                yield eax
