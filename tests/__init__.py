import inspect
import os.path as osp
import shutil
import sys
import tempfile
from textwrap import dedent

import six

from hpcbench.api import (
    Benchmark,
    Metric,
    MetricsExtractor,
)
from hpcbench.cli import bensh
from hpcbench.toolbox.contextlib_ext import pushd


class DriverTestCase(object):
    @classmethod
    def get_campaign_file(cls):
        return osp.splitext(inspect.getfile(cls))[0] + '.yaml'

    @classmethod
    def setUpClass(cls):
        cls.TEST_DIR = tempfile.mkdtemp(prefix='hpcbench-ut')
        with pushd(cls.TEST_DIR):
            cls.driver = bensh.main(cls.get_campaign_file())
        cls.CAMPAIGN_PATH = osp.join(cls.TEST_DIR,
                                     cls.driver.campaign_path)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.TEST_DIR)


class FakeExtractor(MetricsExtractor):
    @property
    def metrics(self):
        return dict(
            performance=Metric('m', float),
            standard_error=Metric('m', float)
        )

    def extract_metrics(self, outdir, metas):
        with open(self.stdout(outdir)) as istr:
            content = istr.readlines()
            return dict(
                performance=float(content[0].strip()),
                standard_error=float(content[1].strip())
            )
        assert not osp.isfile(self.stderr(outdir))


class FakeBenchmark(Benchmark):
    name = 'fake'

    description = '''
        fake benchmark for HPCBench testing purpose
    '''

    INPUTS = [10, 20, 100]

    @property
    def in_campaign_template(self):
        return False

    def __init__(self):
        super(FakeBenchmark, self).__init__(
            attributes=dict(
                input=FakeBenchmark.INPUTS,
            )
        )

    def pre_execute(self, execution):
        with open('test.py', 'w') as ostr:
            ostr.write(dedent("""\
            from __future__ import print_function
            import sys

            print(sys.argv[1])
            print(float(sys.argv[1]) / 10)
            """))

    def execution_matrix(self, context):
        del context  # unused
        return [
            dict(
                category='main',
                command=[
                    sys.executable, 'test.py', str(value)
                ],
                metas=dict(field=value / 10)
                if not isinstance(value, six.string_types) else None
            )
            for value in self.attributes['input']
        ]

    @property
    def metrics_extractors(self):
        return dict(main=FakeExtractor())

    @property
    def plots(self):
        return dict(
            main=[
                dict(
                    name="{hostname} {category} Performance",
                    series=dict(
                        metas=['field'],
                        metrics=[
                            'performance',
                            'standard_error'
                        ],
                    ),
                    plotter=self.plot_performance
                )
            ]
        )

    def plot_performance(self, plt, description, metas, metrics):
        plt.errorbar(metas['field'],
                     metrics['performance'],
                     yerr=metrics['standard_error'],
                     fmt='o', ecolor='g', capthick=2)
