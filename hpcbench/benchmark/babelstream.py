"""https://github.com/UoB-HPC/BabelStream

Usage: ./cuda-stream [OPTIONS]

Options:
  -h  --help               Print the message
      --list               List available devices
      --device     INDEX   Select device at INDEX
  -s  --arraysize  SIZE    Use SIZE elements in the array
  -n  --numtimes   NUM     Run the test NUM times (NUM >= 2)
      --float              Use floats (rather than doubles)
      --triad-only         Only run triad
      --csv                Output as csv table


"""

import csv
import subprocess

from cached_property import cached_property

from hpcbench.api import Benchmark, Metrics, MetricsExtractor
from hpcbench.toolbox.functools_ext import listify
from hpcbench.toolbox.process import find_executable


class BabelStreamExtractor(MetricsExtractor):
    OPERATIONS = {'Copy', 'Mul', 'Add', 'Triad', 'Dot'}
    METRICS = dict(max_mbytes_per_sec=('bandwidth', Metrics.MegaBytesPerSecond))

    @property
    def metrics(self):
        eax = {}
        for metric in BabelStreamExtractor.METRICS.values():
            for op in BabelStreamExtractor.OPERATIONS:
                name = op.lower() + '_' + metric[0]
                eax[name] = metric[1]
        return eax

    @listify(wrapper=dict)
    def extract_metrics(self, metas):
        with open(self.stdout) as istr:
            istr.readline()
            istr.readline()
            reader = csv.DictReader(istr, delimiter=',')
            for row in reader:
                op = row['function']
                for metric, desc in BabelStreamExtractor.METRICS.items():
                    value = float(row[metric])
                    name = op.lower() + '_' + desc[0]
                    yield name, value


class BabelStream(Benchmark):
    """STREAM, for lots of different devices"""

    DEFAULT_EXECUTABLE = 'cuda-stream'
    CATEGORY = 'stream'

    name = 'babelstream'

    def __init__(self):
        super(BabelStream, self).__init__(
            attributes=dict(executable=BabelStream.DEFAULT_EXECUTABLE)
        )

    @property
    def devices(self):
        """List of devices to test
        """
        eax = self.attributes.get('devices')
        if eax is None:
            eax = self._all_devices
        if not isinstance(eax, list):
            eax = [eax]
        return [str(dev) for dev in eax]

    @cached_property
    def executable(self):
        """babel-stream executable to use, "cuda-stream" for instance"""
        return self.attributes['executable']

    @cached_property
    def options(self):
        """Additional optional command line arguments"""
        return self.attributes.get('options', [])

    @property
    @listify
    def _all_devices(self):
        binary = find_executable(self.executable)
        listing_devices = False
        for line in subprocess.check_output([binary, '--list']).splitlines():
            line = line.strip()
            if line == 'Devices:':
                listing_devices = True
                continue
            if listing_devices:
                device = line.split(':', 1)[0]
                yield device

    def execution_matrix(self, context):
        for device in self.devices:
            yield dict(
                category=BabelStream.CATEGORY,
                command=self._command(device),
                metas=dict(device=int(device)),
            )

    def _command(self, device):
        cmd = [
            find_executable(self.executable, required=False),
            '--device',
            device,
        ] + self.options
        if '--csv' not in cmd:
            cmd.append('--csv')
        return cmd

    @cached_property
    def metrics_extractors(self):
        return BabelStreamExtractor()
