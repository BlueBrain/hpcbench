"""Extract build information from executables
"""

import json

try:
    from json import JSONDecodeError as JSONDcdError
except ImportError:
    JSONDcdError = ValueError
import logging
import subprocess

from hpcbench.toolbox.collections_ext import byteify
from hpcbench.toolbox.contextlib_ext import mkdtemp, pushd


LOGGER = logging.getLogger('hpcbench')

OBJCOPY = 'objcopy'
DUMP_SECTION = '--dump-section'
ELF_SECTION = 'build_info'
BUILDINFO_FILE = 'buildinfo.json'


def extract_build_info(exe_path, elf_section=ELF_SECTION):
    """Extracts the build information from a given executable.

    The build information is expected to be in json format, which is parsed
    and returned as a dictionary.
    If no build information is found an empty dictionary is returned.

    This assumes binutils 2.25 to work.

    Args:
        exe_path (str): The full path to the executable to be examined

    Returns:
        dict: A dictionary of the extracted information.
    """
    build_info = {}
    with mkdtemp() as tempd, pushd(tempd):
        proc = subprocess.Popen(
            [
                OBJCOPY,
                DUMP_SECTION,
                "{secn}={ofile}".format(secn=elf_section, ofile=BUILDINFO_FILE),
                exe_path,
            ],
            stderr=subprocess.PIPE,
        )
        proc.wait()
        errno = proc.returncode
        stderr = proc.stderr.read()
        if errno or len(stderr):  # just return the empty dict
            LOGGER.warning('objcopy failed with errno %s.', errno)
            if len(stderr):
                LOGGER.warning('objcopy failed with following msg:\n%s', stderr)
            return build_info

        with open(BUILDINFO_FILE) as build_info_f:
            try:
                build_info = json.load(build_info_f, object_hook=byteify)
            except JSONDcdError as jsde:
                LOGGER.warning('benchmark executable build is not valid json:')
                LOGGER.warning(jsde.msg)
                LOGGER.warning('build info section content:')
                LOGGER.warning(jsde.doc)
    return build_info
