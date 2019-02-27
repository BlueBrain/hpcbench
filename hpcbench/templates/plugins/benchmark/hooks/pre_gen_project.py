from __future__ import print_function

import re
import sys


def check_benchmark_name():
    name = '''{{ cookiecutter.benchmark }}'''
    if not re.match('^[-a-z]+$', name):
        error = 'ERROR: invalid benchmark: "{}"'
        error += ' Expecting regular expression [-a-z]+'
        print(error.format(name), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    check_benchmark_name()
