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
import errno
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

    def __init__(self, report, jobs):
        self.__report = report
        self.__jobs = jobs

    @property
    def slurm_sbatches(self):
        return bool(self.jobs)

    @property
    def report(self):
        return self.__report

    @property
    def jobs(self):
        return self.__jobs

    @property
    def job_ids(self):
        return [job['id'] for job in self.__job_ids]

    @cached_property
    def status(self):
        status = dict(benchmark=self._benchmarks_status(), succeeded=self.succeeded)
        if self.slurm_sbatches:
            status.update(sbatch=self.jobs)
        return status

    @cached_property
    def succeeded(self):
        ok = all(benchmark['succeeded'] for benchmark in self._benchmarks_status())
        ok &= all(job.get('exit_code', True) for job in self.jobs)
        return ok

    def log(self, fmt):
        if fmt == 'yaml':
            yaml.dump(self.status, sys.stdout, default_flow_style=False)
        elif fmt == 'json':
            json.dump(self.status, sys.stdout, indent=2)
            print()
        elif fmt == 'log':
            attrs = self.report.CONTEXT_ATTRS + ['succeeded']
            for benchmark in self.status['benchmark']:
                fields = [field + '=' + str(benchmark[field]) for field in attrs]
                print('benchmark', *fields)
            for job in self.jobs:
                print('sbatch', *[k + '=' + str(v) for k, v in job.items()])
        else:
            raise Exception('Unknown format: ' + fmt)

    @listify
    def _benchmarks_status(self):
        roots = []
        if self.slurm_sbatches:
            for sbatch in self.report.children.values():
                for tag in sbatch.children.values():
                    assert len(tag.children) <= 1
                    for root in tag.children.values():
                        roots.append(root)
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
        try:
            if not Job.finished(jobid):
                logging.info('waiting for SLURM job %s', jobid)
                time.sleep(interval)
                while not Job.finished(jobid):
                    time.sleep(interval)
            yield Job.fromid(jobid)._asdict()
        except OSError as e:
            if e.errno == errno.ENOENT:
                yield dict(id=str(jobid))
            else:
                raise e


def main(argv=None):
    """ben-wait entry point"""
    arguments = cli_common(__doc__, argv=argv)
    report = ReportNode(arguments['CAMPAIGN-DIR'])
    jobs = wait_for_completion(report, float(arguments['--interval']))
    status = ReportStatus(report, jobs)
    if not arguments['--silent']:
        fmt = arguments['--format'] or 'log'
        status.log(fmt)
    if argv is None:
        sys.exit(0 if status.succeeded else 1)
    return status.status
