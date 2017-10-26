"""Helper functions for processes
"""
import os
import os.path as osp
import platform
import subprocess


def find_in_paths(name, paths):
    """Find an executable is a list of directories
    :return: absolute path to the first location where the executable
    is found, ``None`` otherwise.
    :rtype: string
    """
    for path in paths:
        file_ = osp.join(path, name)
        if osp.exists(file_) and not osp.isdir(file_):
            abs_file = osp.abspath(file_)
            if os.access(file_, os.X_OK):
                return abs_file


def find_executable(name, names=None, required=True):
    """Utility function to find an executable in PATH
    name: program to find. Use given value if absolute path

    names: list of additional names. For instance

       >>> find_executable('sed', names=['gsed'])

    required: If True, then the function raises an Exception
    if the program is not found.
    """
    path_from_env = os.environ.get(name.upper())
    if path_from_env is not None:
        return path_from_env
    names = [name] + (names or [])
    for _name in names:
        if osp.isabs(_name):
            return _name
        paths = os.environ.get('PATH', '').split(os.pathsep)
        eax = find_in_paths(_name, paths)
        if eax:
            return eax
    if required:
        raise NameError('Could not find %s executable' % name)


def physical_cpus():
    """Get cpus identifiers, for instance set(["0", "1", "2", "3"])

    :return Number of physical CPUs available
    :rtype: int
    """
    if platform.system() == 'Darwin':
        ncores = subprocess.check_output(
            ['/usr/sbin/sysctl', '-n', 'hw.ncpu'],
            shell=False
        )
        return int(ncores.strip())

    sockets = set()
    with open('/proc/cpuinfo') as istr:
        for line in istr:
            if line.startswith('physical id'):
                sockets.add(line.split(':')[-1].strip())
    return len(sockets)
