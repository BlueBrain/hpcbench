import unittest

from hpcbench.benchmark.hpl import HPL
from .benchmark import AbstractBenchmarkTest


class TestHplData(unittest.TestCase):
    def test_default(self):
        self.maxDiff = None
        hpl = HPL()
        expected = dict(realN=3456, nb=192, pQ=[6, 6])
        self.assertEqual(hpl.data, hpl._data_from_jinja(**expected))

    def test_multi_node(self):
        hpl = HPL()
        hpl.attributes.update(
            nodes=24, cores_per_node=36, memory_per_node=378632, block_size=384
        )
        expected = dict(realN=976128, nb=384, pQ=[27, 32])
        self.assertEqual(hpl.data, hpl._data_from_jinja(**expected))


class TestHpl(AbstractBenchmarkTest, unittest.TestCase):
    EXPECTED_METRICS = dict(
        size_n=2096,
        size_nb=192,
        size_p=2,
        size_q=2,
        time=0.29,
        flops=20.98,
        validity=True,
        precision=0.0051555,
    )

    def get_benchmark_clazz(self):
        return HPL

    def get_expected_metrics(self, category):
        return TestHpl.EXPECTED_METRICS

    def get_benchmark_categories(self):
        return [self.get_benchmark_clazz().DEFAULT_DEVICE]

    @property
    def attributes(self):
        return dict(executable='/path/to/fake', mpirun=['-n', 21], srun_nodes=42)

    def test_attributes(self):
        self.assertExecutionMatrix(
            dict(executable='/path/to/fake', srun_nodes='tag-name'),
            [
                dict(
                    category='cpu',
                    environment=dict(
                        KMP_AFFINITY='scatter', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1'
                    ),
                    command=['/path/to/fake'],
                    srun_nodes='tag-name',
                )
            ],
        )
        self.assertExecutionMatrix(
            dict(executable='/path/to/fake', srun_nodes=None),
            [
                dict(
                    category='cpu',
                    environment=dict(
                        KMP_AFFINITY='scatter', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1'
                    ),
                    command=['/path/to/fake'],
                )
            ],
        )
        self.assertExecutionMatrix(
            dict(
                executable='/path/to/fake',
                srun_nodes=None,
                options=[
                    '--problem_size',
                    '100000',
                    '--block_size',
                    '336',
                    '--hpl_numthreads',
                    '64',
                ],
            ),
            [
                dict(
                    category='cpu',
                    environment=dict(
                        KMP_AFFINITY='scatter', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1'
                    ),
                    command=[
                        '/path/to/fake',
                        '--problem_size',
                        '100000',
                        '--block_size',
                        '336',
                        '--hpl_numthreads',
                        '64',
                    ],
                )
            ],
        )
        self.assertExecutionMatrix(
            dict(
                executable='/path/to/fake', srun_nodes=None, mpirun=['mpirun', '-n', 21]
            ),
            [
                dict(
                    category='cpu',
                    environment=dict(
                        KMP_AFFINITY='scatter', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1'
                    ),
                    command=['mpirun', '-n', '21', '/path/to/fake'],
                )
            ],
        )
