import logging


def setup_logger(verbose):
    level = logging.WARNING
    if verbose == 1:
        level = logging.INFO
    elif verbose > 1:
        verbose == logging.DEBUG
    logging.basicConfig(level=level)
