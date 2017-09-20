import unittest

from hpcbench.benchmark.ior import IOR
from . benchmark import AbstractBenchmarkTest


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
            executable='/path/to/fake'
        )
