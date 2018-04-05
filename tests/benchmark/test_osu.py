import unittest

from hpcbench.api import ExecutionContext
from hpcbench.benchmark.osu import OSU
from . benchmark import AbstractBenchmarkTest


class TestOSU(AbstractBenchmarkTest, unittest.TestCase):
    EXPECTED_METRICS = {
        OSU.OSU_BW: dict(
            max_bw=11952.24,
            max_bw_bytes=4194304,
            maxb_bw=11952.24,
            maxb_bw_bytes=4194304,
            raw=[
                {'bandwidth': 11923.92, 'bytes': 2097152},
                {'bandwidth': 11952.24, 'bytes': 4194304},
            ]
        ),
        OSU.OSU_LAT: dict(
            min_lat=3.68,
            min_lat_bytes=16,
            minb_lat=3.84,
            minb_lat_bytes=64,
            raw=[
                {'bytes': 16, 'latency': 3.68},
                {'bytes': 32, 'latency': 3.85},
                {'bytes': 64, 'latency': 3.84}
            ]
        ),
    }

    def get_benchmark_clazz(self):
        return OSU

    def get_expected_metrics(self, category):
        return TestOSU.EXPECTED_METRICS[category]

    def get_benchmark_categories(self):
        return OSU.DEFAULT_CATEGORIES

    @property
    def attributes(self):
        return dict(
            executable='/path/to/fake'
        )

    @property
    def exec_context(self):
        return ExecutionContext(
            node='node03',
            tag='*',
            nodes=[
                'node01',
                'node03',
                'node05',
            ],
            logger=self.logger,
            srun_options=[],
        )

    @property
    def expected_execution_matrix(self):
        return [
            dict(
                command=['/path/to/fake', '-x', '200', '-i', '100'],
                srun_nodes=['node03', 'node05'],
                category='osu_bw'
            ),
            dict(
                command=['/path/to/fake', '-x', '200', '-i', '100'],
                srun_nodes=['node03', 'node05'],
                category='osu_latency'
            ),
        ]
