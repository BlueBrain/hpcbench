"""Additional methods usable in with-context
"""
import contextlib
import os
import os.path as osp
import shutil
import sys
import tempfile
import timeit

import six


@contextlib.contextmanager
def capture_stdout():
    """Intercept standard output in a with-context
    :return: cStringIO instance

    >>> with capture_stdout() as stdout:
            ...
        print stdout.getvalue()
    """
    stdout = sys.stdout
    sys.stdout = six.moves.cStringIO()
    try:
        yield sys.stdout
    finally:
        sys.stdout = stdout


@contextlib.contextmanager
def write_wherever(file_name=None):
    writer = open(file_name, 'w') if file_name is not None else sys.stdout
    yield writer
    if file_name is not None:
        writer.close()


@contextlib.contextmanager
def pushd(path, mkdir=True, cleanup=False):
    """Change current working directory in a with-context
    :param mkdir: If True, then directory is created if it does not exist
    :param cleanup: If True and no pre-existing directory, the directory is
    cleaned up at the end
    """
    cwd = os.getcwd()
    exists = osp.exists(path)
    if mkdir and not exists:
        os.makedirs(path)
    os.chdir(path)
    try:
        yield path
    finally:
        os.chdir(cwd)
        if not exists and cleanup:
            # NB: should we be checking for rmtree.avoids_symlink_attacks ?
            shutil.rmtree(path)


class Timer(object):  # pylint: disable=too-few-public-methods
    """Object usable in with-context to time it.
    """

    def __init__(self):
        self.start = None
        self.end = None
        self.timer = timeit.Timer()

    def __call__(self):
        return self.timer.timer()

    def __enter__(self):
        self.start = self()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.end = self()

    @property
    def elapsed(self):
        """
        :return: duration in seconds spent in the context.
        :rtype: float
        """
        if self.end is None:
            return self() - self.end
        return self.end - self.start


@contextlib.contextmanager
def mkdtemp(*args, **kwargs):
    """Create a temporary directory in a with-context

    keyword remove: Remove the directory when leaving the
    context if True. Default is True.
    other keywords arguments are given to the tempfile.mkdtemp
    function.
    """
    remove = kwargs.pop('remove', True)
    path = tempfile.mkdtemp(*args, **kwargs)
    try:
        yield path
    finally:
        if remove:
            shutil.rmtree(path)


@contextlib.contextmanager
def modified_environ(*remove, **update):
    """
    Temporarily updates the ``os.environ`` dictionary in-place.

    The ``os.environ`` dictionary is updated in-place so that the modification
    is sure to work in all situations.

    :param remove: Environment variables to remove.
    :param update: Dictionary of environment variables
    and values to add/update.
    """
    env = os.environ
    update = update or {}
    remove = remove or []

    # List of environment variables being updated or removed.
    stomped = (set(update) | set(remove)) & set(env)
    # Environment variables and values to restore on exit.
    update_after = {k: env[k] for k in stomped}
    # Environment variables and values to remove on exit.
    remove_after = frozenset(k for k in update if k not in env)

    try:
        env.update(update)
        [env.pop(k, None) for k in remove]
        yield
    finally:
        env.update(update_after)
        [env.pop(k) for k in remove_after]
