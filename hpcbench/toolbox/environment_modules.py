import os
import subprocess

from . process import find_executable


MODULECMD = find_executable('modulecmd', required=False)


def module(*args):
    command = [MODULECMD, 'python'] + list(args)
    with open(os.devnull, 'w') as devnull:
        proc = subprocess.Popen(command,
                                stdout=subprocess.PIPE, stderr=devnull)
        stdout, _ = proc.communicate()
        exec(stdout)
