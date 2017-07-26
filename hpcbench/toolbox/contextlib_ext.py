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
def pushd(path, mkdir=True):
    """Change current working directory in a with-context
    :param mkdir: If True, then directory is created if it does not exist
    """
    cwd = os.getcwd()
    if mkdir and not osp.exists(path):
        os.makedirs(path)
    os.chdir(path)
    try:
        yield path
    finally:
        os.chdir(cwd)


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
