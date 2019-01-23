"""OSU Micro Benchmarks
   http://mvapich.cse.ohio-state.edu/benchmarks/
"""
from abc import abstractmethod, abstractproperty
from operator import itemgetter
import re
import logging

from cached_property import cached_property

from hpcbench.api import Benchmark, Metric, Metrics, MetricsExtractor
from hpcbench.toolbox.process import find_executable


LOGGER = logging.getLogger('OSU')


class OSUExtractor(MetricsExtractor):
    """Abstract class for OSU micro benchmark metrics extractor
    """

    def __init__(self):
        self.s_raw_data = []

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

    def extract_metrics(self, metas):
        # parse stdout and extract desired metrics
        self.prelude()
        with open(self.stdout) as istr:
            for line in istr:
                if line.strip() == self.stdout_ignore_prior:
                    break
            for line in istr:
                self.process_line(line.strip())
        if not any(self.s_raw_data):
            # output did not contain metrics
            return {}
        return self.epilog()

    @abstractmethod
    def process_line(self, line):
        """Process a line
        """

    def prelude(self):
        """method called before extracting metrics"""
        self.s_raw_data = []

    @abstractmethod
    def epilog(self):
        """:return: extracted metrics as a dictionary
        """


class OSUBWExtractor(OSUExtractor):
    """Metrics extractor for osu_bw benchmark"""

    BW_BANDWIDTH_RE = re.compile(r'^(\d+)[\s]+(\d*\.?\d+)')

    def __init__(self):
        self._metrics = dict(
            max_bw_bytes=Metrics.Byte,
            max_bw=Metrics.MegaBytesPerSecond,
            maxb_bw_bytes=Metrics.Byte,
            maxb_bw=Metrics.MegaBytesPerSecond,
            raw=[dict(bytes=Metrics.Byte, bandwidth=Metrics.MegaBytesPerSecond)],
        )
        super(OSUBWExtractor, self).__init__()

    @cached_property
    def metrics(self):
        return self._metrics

    @cached_property
    def stdout_ignore_prior(self):
        return "# Size      Bandwidth (MB/s)"

    def process_line(self, line):
        search = self.BW_BANDWIDTH_RE.search(line)
        if search:
            self.s_raw_data.append((int(search.group(1)), float(search.group(2))))

    def epilog(self):
        maxb_bw_b, maxb_bw = self.s_raw_data[-1]
        max_bw_b, max_bw = max(self.s_raw_data, key=itemgetter(1))
        return dict(
            maxb_bw=maxb_bw,
            maxb_bw_bytes=maxb_bw_b,
            max_bw=max_bw,
            max_bw_bytes=max_bw_b,
            raw=[{'bytes': b, 'bandwidth': bw} for b, bw in self.s_raw_data],
        )


class OSUMBWExtractor(OSUBWExtractor):
    """Metrics extractor for osu_mbw_mr benchmark"""

    BW_BANDWIDTH_MSGRATE_RE = re.compile(r'^(\d+)[\s]+(\d*\.?\d+)[\s]+(\d*\.?\d+)')

    def __init__(self):
        super(OSUMBWExtractor, self).__init__()
        msg_rate_metric = Metric('Msg/s', float)
        msg_metrics = dict(max_mr=msg_rate_metric, maxb_mr=msg_rate_metric)
        self._metrics.update(msg_metrics)
        self._metrics['raw'][0]['msg_rate'] = msg_rate_metric

    @cached_property
    def stdout_ignore_prior(self):
        return "# Size                  MB/s        Messages/s"

    def process_line(self, line):
        search = self.BW_BANDWIDTH_MSGRATE_RE.search(line)
        if search:
            self.s_raw_data.append(
                (int(search.group(1)), float(search.group(2)), float(search.group(3)))
            )

    def epilog(self):
        maxb_bw_b, maxb_bw, maxb_mr = self.s_raw_data[-1]
        max_bw_b, max_bw, max_mr = max(self.s_raw_data, key=itemgetter(1))
        return dict(
            maxb_bw=maxb_bw,
            maxb_mr=maxb_mr,
            maxb_bw_bytes=maxb_bw_b,
            max_bw=max_bw,
            max_mr=max_mr,
            max_bw_bytes=max_bw_b,
            raw=[
                {'bytes': b, 'bandwidth': bw, 'msg_rate': mr}
                for b, bw, mr in self.s_raw_data
            ],
        )


