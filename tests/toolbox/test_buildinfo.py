import json
import os
import os.path as osp
import subprocess
import tempfile
import unittest

from hpcbench.toolbox.buildinfo import extract_build_info
from hpcbench.toolbox.collections_ext import byteify
from hpcbench.toolbox.contextlib_ext import mkdtemp, pushd

DUMMY_C = """int main(int argc, char** argv) {
  return 0;
}
"""
DUMMY_EXE = 'dummy'

DUMMY_BUILDINFO = """{
  "compiler": {
    "name": "gcc",
    "version": "5.4.0 20160609 (Ubuntu 5.4.0-6ubuntu1~16.04.6)"
  },
  "opt_flags": ["-O0"],
  "build_options": [],
  "extra_info": "this is a test"
}
"""


class TestExtractBuildinfo(unittest.TestCase):
    @classmethod
    def _make_empty_dummy(cls, dummy='dummy'):
        fd, c_file = tempfile.mkstemp(suffix='.c')
        os.write(fd, DUMMY_C.encode('utf-8'))
        os.close(fd)
        subprocess.check_call(['gcc', '-O0', '-o', dummy, c_file])

    @classmethod
    def make_empty_dummy(cls, dummy='dummy'):
        cls._make_empty_dummy(dummy)

    @classmethod
    def make_dummy(cls, dummy='dummy'):
        cls._make_empty_dummy(dummy)
        fd, buildinfo_file = tempfile.mkstemp(suffix='.buildinfo')
        os.write(fd, DUMMY_BUILDINFO.encode('utf-8'))
        os.close(fd)
        subprocess.check_call(
            [
                'objcopy',
                '-I',
                'elf64-x86-64',
                '-O',
                'elf64-x86-64',
                '--add-section',
                'build_info=' + buildinfo_file,
                dummy,
            ]
        )

    @classmethod
    def get_json(cls):
        return json.loads(DUMMY_BUILDINFO, object_hook=byteify)

    @unittest.skipIf(
        'TRAVIS_TAG' in os.environ,
        'objcopy version does not support --dump-section yet',
    )
    def test_extract_build_info(self):
        with mkdtemp() as test_dir, pushd(test_dir):
            TestExtractBuildinfo.make_dummy(DUMMY_EXE)
            build_info = extract_build_info(osp.join(test_dir, DUMMY_EXE))
            self.assertEqual(
                build_info, json.loads(DUMMY_BUILDINFO, object_hook=byteify)
            )

    @unittest.skipIf(
        'TRAVIS_TAG' in os.environ,
        'objcopy version does not support --dump-section yet',
    )
    def test_no_build_info(self):
        with mkdtemp() as test_dir, pushd(test_dir):
            TestExtractBuildinfo.make_empty_dummy(DUMMY_EXE)
            build_info = extract_build_info(osp.join(test_dir, DUMMY_EXE))
            self.assertEqual(build_info, {})
