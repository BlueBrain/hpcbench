import unittest

from hpcbench.benchmark.ior import IOR
from .benchmark import AbstractBenchmarkTest


class TestIORBenchmark(AbstractBenchmarkTest, unittest.TestCase):
    def get_benchmark_clazz(self):
        return IOR

    def get_expected_metrics(self, category):
        return dict(
            read_agg_size=1048576,
            read_block_size=1048576,
            read_file_per_proc=0,
            read_max=85.18,
            read_mean=85.18,
            read_mean_time=0.01174,
            read_min=85.18,
            read_reorder_tasks=True,
            read_reorder_tasks_random=True,
            read_reorder_tasks_random_seed=0,
            read_repetitions=1,
            read_segments=1,
            read_std_dev=0.0,
            read_tasks_per_node=1,
            read_task_per_node_offset=1,
            read_tasks=1,
            read_transfer_size=262144,
            write_agg_size=1048576,
            write_block_size=1048576,
            write_file_per_proc=0,
            write_max=75.82,
            write_mean=75.82,
            write_mean_time=0.01319,
            write_min=75.82,
            write_reorder_tasks=True,
            write_reorder_tasks_random=True,
            write_reorder_tasks_random_seed=0,
            write_repetitions=1,
            write_segments=1,
            write_std_dev=0.0,
            write_tasks_per_node=1,
            write_task_per_node_offset=1,
            write_tasks=1,
            write_transfer_size=262144,
        )

    def get_benchmark_categories(self):
        return ['POSIX']

    @property
    def attributes(self):
        return dict(
            executable='/path/to/fake',
            path='ime:///path/with/ime/{benchmark}/{api}/{file_mode}/{block_size}/{transfer_size}/test',
        )

    @property
    def expected_execution_matrix(self):
        paths = dict(
            POSIX='/ime/bench-name/POSIX/fpp/1G/32M/test/data',
            MPIIO='ime:///path/with/ime/bench-name/MPIIO/fpp/1G/32M/test/data',
            HDF5='ime:///path/with/ime/bench-name/HDF5/fpp/1G/32M/test/data',
        )
        return [
            dict(
                category=api,
                command=[
                    '/path/to/fake',
                    '-a',
                    api,
                    '-b',
                    '1G',
                    '-t',
                    '32M',
                    '-i',
                    '3',
                    '-o',
                    paths[api],
                    '-F',
                ],
                metas=dict(file_mode='fpp', block_size='1G', transfer_size='32M'),
                srun_nodes=0,
            )
            for api in IOR.APIS
        ]

    def test_sizes(self):
        ior = IOR()
        ior.attributes['sizes'] = [
            dict(transfer="1K 4K", block="8M"),
            dict(transfer="1M 4M", block="1G"),
        ]
        sizes = sorted(list(ior.sizes))
        self.assertEqual(
            sizes, [('1G', '1M'), ('1G', '4M'), ('8M', '1K'), ('8M', '4K')]
        )
