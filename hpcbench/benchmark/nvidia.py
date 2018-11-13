import itertools
import os
import subprocess

from cached_property import cached_property

from hpcbench.api import Benchmark, Metrics, MetricsExtractor
from hpcbench.toolbox.functools_ext import listify
from hpcbench.toolbox.process import find_executable


@listify
def get_devices(executable='deviceQuery'):
    dq = find_executable(executable)
    output = subprocess.check_output(dq)
    for line in output.splitlines():
        if line.startswith('Device '):  # Device 0: "Tesla K20m"
            device = line.split(':', 1)[0]  # Device 0
            yield int(device.split(' ')[-1])


class NvidiaP2pBandwidthLatencyTestExtractor(MetricsExtractor):
    OPERATIONS = {
        'Unidirectional P2P=Disabled Bandwidth Matrix (GB/s)': (
            'unidirectional_bandwidth',
            Metrics.MegaBytesPerSecond,
            1024,
        ),
        'Unidirectional P2P=Enabled Bandwidth Matrix (GB/s)': (
            'p2p_unidirectional_bandwidth',
            Metrics.MegaBytesPerSecond,
            1024,
        ),
        'Bidirectional P2P=Disabled Bandwidth Matrix (GB/s)': (
            'bidirectional_bandwidth',
            Metrics.MegaBytesPerSecond,
            1024,
        ),
        'Bidirectional P2P=Enabled Bandwidth Matrix (GB/s)': (
            'p2p_bidirectional_bandwidth',
            Metrics.MegaBytesPerSecond,
            1024,
        ),
        'P2P=Disabled Latency Matrix (us)': ('latency', Metrics.Microsecond, 1.0),
        'P2P=Enabled Latency Matrix (us)': ('p2p_latency', Metrics.Microsecond, 1.0),
    }

    @cached_property
    @listify(wrapper=dict)
    def metrics(self):
        operations = NvidiaP2pBandwidthLatencyTestExtractor.OPERATIONS.values()
        for metric, unit, _ in operations:
            yield (metric, unit)

    @listify(wrapper=dict)
    def extract_metrics(self, metas):
        with open(self.stdout) as istr:
            while True:
                try:
                    line = next(istr)
                except StopIteration:
                    break
                line = line.strip()
                metric = self.OPERATIONS.get(line)
                if metric:
                    next(istr)  # skip
                    value = max(
                        self._get_nth_float(next(istr), 3),
                        self._get_nth_float(next(istr), 2),
                    )
                    factor = metric[2]
                    yield metric[0], value * factor

    def _get_nth_float(self, line, n):
        word = line.lstrip().split()[n - 1]
        return float(word)


class NvidiaBandwidthTestExtractor(MetricsExtractor):
    OPERATIONS = dict(
        H2D='host_to_device_bandwidth',
        D2H='device_to_host_bandwidth',
        D2D='device_to_device_bandwidth',
    )

    @cached_property
    @listify(wrapper=dict)
    def metrics(self):
        for op, label in NvidiaBandwidthTestExtractor.OPERATIONS.items():
            yield label, Metrics.MegaBytesPerSecond

    @listify(wrapper=dict)
    def extract_metrics(self, metas):
        eax = {}
        with open(self.stdout) as istr:
            skip_content = True
            for line in istr:
                if skip_content:
                    if line.startswith('.............'):
                        skip_content = False
                    continue
                if line.startswith('bandwidthTest-'):
                    NvidiaBandwidthTestExtractor._read_line(eax, line)
        return eax

    @classmethod
    def _read_line(cls, metrics, line):
        def operation():
            op = line.split(',', 1)[0]
            return op.split('-')[1]

        def bandwidth():
            value = line.split(',', 2)[1]  # Bandwidth = 382.1 MB/s
            value = value.split(' = ', 1)[1]  # 382.1 MB/s
            value = value.split(' ', 1)[0]  # 382.1
            return float(value)

        metric = cls.OPERATIONS[operation()]
        metrics[metric] = max(metrics.setdefault(metric, 0), bandwidth())


class NvidiaP2pBandwidthLatencyTest(Benchmark):
    """Compute latency and bandwidth of devices with and without Peer-To-Peer
    """

    DEFAULT_EXECUTABLE = 'p2pBandwidthLatencyTest'
    DEFAULT_DEVICEQUERY_EXECUTABLE = 'deviceQuery'
    CATEGORY = 'gpu'

    name = 'p2pBandwidthLatencyTest'

    @cached_property
    def executable(self):
        """Path to bandwidthTest executable"""
        return self.attributes['executable']

    @cached_property
    def devicequery_executable(self):
        """Path to deviceQuery Nvidia utility"""
        return self.attributes['devicequery_executable']

    @property
    def devices(self):
        devices = os.environ.get('CUDA_VISIBLE_DEVICES')
        if devices is None:
            devices = get_devices(self.devicequery_executable)
        else:
            devices = [int(dev) for dev in devices.split(',')]
        return devices

    def __init__(self):
        super(NvidiaP2pBandwidthLatencyTest, self).__init__(
            attributes=dict(
                executable=self.DEFAULT_EXECUTABLE,
                devicequery_executable=self.DEFAULT_DEVICEQUERY_EXECUTABLE,
            )
        )

    @property
    def device_pairs(self):
        if len(self.devices) == 2:
            return [self.devices]
        else:
            return itertools.combinations(self.devices, 2)

    def execution_matrix(self, context):
        del context  # unused
        for dev1, dev2 in self.device_pairs:
            yield dict(
                category=NvidiaP2pBandwidthLatencyTest.CATEGORY,
                command=[find_executable(self.executable)],
                metas=dict(device1=dev1, device2=dev2),
                environment=dict(CUDA_VISIBLE_DEVICES="%s,%s" % (dev1, dev2)),
            )

    @cached_property
    def metrics_extractors(self):
        return NvidiaP2pBandwidthLatencyTestExtractor()


class NvidiaBandwidthTest(Benchmark):
    """measure the memcopy bandwidth of the GPU and memcpy bandwidth across PCI-e
    """

    DEFAULT_EXECUTABLE = 'bandwidthTest'
    DEFAULT_DEVICE = 0
    DEFAULT_MODE = 'shmoo'
    CATEGORY = 'gpu'

    name = 'nvidia-bandwidthtest'

    def __init__(self):
        super(NvidiaBandwidthTest, self).__init__(
            attributes=dict(
                executable=NvidiaBandwidthTest.DEFAULT_EXECUTABLE,
                device=NvidiaBandwidthTest.DEFAULT_DEVICE,
                mode=NvidiaBandwidthTest.DEFAULT_MODE,
            )
        )

    @cached_property
    def executable(self):
        """Path to bandwidthTest executable"""
        return self.attributes['executable']

    @property
    def device(self):
        """GPU device identifier"""
        return self.attributes['device']

    @cached_property
    def options(self):
        """Additional optional command line arguments"""
        return self.attributes.get('options', [])

    @cached_property
    def mode(self):
        """Computation mode"""
        return self.attributes['mode']

    def execution_matrix(self, context):
        del context  # unused
        yield dict(
            category=NvidiaBandwidthTest.CATEGORY,
            command=self._command,
            metas=dict(device=int(self.device)),
        )

    @property
    def _command(self):
        cmd = [
            find_executable(self.executable, required=False),
            '--device',
            str(self.device),
            '--mode',
            self.mode,
        ] + self.options
        if '--csv' not in self.options:
            cmd.append('--csv')
        return cmd

    @cached_property
    def metrics_extractors(self):
        return NvidiaBandwidthTestExtractor()
