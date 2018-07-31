import unittest

from hpcbench.api import ExecutionContext
from hpcbench.benchmark.imb import IMB
from .benchmark import AbstractBenchmarkTest
from .. import FakeBenchmark, FakeCluster


class TestImb(AbstractBenchmarkTest, unittest.TestCase):
    EXPECTED_METRICS = {
        IMB.PING_PONG: dict(
            max_bw=8344.45,
            max_bw_bytes=524288,
            maxb_bw=5257.28,
            maxb_bw_bytes=4194304,
            min_lat=0.20,
            min_lat_bytes=1,
            minb_lat=0.20,
            minb_lat_bytes=1,
            raw=[
                dict(bytes=1, latency=0.20, bandwidth=4.89),
                dict(bytes=2, latency=0.21, bandwidth=9.66),
                dict(bytes=4, latency=0.21, bandwidth=19.04),
                dict(bytes=8, latency=0.24, bandwidth=33.06),
                dict(bytes=16, latency=0.22, bandwidth=74.40),
                dict(bytes=32, latency=0.22, bandwidth=147.82),
                dict(bytes=64, latency=0.23, bandwidth=283.16),
                dict(bytes=128, latency=0.28, bandwidth=453.82),
                dict(bytes=256, latency=0.28, bandwidth=924.05),
                dict(bytes=512, latency=0.34, bandwidth=1497.03),
                dict(bytes=1024, latency=0.43, bandwidth=2376.19),
                dict(bytes=2048, latency=0.57, bandwidth=3574.67),
                dict(bytes=4096, latency=1.12, bandwidth=3672.09),
                dict(bytes=8192, latency=2.54, bandwidth=3229.0),
                dict(bytes=16384, latency=3.34, bandwidth=4901.71),
                dict(bytes=32768, latency=5.83, bandwidth=5623.53),
                dict(bytes=65536, latency=8.85, bandwidth=7401.94),
                dict(bytes=131072, latency=16.83, bandwidth=7790.19),
                dict(bytes=262144, latency=33.17, bandwidth=7904.11),
                dict(bytes=524288, latency=62.83, bandwidth=8344.45),
                dict(bytes=1048576, latency=183.61, bandwidth=5710.82),
                dict(bytes=2097152, latency=409.45, bandwidth=5121.82),
                dict(bytes=4194304, latency=797.81, bandwidth=5257.28),
            ],
        ),
        IMB.ALL_TO_ALL: dict(
            max_bw=3685.14,
            max_bw_bytes=32768,
            maxb_bw=1280.39,
            maxb_bw_bytes=4194304,
            min_lat=0.38,
            min_lat_bytes=1,
            minb_lat=0.38,
            minb_lat_bytes=1,
        ),
        IMB.ALL_GATHER: dict(
            max_bw=2290.22,
            max_bw_bytes=65536,
            maxb_bw=1010.21,
            maxb_bw_bytes=4194304,
            min_lat=0.65,
            min_lat_bytes=8,
            minb_lat=0.68,
            minb_lat_bytes=1,
        ),
    }

    def get_benchmark_clazz(self):
        return IMB

    def get_expected_metrics(self, category):
        return TestImb.EXPECTED_METRICS[category]

    def get_benchmark_categories(self):
        return IMB.DEFAULT_CATEGORIES

    @property
    def attributes(self):
        return dict(executable='/path/to/fake')

    @property
    def exec_context(self):
        node = 'node03'
        tag = '*'
        nodes = ['node01', 'node02', 'node03', 'node04', 'node05']
        return ExecutionContext(
            benchmark=FakeBenchmark.DEFAULT_BENCHMARK_NAME,
            cluster=FakeCluster(tag, nodes, node),
            logger=self.logger,
            node=node,
            srun_options=[],
            tag=tag,
        )

    @property
    def expected_execution_matrix(self):
        return [
            dict(
                command=['/path/to/fake', 'PingPong'],
                srun_nodes=('node03', 'node04'),
                category='PingPong',
                metas=dict(from_node='node03', to_node='node04'),
            ),
            dict(
                command=['/path/to/fake', 'PingPong'],
                srun_nodes=('node03', 'node05'),
                category='PingPong',
                metas=dict(from_node='node03', to_node='node05'),
            ),
            dict(
                command=['/path/to/fake', 'Allgather', '-npmin', '{process_count}'],
                srun_nodes=0,
                category='Allgather',
            ),
            dict(
                command=['/path/to/fake', 'Alltoallv', '-npmin', '{process_count}'],
                srun_nodes=0,
                category='Alltoallv',
            ),
        ]