class OSULatExtractor(OSUExtractor):
    """Metrics extractor for osu_bw benchmark"""

    BW_LATENCY_RE = re.compile(r'^(\d+)[\s]+(\d*\.?\d+)')

    def __init__(self):
        super(OSULatExtractor, self).__init__()

    @cached_property
    def metrics(self):
        return dict(
            min_lat_bytes=Metrics.Byte,
            min_lat=Metrics.Microsecond,
            minb_lat_bytes=Metrics.Byte,
            minb_lat=Metrics.Microsecond,
            raw=[dict(bytes=Metrics.Byte, latency=Metrics.Microsecond)],
        )

    @cached_property
    def stdout_ignore_prior(self):
        return "# Size          Latency (us)"

    def process_line(self, line):
        search = self.BW_LATENCY_RE.search(line)
        if search:
            bytes = int(search.group(1))
            if bytes > 0:
                self.s_raw_data.append((bytes, float(search.group(2))))

    def epilog(self):
        minb_lat_b, minb_lat = self.s_raw_data[0]
        min_lat_b, min_lat = min(self.s_raw_data, key=itemgetter(1))
        return dict(
            minb_lat=minb_lat,
            minb_lat_bytes=minb_lat_b,
            min_lat=min_lat,
            min_lat_bytes=min_lat_b,
            raw=[{'bytes': b, 'latency': l} for b, l in self.s_raw_data],
        )


class OSUCollectiveLatExtractor(OSUExtractor):
    """Metrics extractor for osu_bw benchmark"""

    BW_LATENCY_RE = re.compile(r'^(\d+)[\s]+(\d*\.?\d+)')

    def __init__(self):
        super(OSUCollectiveLatExtractor, self).__init__()

    @cached_property
    def metrics(self):
        return dict(
            min_lat_bytes=Metrics.Byte,
            min_lat=Metrics.Microsecond,
            minb_lat_bytes=Metrics.Byte,
            minb_lat=Metrics.Microsecond,
            raw=[dict(bytes=Metrics.Byte, latency=Metrics.Microsecond)],
        )

    @cached_property
    def stdout_ignore_prior(self):
        return "# Size       Avg Latency(us)"

    def process_line(self, line):
        search = self.BW_LATENCY_RE.search(line)
        if search:
            bytes = int(search.group(1))
            if bytes > 0:
                self.s_raw_data.append((bytes, float(search.group(2))))

    def epilog(self):
        minb_lat_b, minb_lat = self.s_raw_data[0]
        min_lat_b, min_lat = min(self.s_raw_data, key=itemgetter(1))
        return dict(
            minb_lat=minb_lat,
            minb_lat_bytes=minb_lat_b,
            min_lat=min_lat,
            min_lat_bytes=min_lat_b,
            raw=[{'bytes': b, 'latency': l} for b, l in self.s_raw_data],
        )


