import contextlib
import os
import os.path as osp
import timeit


@contextlib.contextmanager
def pushd(path, mkdir=True):
    cwd = os.getcwd()
    if mkdir and not osp.exists(path):
        os.makedirs(path)
    os.chdir(path)
    try:
        yield path
    finally:
        os.chdir(cwd)


class Timer(object):
    def __init__(self):
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
        if self.end is None:
            return self.timer() - self.end
        return self.end - self.start
