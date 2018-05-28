"""ben-wait - Wait for asynchronous processes

Usage:
  ben-wait [-v | -vv] [--interval=<seconds>] [-l LOGFILE] CAMPAIGN-DIR
  ben-wait (-h | --help)
  ben-wait --version

Options:
  -l --log=LOGFILE                    Specify an option logfile to write to.
  -n <seconds>, --interval <seconds>  Specify wait interval [default: 10].
  -h --help                           Show this screen.
  --version                           Show version.
  -v -vv                              Increase program verbosity.
"""

import logging
import subprocess
import time

from hpcbench.campaign import ReportNode
from hpcbench.toolbox.functools_ext import listify
from hpcbench.toolbox.process import find_executable
from . import cli_common


def is_slurm_job_terminated(jobid):
    output = subprocess.check_output([
        find_executable('sacct'),
        '-n', '-X', '-o', "end", '-j', str(jobid)
    ])
    end = output.strip()
    end = end.decode()
    return end != 'Unknown'


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
        while not is_slurm_job_terminated(jobid):
            logging.info('waiting for SLURM job %s', jobid)
            time.sleep(interval)
        yield jobid


def main(argv=None):
    """ben-wait entry point"""
    arguments = cli_common(__doc__, argv=argv)
    report = ReportNode(arguments['CAMPAIGN-DIR'])
    wait_for_completion(report, float(arguments['--interval']))
