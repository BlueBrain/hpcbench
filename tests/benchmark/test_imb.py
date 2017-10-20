import unittest

from hpcbench.api import ExecutionContext
from hpcbench.benchmark.imb import IMB
from . benchmark import AbstractBenchmarkTest


class TestImb(AbstractBenchmarkTest, unittest.TestCase):
    EXPECTED_METRICS = {
        IMB.PING_PONG: dict(
            latency=0.20,
            bandwidth=8344.45,
        ),
        IMB.ALL_TO_ALL: dict(
            latency=0.38,
        ),
        IMB.ALL_GATHER: dict(
            latency=0.65,
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
                'node02',
                'node03',
                'node04',
                'node05',
            ],
            logger=self.logger,
            srun_options=[],
        )

    @property
    def expected_execution_matrix(self):
        return [
            dict(
                command=['/path/to/fake', 'PingPong'],
                srun_nodes=['node03', 'node04'],
                category='PingPong'
            ),
            dict(
                command=['/path/to/fake', 'PingPong'],
                srun_nodes=['node03', 'node05'],
                category='PingPong'
            ),
            dict(
                command=[
                    '/path/to/fake', 'Allgather',
                    '-npmin', '{process_count}'
                ],
                srun_nodes=0,
                category='Allgather'
            ),
            dict(
                command=[
                    '/path/to/fake', 'Alltoallv',
                    '-npmin', '{process_count}',
                ],
                srun_nodes=0,
                category='Alltoallv'
            ),
        ]
