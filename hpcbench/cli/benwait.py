"""ben-wait - Wait for asynchronous processes

Usage:
  ben-wait [-v | -vv] [--interval=<seconds>] [-l LOGFILE]
           [--silent] [--format=<format>]
           CAMPAIGN-DIR
  ben-wait (-h | --help)
  ben-wait --version

Options:
  -l --log=LOGFILE                    Specify an option logfile to write to.
  -n <seconds>, --interval <seconds>  Specify wait interval [default: 10].
  -s --silent                         Do you write campaign status to console
  -f --format=FORMAT                  Campaign status output format.
                                      possible values: json, yaml, log[default]
  -h --help                           Show this screen.
  --version                           Show version.
  -v -vv                              Increase program verbosity.

Exit status:
  exits 1 if at least one of the benchmark executions fails, 0 otherwise.
"""
from __future__ import print_function
import json
import logging
import sys
import time

from cached_property import cached_property
import yaml

from hpcbench.campaign import ReportNode
from hpcbench.toolbox.functools_ext import listify
from hpcbench.toolbox.slurm import Job
from . import cli_common


class ReportStatus:
    """Build a dictionary reporting benchmarks execution status"""
    def __init__(self, report, job_ids):
        self.__report = report
        self.__job_ids = job_ids

    @property
    def slurm_sbatches(self):
        return bool(self.__job_ids)

    @property
    def report(self):
        return self.__report

    @property
    def job_ids(self):
        return self.__job_ids

    @cached_property
    def status(self):
        status = dict(benchmarks=self._benchmarks_status())
        if self.slurm_sbatches:
            status.update(slurm_jobs=self.job_ids)
        return status

    @cached_property
    def successfull(self):
        return all(
            benchmark['succeeded']
            for benchmark in self.status['benchmarks']
        )

    def log(self, fmt):
        if fmt == 'yaml':
            yaml.dump(self.status, sys.stdout, default_flow_style=False)
        elif fmt == 'json':
            json.dump(self.status, sys.stdout, indent=2)
            print()
        elif fmt == 'log':
            attrs = self.report.CONTEXT_ATTRS + ['succeeded']
            for benchmark in self.status['benchmarks']:
                fields = [
                    field + '=' + str(benchmark[field])
                    for field in attrs
                ]
                print(*fields)
        else:
            raise Exception('Unknown format: ' + fmt)

    @listify
    def _benchmarks_status(self):
        roots = []
        if self.slurm_sbatches:
            for sbatch in self.report.children.values():
                for tag in sbatch.children.values():
                    assert len(tag.children) == 1
                    roots.append(tag.children.values()[0])
        else:
            roots.append(self.report)
        for root in roots:
            for path, succeeded in root.collect('command_succeeded', with_path=True):
                ctx = root.path_context(path)
                ctx.update(succeeded=succeeded)
                yield ctx


@listify
def wait_for_completion(report, interval=10):
    """Wait for asynchronous jobs stil running in the given campaign.

    :param report: memory representation of a campaign report
    :type campaign: ReportNode
    :param interval: wait interval
    :type interval: int or float
    :return: list of asynchronous job identifiers
    """
    for jobid in report.collect('jobid'):
        if not Job.finished(jobid):
            logging.info('waiting for SLURM job %s', jobid)
            time.sleep(interval)
            while not Job.finished(jobid):
                time.sleep(interval)
        yield jobid


def main(argv=None):
    """ben-wait entry point"""
    arguments = cli_common(__doc__, argv=argv)
    report = ReportNode(arguments['CAMPAIGN-DIR'])
    job_ids = wait_for_completion(report, float(arguments['--interval']))
    status = ReportStatus(report, job_ids)
    if not arguments['--silent']:
        fmt = arguments['--format'] or 'log'
        status.log(fmt)
    if argv is None:
        sys.exit(0 if status.successfull else 1)
    return status.status
