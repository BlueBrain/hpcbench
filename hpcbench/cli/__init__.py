"""Provide all package executables
"""
import logging

from docopt import docopt

from hpcbench import __version__
from hpcbench.toolbox.loader import load_components


def setup_logger(verbose):
    """Prepare root logger
    :param verbose: integer greater than 0 to indicate verbosity level
    """
    level = logging.WARNING
    if verbose == 1:
        level = logging.INFO
    elif verbose > 1:
        level = logging.DEBUG
    logging.basicConfig(level=level)


def cli_common(doc, **kwargs):
    """Program initialization for all provided executables
    """
    arguments = docopt(doc, version='hpcbench ' + __version__, **kwargs)
    setup_logger(arguments['-v'])
    load_components()
    try:
        import matplotlib
    except ImportError:
        pass
    else:
        matplotlib.use('PS')
    return arguments
