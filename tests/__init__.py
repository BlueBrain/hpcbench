import inspect
import os.path as osp
import shutil
import sys
import tempfile
from textwrap import dedent

from cached_property import cached_property
import six

from hpcbench.api import (
    Benchmark,
    Metric,
    MetricsExtractor,
)
from hpcbench.cli import bensh
from hpcbench.toolbox.contextlib_ext import pushd
from . toolbox.test_buildinfo import TestExtractBuildinfo


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


class NullExtractor(MetricsExtractor):

    @property
    def metrics(self):
        return dict()

    def extract_metrics(self, metas):
        return dict()


class FakeExtractor(MetricsExtractor):
    def __init__(self, show_cwd=None):
        self.show_cwd = show_cwd

    @cached_property
    def metrics(self):
        metrics = dict(
            performance=Metric('m', float),
            standard_error=Metric('m', float),
            pairs=[dict(first=Metric('m', float),
                        second=Metric('m', bool))]
        )
        if self.show_cwd:
            metrics.update(path=Metric('', str))
        return metrics

    def extract_metrics(self, metas):
        with open(self.stdout) as istr:
            content = istr.readlines()
            metrics = dict(
                performance=float(content[0].strip()),
                standard_error=float(content[1].strip()),
                pairs=[
                    dict(first=1.5, second=True),
                    dict(first=3.0, second=False),
                ],
            )
            if self.show_cwd:
                metrics.update(path=content[2].strip())
        return metrics


class BuildInfoBench(Benchmark):
    name = 'buildinfo_tester'

    description = '''
        fake benchmark for testing build info extraction
    '''

    metric_required = False

    def __init__(self):
        super(BuildInfoBench, self).__init__(
            attributes=dict(
                run_path=None,
            )
        )
        temp_dir = tempfile.mkdtemp(prefix='hpcbench-ut')
        bibench = osp.join(temp_dir, 'bibench')
        TestExtractBuildinfo.make_dummy(bibench)
        self.exe_matrix = [dict(
            category='main',
            command=[bibench],
            metas=dict()
        )]

    @property
    def in_campaign_template(self):
        return False

    @property
    def build_info(self):
        return TestExtractBuildinfo.get_json()

    def execution_matrix(self, context):
        del context
        return self.exe_matrix

    @property
    def metrics_extractors(self):
        return NullExtractor()


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
                run_path=None,
            )
        )

    def pre_execute(self, execution):
        with open('test.py', 'w') as ostr:
            ostr.write(dedent("""\
            from __future__ import print_function
            import os
            import sys

            print(sys.argv[1])
            print(float(sys.argv[1]) / 10)
            if os.environ.get('SHOW_CWD'):
                print(os.getcwd())
            """))

    def execution_matrix(self, context):
        del context  # unused
        cmds = [
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
        if self.attributes['run_path']:
            for cmd in cmds:
                cmd.update(
                    environment=dict(SHOW_CWD='1'),
                    cwd=self.attributes['run_path']
                )
        return cmds

    @property
    def metrics_extractors(self):
        return dict(main=FakeExtractor(self.attributes['run_path']))

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
