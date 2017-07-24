import logging
import pkg_resources
from pkg_resources import (
    working_set,
    DistributionNotFound,
    VersionConflict,
    UnknownExtra,
)

LOGGER = logging.getLogger()


def load_eggs(entry_point_name):
    """Loader that loads any eggs in `sys.path`."""
    def _load_eggs():
        distributions, errors = working_set.find_plugins(
            pkg_resources.Environment()
        )
        for dist in distributions:
            if dist not in working_set:
                LOGGER.debug('Adding plugin %s from %s', dist, dist.location)
                working_set.add(dist)

        def _log_error(item, e):
            if isinstance(e, DistributionNotFound):
                LOGGER.debug('Skipping "%s": ("%s" not found)', item, e)
            elif isinstance(e, VersionConflict):
                LOGGER.error('Skipping "%s": (version conflict "%s")',
                             item, e)
            elif isinstance(e, UnknownExtra):
                LOGGER.error('Skipping "%s": (unknown extra "%s")', item, e)
            else:
                LOGGER.error('Skipping "%s": %s', item, e)

        for dist, e in errors.iteritems():
            _log_error(dist, e)

        for entry in sorted(working_set.iter_entry_points(entry_point_name),
                            key=lambda entry: entry.name):
            LOGGER.debug(
                'Loading %s from %s',
                entry.name,
                entry.dist.location
            )
            try:
                entry.load(require=True)
            except Exception as exc:
                _log_error(entry, exc)
    return _load_eggs


def load_components(loaders=(load_eggs('hpcbench.benchmarks'),)):
    """Load all plugin components found in `sys.path`."""
    for loadfunc in loaders:
        loadfunc()
