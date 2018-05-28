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
            minb_lat=3.68,
            minb_lat_bytes=16,
            raw=[
                {'bytes': 16, 'latency': 3.68},
                {'bytes': 32, 'latency': 3.85},
                {'bytes': 64, 'latency': 3.84}
            ]
        ),
        OSU.OSU_ALLTOALLV: dict(
            min_lat=1.31,
            min_lat_bytes=128,
            minb_lat=8.64,
            minb_lat_bytes=64,
            raw=[
                {'bytes': 64, 'latency': 8.64},
                {'bytes': 128, 'latency': 1.31},
                {'bytes': 256, 'latency': 1.58},
                {'bytes': 512, 'latency': 1.71},
                {'bytes': 1024, 'latency': 1.98}
            ]
        ),
        OSU.OSU_ALLGATHERV: dict(
            min_lat=1.64,
            min_lat_bytes=64,
            minb_lat=1.64,
            minb_lat_bytes=64,
            raw=[
                {'bytes': 64, 'latency': 1.64},
                {'bytes': 128, 'latency': 6.18},
                {'bytes': 256, 'latency': 1.84},
                {'bytes': 512, 'latency': 2.37},
                {'bytes': 1024, 'latency': 3.06}
            ]
        ),
        OSU.OSU_MBW_MR: dict(
            max_bw=4306.41,
            max_mr=4205474.79,
            max_bw_bytes=1024,
            maxb_bw=4306.41,
            maxb_mr=4205474.79,
            maxb_bw_bytes=1024,
            raw=[
                {'bytes': 64, 'bandwidth': 489.18, 'msg_rate': 7643378.59},
                {'bytes': 128, 'bandwidth': 998.25, 'msg_rate': 7798822.08},
                {'bytes': 256, 'bandwidth': 1912.59, 'msg_rate': 7471067.52},
                {'bytes': 512, 'bandwidth': 3080.21, 'msg_rate': 6016034.42},
                {'bytes': 1024, 'bandwidth': 4306.41, 'msg_rate': 4205474.79}
            ]
        ),
    }

    def get_benchmark_clazz(self):
        return OSU

    def get_expected_metrics(self, category):
        return TestOSU.EXPECTED_METRICS[category]

    def get_benchmark_categories(self):
        return OSU.DEFAULT_CATEGORIES + ['osu_mbw_mr']

    @property
    def attributes(self):
        return dict(
            executable='/path/to/fake',
            srun_nodes=[
                'node01',
                'node03',
                'node05',
            ],
            categories=self.get_benchmark_categories()
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
                command=['/path/to/fake'],
                srun_nodes=['node01', 'node03', 'node05'],
                category='osu_mbw_mr'
            ),
            dict(
                command=['/path/to/fake', '-x', '200', '-i', '100'],
                srun_nodes=['node03', 'node05'],
                category='osu_latency'
            ),
            dict(
                command=['/path/to/fake', '-x', '200', '-i', '100'],
                srun_nodes=['node01', 'node03', 'node05'],
                category='osu_alltoallv'
            ),
            dict(
                command=['/path/to/fake', '-x', '200', '-i', '100'],
                srun_nodes=['node01', 'node03', 'node05'],
                category='osu_allgatherv'
            ),
        ]
