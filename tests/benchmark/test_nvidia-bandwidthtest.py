import unittest

from hpcbench.benchmark.nvidia import NvidiaBandwidthTest
from .benchmark import AbstractBenchmarkTest


class TestNvidiaBandwidthTest(AbstractBenchmarkTest, unittest.TestCase):
    EXPECTED_METRICS = dict(
        device_to_device_bandwidth=147968.8,
        device_to_host_bandwidth=6549.3,
        host_to_device_bandwidth=6139.4,
    )

    def get_benchmark_clazz(self):
        return NvidiaBandwidthTest

    def get_expected_metrics(self, category):
        del category
        return TestNvidiaBandwidthTest.EXPECTED_METRICS

    @property
    def attributes(self):
        return dict(executable='/fake-stream', devices=["0"])

    def get_benchmark_categories(self):
        return [NvidiaBandwidthTest.CATEGORY]

    def test_custom_attributes(self):
        self.assertExecutionMatrix(
            dict(device=42, executable='/foo', options=['--csv']),
            [
                dict(
                    category='gpu',
                    command=['/foo', '--device', '42', '--mode', 'shmoo', '--csv'],
                    metas=dict(device=42),
                )
            ],
        )
