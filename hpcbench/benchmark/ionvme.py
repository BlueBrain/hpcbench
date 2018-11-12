"""IO NVME Bandwidth measurement using linux tool
   WRITE: sync; dd if=/dev/zero of=tempfile bs=1M count=1024; sync
   FLASH THE CASH: sudo /sbin/sysctl -w vm.drop_caches=3
   READ: dd if=tempfile of=/dev/null bs=1M count=1024

"""
from __future__ import division

import os
import re
import stat
import textwrap

from cached_property import cached_property

from hpcbench.api import Benchmark, Metrics, MetricsExtractor


class IONVMEExtractor(MetricsExtractor):
    """Ignore stdout until this line"""

    STDOUT_IGNORE_PRIOR = "1024+0 records out"
    METRICS = dict(bandwidth=Metrics.MegaBytesPerSecond)
    METRICS_NAMES = set(METRICS)

    BANDWIDTH_OSX_RE = re.compile(r'^\s*\d+\s\w+\s\w+\s\w+\s\d*\.?\d+\s\w+\s[(](\d+)')

    def __init__(self):
        self.s_bandwidth = set()

    @property
    def metrics(self):
        """ The metrics to be extracted.
            This property can not be replaced, but can be mutated as required
        """
        return self.METRICS

    def prelude(self):
        self.s_bandwidth.clear()

    def extract_metrics(self, metas):
        # parse stdout and extract desired metrics
        self.prelude()
        with open(self.stderr) as istr:
            for line in istr:
                if line.strip() == self.STDOUT_IGNORE_PRIOR:
                    break
            for line in istr:
                self.process_line(line.strip())
        return self.epilog()

    def process_line(self, line):
        search = self.BANDWIDTH_OSX_RE.search(line)
        if search:
            self.s_bandwidth.add(float(int(search.group(1)) / (1024 * 1024)))
        else:
            # Linux?
            tokens = line.rsplit('s, ', 2)
            if len(tokens) == 2:
                value, unit = tokens[1].split(' ', 2)
                value = float(value)
                bandwidth = IONVMEExtractor.parse_bandwidth_linux(value, unit)
                self.s_bandwidth.add(bandwidth)

    @classmethod
    def parse_bandwidth_linux(cls, value, unit):
        if unit == 'bytes/s':
            value /= 1024
            unit = 'KB/s'
        if unit == 'KB/s':
            value /= 1024
            unit = 'MB/s'
        if unit == 'MB/s':
            return value
        if unit == 'GB/s':
            return value * 1024
        raise Exception('Unexpected unit: "{}"'.format(unit))

    def epilog(self):
        return dict(bandwidth=max(self.s_bandwidth))


class IONVMEWriteExtractor(IONVMEExtractor):
    pass


class IONVMEReadExtractor(IONVMEExtractor):
    pass


class IONVME(Benchmark):
    """Provides NVME bandwidth benchmark
    """

    name = 'ionvme'

    NVME_READ = 'Read'
    NVME_WRITE = 'Write'
    DEFAULT_CATEGORIES = [NVME_WRITE, NVME_READ]

    SCRIPT_NAME = 'ionvme.sh'
    SCRIPT = textwrap.dedent(
        """\
    #!/bin/bash -e

    TESTDIR="${FILE_PATH:-$PWD}"
    mkdir -p "$TESTDIR"
    TEMPFILE="$TESTDIR/tempfile"

    case `uname -s` in
        Darwin)
            NAME=Darwin
            MB=m
            WCONV=sync
            ;;
        *)
            NAME=Linux
            MB=M
            WCONV=fdatasync
    esac

    function benchmark_write {
        echo "Writing benchmark"
        sync
        dd conv=$WCONV if=/dev/zero of="$TEMPFILE" bs=1$MB count=1024
        sync
    }

    function benchmark_read {
        echo "Reading benchmark"
        # flash the ddr to be sure we are using the IO
        # /sbin/sysctl -w vm.drop_caches=3;
        dd if="$TEMPFILE" of=/dev/null bs=1$MB count=1024
    }

    if [ $1 = "Write" ]; then
        benchmark_write
    else
        benchmark_write >/dev/null 2>&1
        if [ $NAME = "Linux" ]; then
            sudo sysctl -w vm.drop_caches=3 >/dev/null 2>&1
        else
            sync && sudo purge 2>&1
        fi
        benchmark_read
    fi
    rm -f "$TEMPFILE"
    """
    )

    def __init__(self):
        super(IONVME, self).__init__(
            attributes=dict(categories=[IONVME.NVME_WRITE, IONVME.NVME_READ], path=None)
        )

    @property
    def categories(self):
        """List of categories to test"""
        return self.attributes['categories']

    def execution_matrix(self, context):
        del context  # unused
        for category in self.categories:
            cmd = dict(category=category, command=['./' + IONVME.SCRIPT_NAME, category])
            if self.path:
                cmd.setdefault('environment', {})['FILE_PATH'] = self.path
                cmd.setdefault('metas', {})['path'] = self.path
            yield cmd

    @cached_property
    def path(self):
        """Custom path the benchmark must be executed into"""
        return self.attributes['path']

    @cached_property
    def metrics_extractors(self):
        return {
            IONVME.NVME_READ: IONVMEReadExtractor(),
            IONVME.NVME_WRITE: IONVMEWriteExtractor(),
        }

    def pre_execute(self, execution):
        del execution  # unused
        with open(IONVME.SCRIPT_NAME, 'w') as ostr:
            ostr.write(IONVME.SCRIPT)
        st = os.stat(IONVME.SCRIPT_NAME)
        os.chmod(IONVME.SCRIPT_NAME, st.st_mode | stat.S_IEXEC)
