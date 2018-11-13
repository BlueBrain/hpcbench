import inspect
import os
import os.path as osp
import shutil
import sys
import tempfile
from textwrap import dedent

from cached_property import cached_property
import six
import yaml

from hpcbench.api import Benchmark, Metric, MetricsExtractor
from hpcbench.cli import bensh
from hpcbench.driver.base import ClusterWrapper
from hpcbench.toolbox.contextlib_ext import pushd
from .toolbox.test_buildinfo import TestExtractBuildinfo


class DriverTestCase(object):
    check_campaign_consistency = False
    EXCLUDE_NODES = None

    @classmethod
    def get_campaign_file(cls):
        return osp.splitext(inspect.getfile(cls))[0] + '.yaml'

    @classmethod
    def setUpClass(cls):
        cls.TEST_DIR = cls.mkdtemp()
        with pushd(cls.TEST_DIR):
            argv = []
            if cls.EXCLUDE_NODES:
                argv.extend(['--exclude-nodes', cls.EXCLUDE_NODES])
            argv.append(cls.get_campaign_file())
            cls.driver = bensh.main(argv=argv)
        cls.CAMPAIGN_PATH = osp.join(cls.TEST_DIR, cls.driver.campaign_path)
        if cls.check_campaign_consistency:
            cls._check_campaign_consistency()

    @classmethod
    def mkdtemp(cls):
        return tempfile.mkdtemp(prefix='hpcbench-ut')

    @classmethod
    def _check_campaign_consistency(cls):
        dirs = [cls.CAMPAIGN_PATH]
        while dirs:
            path = dirs.pop()
            files = os.listdir(path)
            if not files:
                # empty directory is considered valid
                continue
            hpcbench_yaml = osp.join(path, 'hpcbench.yaml')
            if not osp.isfile(hpcbench_yaml):
                raise Exception('Missing hpchench.yaml in %s' % hpcbench_yaml)
            with open(hpcbench_yaml) as istr:
                data = yaml.safe_load(istr)
            children = data.get('children', [])
            assert isinstance(children, list)
            children = set(children)
            for file in files:
                fpath = osp.join(path, file)
                if osp.isdir(fpath):
                    dirs.append(fpath)

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
            pairs=[dict(first=Metric('m', float), second=Metric('m', bool))],
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
                pairs=[dict(first=1.5, second=True), dict(first=3.0, second=False)],
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
        super(BuildInfoBench, self).__init__(attributes=dict(run_path=None))
        temp_dir = tempfile.mkdtemp(prefix='hpcbench-ut')
        bibench = osp.join(temp_dir, 'bibench')
        TestExtractBuildinfo.make_dummy(bibench)
        self.exe_matrix = [dict(category='main', command=[bibench], metas=dict())]

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
    """Fake benchmark for HPCBench testing purpose"""

    name = 'fake'

    INPUTS = [10, 20, 100]
    DEFAULT_BENCHMARK_NAME = 'bench-name'

    @property
    def in_campaign_template(self):
        return False

    def __init__(self):
        super(FakeBenchmark, self).__init__(
            attributes=dict(
                input=FakeBenchmark.INPUTS,
                run_path=None,
                executable=sys.executable,
                expected_name=FakeBenchmark.DEFAULT_BENCHMARK_NAME,
            )
        )

    @cached_property
    def executable(self):
        """Get path to python executable"""
        return self.attributes['executable']

    @cached_property
    def run_path(self):
        """benchmark working directory"""
        return self.attributes['run_path']

    @cached_property
    def input(self):
        """Input values"""
        return self.attributes['input']

    @cached_property
    def expected_name(self):
        """benchmark name expected in YAML"""
        return self.attributes['expected_name']

    def pre_execute(self, execution, context):
        del execution  # unused
        del context  # unused
        with open('test.py', 'w') as ostr:
            ostr.write(
                dedent(
                    """\
            from __future__ import print_function
            import os
            import sys

            print(sys.argv[1])
            print(float(sys.argv[1]) / 10)
            if os.environ.get('SHOW_CWD'):
                print(os.getcwd())
            """
                )
            )

    def execution_matrix(self, context):
        msg = "%s != %s" % (repr(context.benchmark), repr(self.expected_name))
        assert context.benchmark == self.expected_name, msg
        cmds = [
            dict(
                category='main',
                command=[self.executable, 'test.py', str(value)],
                metas=dict(field=value / 10)
                if not isinstance(value, six.string_types)
                else None,
            )
            for value in self.input
        ]
        if self.run_path:
            for cmd in cmds:
                cmd.update(environment=dict(SHOW_CWD='1'), cwd=self.run_path)
        return cmds

    @property
    def metrics_extractors(self):
        return dict(main=FakeExtractor(self.run_path))


class FakeNetwork:
    def __init__(self, tag, nodes):
        self._tag = tag
        self._nodes = nodes

    def nodes(self, tag):
        if self._tag is not None:
            assert tag == self._tag
        return self._nodes

    def node_pairs(self, tag, node):
        nodes = self.nodes(tag)
        pos = nodes.index(node)
        return [(node, nodes[i]) for i in range(pos + 1, len(nodes))]


class FakeCluster(ClusterWrapper):
    def __init__(self, tag, nodes, node):
        super(FakeCluster, self).__init__(FakeNetwork(tag, nodes), tag, node)
