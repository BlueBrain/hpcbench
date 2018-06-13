import os
import unittest

import mock

from hpcbench.benchmark.nvidia import NvidiaP2pBandwidthLatencyTest
from .benchmark import AbstractBenchmarkTest


class TestNvidiaP2pBandwidthLatency(AbstractBenchmarkTest, unittest.TestCase):
    def setUp(self):
        self.prev_cuda_visible_devices = os.environ.get('CUDA_VISIBLE_DEVICES')
        os.environ['CUDA_VISIBLE_DEVICES'] = "42,46"

    def tearDown(self):
        if self.prev_cuda_visible_devices is not None:
            os.environ['CUDA_VISIBLE_DEVICES'] = self.prev_cuda_visible_devices
        else:
            os.environ.pop('CUDA_VISIBLE_DEVICES', None)

    EXPECTED_METRICS = dict(
        unidirectional_bandwidth=5.66 * 1024,
        p2p_unidirectional_bandwidth=5.82 * 1024,
        bidirectional_bandwidth=10.32 * 1024,
        p2p_bidirectional_bandwidth=10.40 * 1024,
        latency=22.48,
        p2p_latency=22.55,
    )

    def get_benchmark_clazz(self):
        return NvidiaP2pBandwidthLatencyTest

    def get_expected_metrics(self, category):
        del category
        return TestNvidiaP2pBandwidthLatency.EXPECTED_METRICS

    @property
    def attributes(self):
        return dict(executable='/fake-stream')

    def get_benchmark_categories(self):
        return [NvidiaP2pBandwidthLatencyTest.CATEGORY]

    @mock.patch('subprocess.check_output')
    def test_custom_attributes(self, mock_co):
        self.assertExecutionMatrix(
            dict(executable='/deviceQuery'),
            [
                dict(
                    category='gpu',
                    command=['/deviceQuery'],
                    environment=dict(CUDA_VISIBLE_DEVICES="42,46"),
                    metas=dict(device1=42, device2=46),
                )
            ],
        )
        os.environ.pop('CUDA_VISIBLE_DEVICES')
        with open('tests/benchmark/nvidia-deviceQuery.stdout') as istr:
            mock_co.return_value = istr.read()
        self.assertExecutionMatrix(
            dict(executable='/deviceQuery', devicequery_executable='/fake'),
            [
                dict(
                    category='gpu',
                    command=['/deviceQuery'],
                    environment=dict(CUDA_VISIBLE_DEVICES="6,8"),
                    metas=dict(device1=6, device2=8),
                ),
                dict(
                    category='gpu',
                    command=['/deviceQuery'],
                    environment=dict(CUDA_VISIBLE_DEVICES="6,10"),
                    metas=dict(device1=6, device2=10),
                ),
                dict(
                    category='gpu',
                    command=['/deviceQuery'],
                    environment=dict(CUDA_VISIBLE_DEVICES="8,10"),
                    metas=dict(device1=8, device2=10),
                ),
            ],
        )
