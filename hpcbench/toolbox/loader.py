"""Load symbols referenced in setuptools entry points
"""

import logging

from pkg_resources import (
    DistributionNotFound,
    Environment,
    UnknownExtra,
    VersionConflict,
    working_set,
)


LOGGER = logging.getLogger()


def load_eggs(entry_point_name):
    """Loader that loads any eggs in `sys.path`."""

    def _load_eggs():
        distributions, errors = working_set.find_plugins(Environment())
        for dist in distributions:
            # pylint: disable=unsupported-membership-test
            if dist not in working_set:
                LOGGER.debug('Adding plugin %s from %s', dist, dist.location)
                working_set.add(dist)

        def _log_error(item, err):
            if isinstance(err, DistributionNotFound):
                LOGGER.debug('Skipping "%s": ("%s" not found)', item, err)
            elif isinstance(err, VersionConflict):
                LOGGER.error('Skipping "%s": (version conflict "%s")', item, err)
            elif isinstance(err, UnknownExtra):
                LOGGER.error('Skipping "%s": (unknown extra "%s")', item, err)
            else:
                LOGGER.error('Skipping "%s": %s', item, err)

        for dist, err in errors.items():
            _log_error(dist, err)

        for entry in sorted(
            working_set.iter_entry_points(entry_point_name),
            key=lambda entry: entry.name,
        ):
            try:
                entry.load(require=True)
            except Exception as exc:  # pylint: disable=broad-except
                _log_error(entry, exc)

    return _load_eggs


def load_components(loaders=(load_eggs('hpcbench.benchmarks'),)):
    """Load all plugin components found in `sys.path`."""
    for loadfunc in loaders:
        loadfunc()