class OSU(Benchmark):
    """Benchmark wrapper for the OSU micro benchmarks

    Provides MPI-based interconnect benchmarking.
    the `srun_nodes` does not apply to the PingPong benchmark.
    """

    OSU_BW = 'osu_bw'
    OSU_LAT = 'osu_latency'
    OSU_MBW_MR = 'osu_mbw_mr'
    OSU_ALLGATHER = 'osu_allgather'
    OSU_ALLGATHERV = 'osu_allgatherv'
    OSU_ALLTOALL = 'osu_alltoall'
    OSU_ALLTOALLV = 'osu_alltoallv'
    OSU_REDUCE = 'osu_reduce'
    OSU_ALLREDUCE = 'osu_allreduce'
    NODE_PAIRING = {'node', 'tag'}
    DEFAULT_NODE_PAIRING = 'node'
    DEFAULT_CATEGORIES = [OSU_BW, OSU_LAT, OSU_ALLGATHERV, OSU_ALLTOALLV]
    DEFAULT_OPTIONS = {
        OSU_BW: ["-x", "200", "-i", "100"],
        OSU_MBW_MR: [],
        OSU_LAT: ["-x", "200", "-i", "100"],
        OSU_ALLGATHER: ["-x", "200", "-i", "100"],
        OSU_ALLGATHERV: ["-x", "200", "-i", "100"],
        OSU_ALLTOALL: ["-x", "200", "-i", "100"],
        OSU_ALLTOALLV: ["-x", "200", "-i", "100"],
        OSU_REDUCE: ["-x", "200", "-i", "100"],
        OSU_ALLREDUCE: ["-x", "200", "-i", "100"],
    }

    def __init__(self):
        super(OSU, self).__init__(
            attributes=dict(
                categories=OSU.DEFAULT_CATEGORIES,
                options=OSU.DEFAULT_OPTIONS,
                srun_nodes=0,
                node_pairing=OSU.DEFAULT_NODE_PAIRING,
            )
        )

    name = 'osu'

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
        if 'arguments' in self.attributes:
            LOGGER.warning(
                "WARNING: 'arguments' use in OSU yaml configuration file is deprecated. Please use 'options'!"
            )
            arguments = self.attributes['arguments']
            if isinstance(arguments, dict):
                return arguments
            else:
                return {k: arguments for k in self.categories}
        elif 'options' in self.attributes:
            options = self.attributes['options']
            if isinstance(options, dict):
                return options
            else:
                return {k: options for k in self.categories}

    @property
    def options(self):
        """Dictionary providing the list of arguments for every
        benchmark"""
        return self.attributes['options']

    @property
    def node_pairing(self):
        """if "node" then test current node and next one
        if "tag", then create tests for every pair of the current tag.
        """
        value = self.attributes['node_pairing']
        if value not in OSU.NODE_PAIRING:
            msg = 'Unexpected {0} value: got "{1}" but valid values are {2}'
            msg = msg.format('node_pairing', value, OSU.NODE_PAIRING)
            raise ValueError(msg)
        return value

    def node_pairs(self, context):
        if self.node_pairing == 'node':
            return context.cluster.node_pairs
        elif self.node_pairing == 'tag':
            return context.cluster.tag_node_pairs
        assert False

    @property
    def srun_nodes(self):
        """Number of nodes the benchmark (other than PingPong)
        must be executed on"""
        return self.attributes['srun_nodes']

    def execution_matrix(self, context):
        for category in self.categories:
            arguments = self.arguments.get(category) or []
            if category in {OSU.OSU_BW, OSU.OSU_LAT}:
                if context.implicit_nodes:
                    context.logger.warn(
                        'Category %s does not support ' 'SLURM implicit nodes', category
                    )
                else:
                    executable = find_executable(
                        self.executable(category), required=False
                    )
                    for pair in self.node_pairs(context):
                        yield dict(
                            category=category,
                            command=[executable] + arguments,
                            srun_nodes=pair,
                            metas=dict(from_node=pair[0], to_node=pair[1]),
                        )
            else:
                yield dict(
                    category=category,
                    command=[find_executable(self.executable(category), required=False)]
                    + arguments,
                    srun_nodes=self.srun_nodes,
                )

    @cached_property
    def metrics_extractors(self):
        return {
            OSU.OSU_BW: OSUBWExtractor(),
            OSU.OSU_LAT: OSULatExtractor(),
            OSU.OSU_MBW_MR: OSUMBWExtractor(),
            OSU.OSU_ALLGATHER: OSUCollectiveLatExtractor(),
            OSU.OSU_ALLGATHERV: OSUCollectiveLatExtractor(),
            OSU.OSU_ALLTOALL: OSUCollectiveLatExtractor(),
            OSU.OSU_ALLTOALLV: OSUCollectiveLatExtractor(),
            OSU.OSU_REDUCE: OSUCollectiveLatExtractor(),
            OSU.OSU_ALLREDUCE: OSUCollectiveLatExtractor(),
        }
