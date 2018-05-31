"""ben-sh - Execute a campaign

Usage:
  ben-sh [-v | -vv] [-r TAG] [-n HOST] [-o OUTDIR] [-l LOGFILE]
         [-g] CAMPAIGN_FILE
  ben-sh (-h | --help)
  ben-sh --version

Options:
  -n HOST                 Specify node name. Default is localhost
  -o --output-dir=OUTDIR  Specify output directory, overwriting campaign file
                          output_dir directive
  -l --log=LOGFILE        Specify an option logfile to write to
  -r --srun=TAG           Go into srun mode and run on one tag, which is used
                          when ben-sh is called as a dependent process inside
                          a SLURM job.
  -h --help               Show this screen
  -g                      Generate a default YAML campaign file
  --version               Show version
  -v -vv                  Increase program verbosity
"""

import os.path as osp

from hpcbench.campaign import Generator
from hpcbench.driver import CampaignDriver
from . import cli_common


def main(argv=None):
    """ben-sh entry point"""
    arguments = cli_common(__doc__, argv=argv)
    campaign_file = arguments['CAMPAIGN_FILE']
    if arguments['-g']:
        if osp.exists(campaign_file):
            raise Exception('Campaign file already exists')
        with open(campaign_file, 'w') as ostr:
            Generator().write(ostr)
    else:
        node = arguments.get('-n')
        output_dir = arguments.get('--output-dir')
        srun_tag = arguments.get('--srun')
        driver = CampaignDriver(campaign_file,
                                node=node,
                                output_dir=output_dir,
                                srun=srun_tag)
        driver()
        if argv is not None:
            return driver
