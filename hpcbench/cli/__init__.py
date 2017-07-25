import logging

from docopt import docopt
import matplotlib

from hpcbench import __version__
from hpcbench.toolbox.loader import load_components


def setup_logger(verbose):
    level = logging.WARNING
    if verbose == 1:
        level = logging.INFO
    elif verbose > 1:
        verbose = logging.DEBUG
    logging.basicConfig(level=level)


def cli_common(doc, **kwargs):
    arguments = docopt(doc, version='hpcbench ' + __version__, **kwargs)
    setup_logger(arguments['-v'])
    load_components()
    matplotlib.use('PS')
    return arguments
