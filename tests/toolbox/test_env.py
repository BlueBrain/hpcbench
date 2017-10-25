import os
import unittest

from hpcbench.toolbox.env import expandvars


class TestEnvVarExpander(unittest.TestCase):
    def test_variable(self):
        self.assertExpansionEquals('test $TEST_VARIABLE', 'test value')

    def test_quoted_variable(self):
        self.assertExpansionEquals('test ${TEST_VARIABLE}', 'test value')

    def test_variable_length(self):
        self.assertExpansionEquals('test ${#TEST_VARIABLE}', 'test 5')

    def assertExpansionEquals(self, pattern, expanded):
        os.environ['TEST_VARIABLE'] = "value"
        try:
            self.assertEquals(expandvars(pattern), expanded)
        finally:
            os.environ.pop('TEST_VARIABLE')
