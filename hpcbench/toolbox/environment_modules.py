import os
from subprocess import PIPE, Popen

from .process import find_executable


class Module:
    MODULECMD = find_executable('modulecmd', required=False)

    @classmethod
    def load(cls, *args):
        cls.python('load', *args)

    @classmethod
    def unload(cls, *args):
        cls.python('load', *args)

    @classmethod
    def purge(cls, *args):
        cls.python('purge', *args)

    @classmethod
    def python(cls, *args):
        command = [cls.MODULECMD, 'python'] + list(args)
        with open(os.devnull, 'w') as devnull:
            proc = Popen(command, shell=False, stdout=PIPE, stderr=devnull)
            stdout, _ = proc.communicate()
            exec(stdout)
