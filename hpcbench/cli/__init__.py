"""Provide all package executables
"""
import logging

from docopt import docopt

from hpcbench import __version__
from hpcbench.toolbox.loader import load_components

LOGGING_FORMAT = "%(asctime)-15s:%(levelname)s:%(name)s:%(message)s"


def setup_logger(verbose, logfile):
    """Prepare root logger
    :param verbose: integer greater than 0 to indicate verbosity level
    """
    level = logging.WARNING
    if verbose == 1:
        level = logging.INFO
    elif verbose > 1:
        level = logging.DEBUG
    if logfile:
        logging.basicConfig(filename=logfile, level=level, format=LOGGING_FORMAT)
    else:
        logging.basicConfig(level=level, format=LOGGING_FORMAT)


def cli_common(doc, **kwargs):
    """Program initialization for all provided executables
    """
    arguments = docopt(doc, version='hpcbench ' + __version__, **kwargs)
    setup_logger(arguments['-v'], arguments['--log'])
    load_components()
    try:
        import matplotlib
    except ImportError:
        pass
    else:
        matplotlib.use('PS')
    return arguments
