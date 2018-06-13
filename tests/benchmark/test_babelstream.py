import textwrap
import unittest

import mock

from hpcbench.benchmark.babelstream import BabelStream
from .benchmark import AbstractBenchmarkTest


class TestBabelStream(AbstractBenchmarkTest, unittest.TestCase):
    EXPECTED_METRICS = dict(
        copy_bandwidth=152212.0,
        mul_bandwidth=152026.0,
        add_bandwidth=150275.0,
        triad_bandwidth=150272.0,
        dot_bandwidth=144512.0,
    )

    def get_benchmark_clazz(self):
        return BabelStream

    def get_expected_metrics(self, category):
        del category
        return TestBabelStream.EXPECTED_METRICS

    @property
    def attributes(self):
        return dict(executable='/fake-stream', devices=["0"])

    def get_benchmark_categories(self):
        return [BabelStream.CATEGORY]

    def test_custom_attributes(self):
        self.assertExecutionMatrix(
            dict(devices=42, executable='/foo', options=['--csv']),
            [
                dict(
                    category='stream',
                    command=['/foo', '--device', '42', '--csv'],
                    metas=dict(device=42),
                )
            ],
        )

    DEVICES_MOCK_OUTPUT = textwrap.dedent(
        """\
    Devices:
    01: Tesla K20m
    02: Tesla K20m
    """
    )

    @mock.patch('subprocess.check_output')
    def test_list_devices(self, mock_co):
        mock_co.return_value = TestBabelStream.DEVICES_MOCK_OUTPUT
        self.assertExecutionMatrix(
            dict(executable='/bar'),
            [
                dict(
                    category='stream',
                    command=['/bar', '--device', '01', '--csv'],
                    metas=dict(device=1),
                ),
                dict(
                    category='stream',
                    command=['/bar', '--device', '02', '--csv'],
                    metas=dict(device=2),
                ),
            ],
        )
