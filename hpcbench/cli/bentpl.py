"""ben-tpl Generate HPCBench related templates

Usage:
  ben-tpl [-v | -vv ] [-l LOGFILE] (benchmark) [-i ] [-g|-o DIR] <FILE>
  ben-tpl (-h | --help)
  ben-tpl --version

Options:
  -g                Generate configuration template
  -i, --interactive
  -h --help         Show this screen
  -o <DIR>, --output-dir <DIR>
  -l --log=LOGFILE  Specify an option logfile to write to
  --version         Show version
  -v -vv            Increase program verbosity
"""

import json
import logging
import os


from hpcbench import template
from . import cli_common


def main(argv=None):
    """ben-tpl entry point"""
    arguments = cli_common(__doc__, argv=argv)
    plugin = 'benchmark' if arguments['benchmark'] else None

    if arguments['-g']:
        template.generate_config(plugin, arguments['<FILE>'])
    else:
        with open(arguments['<FILE>']) as istr:
            context = json.load(istr)
        kwargs = dict(no_input=True, extra_context=context)
        if arguments['--output-dir']:
            kwargs.update(output_dir=arguments['--output-dir'])
        if arguments['--interactive']:
            kwargs.update(no_input=False)
        logging.info(
            'generating template in directory ' + kwargs.get('output_dir', os.getcwd())
        )
        template.generate_template(plugin, **kwargs)
