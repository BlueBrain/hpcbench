"""The Intel MPI Benchmarks
    https://software.intel.com/en-us/articles/intel-mpi-benchmarks
"""
from abc import abstractmethod, abstractproperty
import re

from cached_property import cached_property

from hpcbench.api import (
    Benchmark,
    Metrics,
    MetricsExtractor,
)
from hpcbench.toolbox.process import find_executable


class IMBExtractor(MetricsExtractor):
    """Abstract class for IMB benchmark metrics extractor
    """
    @abstractproperty
    def metrics(self):
        """ The metrics to be extracted.
            This property can not be replaced, but can be mutated as required
        """

    @abstractproperty
    def stdout_ignore_prior(self):
        """Ignore stdout until this line"""

    @cached_property
    def metrics_names(self):
        """get metrics names"""
        return set(self.metrics)

    def extract_metrics(self, outdir, metas):
        # parse stdout and extract desired metrics
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

    @abstractmethod
    def epilog(self):
        """:return: extracted metrics as a dictionary
        """


class IMBPingPongExtractor(IMBExtractor):
    """Metrics extractor for PingPong IMB benchmark"""

    LATENCY_BANDWIDTH_RE = re.compile(
        r'^\s*(\d+)\s+\d+\s+(\d*\.?\d+)[\s]+(\d*\.?\d+)'
    )

    def __init__(self):
        super(IMBPingPongExtractor, self).__init__()
        self.s_latency = set()
        self.s_bandwidth = set()

    @cached_property
    def metrics(self):
        return dict(
            latency=Metrics.Second,
            bandwidth=Metrics.MegaBytesPerSecond,
        )

    @cached_property
    def stdout_ignore_prior(self):
        return "# Benchmarking PingPong"

    def process_line(self, line):
        search = self.LATENCY_BANDWIDTH_RE.search(line)
        if search:
            byte = int(search.group(1))
            if byte != 0:
                self.s_latency.add(float(search.group(2)))
                self.s_bandwidth.add(float(search.group(3)))

    def epilog(self):
        return dict(
            latency=min(self.s_latency),
            bandwidth=max(self.s_bandwidth),
        )


class IMBAllToAllExtractor(IMBExtractor):
    """Metrics extractor for AllToAll IMB benchmark"""

    LATENCY_RE = re.compile(
        r'^\s*(\d+)\s+\d+\s+\d*\.?\d+[\s]+\d*\.?\d+[\s]+(\d*\.?\d+)'
    )

    def __init__(self):
        super(IMBAllToAllExtractor, self).__init__()
        self.s_res = set()

    @property
    def metrics(self):
        return dict(latency=Metrics.Second)

    @cached_property
    def stdout_ignore_prior(self):
        return "# Benchmarking Alltoallv"

    def process_line(self, line):
        search = self.LATENCY_RE.search(line)
        if search:
            byte = int(search.group(1))
            if byte != 0:
                self.s_res.add(float(search.group(2)))

    def epilog(self):
        return dict(latency=min(self.s_res))


class IMBAllGatherExtractor(IMBAllToAllExtractor):
    """Metrics extractor for AllGather IMB benchmark"""

    def __init__(self):
        super(IMBAllGatherExtractor, self).__init__()

    @cached_property
    def stdout_ignore_prior(self):
        return "# Benchmarking Allgather"


class IMB(Benchmark):
    """Benchmark wrapper for the IMBbench utility

    the `srun_nodes` does not apply to the PingPong benchmark.
    """
    DEFAULT_EXECUTABLE = 'IMB-MPI1'
    PING_PONG = 'PingPong'
    ALL_TO_ALL = 'Alltoallv'
    ALL_GATHER = 'Allgather'
    DEFAULT_CATEGORIES = [
        PING_PONG,
        ALL_TO_ALL,
        ALL_GATHER,
    ]
    DEFAULT_ARGUMENTS = {
        ALL_GATHER: ["-npmin", "{process_count}"],
        ALL_TO_ALL: ["-npmin", "{process_count}"],
    }

    def __init__(self):
        super(IMB, self).__init__(
            attributes=dict(
                executable=IMB.DEFAULT_EXECUTABLE,
                categories=IMB.DEFAULT_CATEGORIES,
                arguments=IMB.DEFAULT_ARGUMENTS,
                srun_nodes=0,
            )
        )
    name = 'imb'

    description = "Provides latency/bandwidth of the network."

    @cached_property
    def executable(self):
        """Get path to Intel MPI Benchmark executable
        """
        return self.attributes['executable']

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
            if category == IMB.PING_PONG:
                for pair in IMB.host_pairs(context):
                    yield dict(
                        category=category,
                        command=[
                            find_executable(self.executable),
                            category
                        ] + arguments,
                        srun_nodes=pair,
                    )
            else:
                yield dict(
                    category=category,
                    command=[self.executable, category] + arguments,
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
            IMB.PING_PONG: IMBPingPongExtractor(),
            IMB.ALL_TO_ALL: IMBAllToAllExtractor(),
            IMB.ALL_GATHER: IMBAllGatherExtractor(),
        }
