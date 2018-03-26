"""OSU Micro Benchmarks
   http://mvapich.cse.ohio-state.edu/benchmarks/
"""
from abc import abstractmethod, abstractproperty
from operator import itemgetter
import re

from cached_property import cached_property

from hpcbench.api import (
    Benchmark,
    Metrics,
    MetricsExtractor,
)
from hpcbench.toolbox.process import find_executable


class OSUExtractor(MetricsExtractor):
    """Abstract class for OSU micro benchmark metrics extractor
    """
    @abstractproperty
    def metrics(self):
        """Define metrics"""

    @abstractproperty
    def stdout_ignore_prior(self):
        """Ignore stdout until this line"""

    @cached_property
    def metrics_names(self):
        """get metrics names"""
        return set(self.metrics)

    def extract_metrics(self, outdir, metas):
        # parse stdout and extract desired metrics
        self.prelude()
        with open(self.stdout(outdir)) as istr:
            for line in istr:
                if line.strip() == self.stdout_ignore_prior:
                    break
            for line in istr:
                self.process_line(line.strip())
        return self.epilog()

    @abstractmethod
    def process_line(self, line):
        """Process a line
        """

    def prelude(self):
        """method called before extracting metrics"""

    @abstractmethod
    def epilog(self):
        """:return: extracted metrics as a dictionary
        """


class OSUBWExtractor(OSUExtractor):
    """Metrics extractor for osu_bw benchmark"""

    BW_BANDWIDTH_RE = re.compile(
        r'^(\d+)[\s]+(\d*\.?\d+)'
    )

    def __init__(self):
        super(OSUBWExtractor, self).__init__()
        self.s_bytes = []
        self.s_bandwidth = []

    @cached_property
    def metrics(self):
        return dict(max_bw_bytes=Metrics.Byte,
                    max_bw=Metrics.MegaBytesPerSecond,
                    maxb_bw_bytes=Metrics.Byte,
                    maxb_bw=Metrics.MegaBytesPerSecond)

    def prelude(self):
        self.s_bytes.clear()
        self.s_bandwidth.clear()

    @cached_property
    def stdout_ignore_prior(self):
        return "# Size      Bandwidth (MB/s)"

    def process_line(self, line):
        search = self.BW_BANDWIDTH_RE.search(line)
        if search:
            self.s_bytes.append(int(search.group(0)))
            self.s_bandwidth.append(float(search.group(1)))

    def epilog(self):
        maxb_bw, maxb_bw_b = self.s_bandwidth[-1], self.s_bytes[-1]
        max_bw, max_bw_b = max(zip(self.s_bandwidth, self.s_bytes),
                               key=itemgetter(0))
        return dict(maxb_bw=maxb_bw, maxb_bw_bytes=maxb_bw_b,
                    max_bw=max_bw, max_bw_bytes=max_bw_b)


class OSULatExtractor(OSUExtractor):
    """Metrics extractor for osu_bw benchmark"""

    BW_LATENCY_RE = re.compile(
        r'^(\d+)[\s]+(\d*\.?\d+)'
    )

    def __init__(self):
        super(OSULatExtractor, self).__init__()
        self.s_bytes = []
        self.s_latency = []

    @cached_property
    def metrics(self):
        return dict(mn_lat_bytes=Metrics.Byte,
                    min_lat=Metrics.Microsecond,
                    minb_lat_bytes=Metrics.Byte,
                    minb_lat=Metrics.Microsecond)

    def prelude(self):
        self.s_bytes.clear()
        self.s_latency.clear()

    @cached_property
    def stdout_ignore_prior(self):
        return "# Size      Bandwidth (MB/s)"

    def process_line(self, line):
        search = self.BW_LATENCY_RE.search(line)
        if search:
            bytes = int(search.group(0))
            if bytes > 0:
                self.s_bytes.append(bytes)
                self.s_latency.append(float(search.group(1)))

    def epilog(self):
        minb_lat, minb_lat_b = self.s_latency[-1], self.s_bytes[-1]
        min_lat, min_lat_b = max(zip(self.s_latency, self.s_bytes),
                               key=itemgetter(0))
        return dict(minb_lat=minb_lat, minb_lat_bytes=minb_lat_b,
                    min_lat=min_lat, min_lat_bytes=min_lat_b)


class OSU(Benchmark):
    """Benchmark wrapper for the OSU micro benchmarks

    the `srun_nodes` does not apply to the PingPong benchmark.
    """
    OSU_BW = 'osu_bw'
    OSU_LAT = 'osu_latency'
    DEFAULT_CATEGORIES = [
        OSU_BW,
        OSU_LAT,
    ]
    DEFAULT_ARGUMENTS = {
        OSU_BW: ["-x", "200", "-i", "100"],
        OSU_LAT: ["-x", "200", "-i", "100"],
    }

    def __init__(self):
        super(OSU, self).__init__(
            attributes=dict(
                categories=OSU.DEFAULT_CATEGORIES,
                arguments=OSU.DEFAULT_ARGUMENTS,
                srun_nodes=0,
            )
        )
    name = 'osu'

    description = "Provides MPI-based interconnect benchmarking."

    def executable(self, category=None):
        """Get path to OSU micro benchmark executable

        If no executable is provided then use the category name and find it
        in the path.
        """
        if 'executable' in self.attributes:
            return self.attributes['executable']
        else:
           return category

    @property
    def categories(self):
        """List of IMB benchmarks to test"""
        return self.attributes['categories']

    @property
    def arguments(self):
        """Dictionary providing the list of arguments for every
        benchmark"""
        return self.attributes['arguments']

    @property
    def srun_nodes(self):
        """Number of nodes the benchmark (other than PingPong)
        must be executed on"""
        return self.attributes['srun_nodes']

    def execution_matrix(self, context):
        for category in self.categories:
            arguments = self.arguments.get(category) or []
            if category == OSU.OSU_BW:
                for pair in OSU.host_pairs(context):
                    yield dict(
                        category=category,
                        command=[find_executable(self.executable(category))]
                                + arguments,
                        srun_nodes=pair,
                    )
            else:
                yield dict(
                    category=category,
                    command=[find_executable(self.executable(category))]
                            + arguments,
                    srun_nodes=self.srun_nodes
                )

    @staticmethod
    def host_pairs(context):
        try:
            pos = context.nodes.index(context.node)
        except ValueError:
            context.logger.error(
                'Could not find current node %s in nodes %s',
                context.node,
                ', '.join(context.nodes)
            )
            return []
        else:
            return [
                [context.node, context.nodes[i]]
                for i in range(pos + 1, len(context.nodes))
            ]

    @cached_property
    def metrics_extractors(self):
        return {
            OSU.OSU_BW: OSUBWExtractor(),
            OSU.OSU_LAT: OSULatExtractor(),
        }
