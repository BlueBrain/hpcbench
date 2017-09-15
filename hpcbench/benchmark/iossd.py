"""IO SSD Bandwidth measurement using linux tool
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

from hpcbench.api import (
    Benchmark,
    Metrics,
    MetricsExtractor,
)


class IOSSDExtractor(MetricsExtractor):
    """Ignore stdout until this line"""
    STDOUT_IGNORE_PRIOR = "1024+0 records out"
    METRICS = dict(
        bandwidth=Metrics.MegaBytesPerSecond,
    )
    METRICS_NAMES = set(METRICS)

    BANDWIDTH = re.compile(r'^\s*\d+\s\w+\s\w+\s\w+\s\d*\.?\d+\s\w+\s[(](\d+)')

    @property
    def metrics(self):
        """ The metrics to be extracted.
            This property can not be replaced, but can be mutated as required
        """
        return self.METRICS

    def extract_metrics(self, outdir, metas):
        # parse stdout and extract desired metrics
        with open(self.stdout(outdir)) as istr:
            for line in istr:
                if line.strip() == self.STDOUT_IGNORE_PRIOR:
                    break
            for line in istr:
                self.process_line(line.strip())
        return self.epilog()

    def process_line(self, line):
        search = self.BANDWIDTH.search(line)
        if search:
            self.s_bandwidth.add(float(int(search.group(1)) / (1024 * 1024)))

    def epilog(self):
        return dict(bandwidth=max(self.s_bandwidth))


class IOSSDWriteExtractor(IOSSDExtractor):
    def __init__(self):
        super(IOSSDWriteExtractor, self).__init__()
        self.s_bandwidth = set()


class IOSSDReadExtractor(IOSSDExtractor):
    def __init__(self):
        super(IOSSDReadExtractor, self).__init__()
        self.s_bandwidth = set()


class IOSSD(Benchmark):
    """Benchmark wrapper for the SSDIObench utility
    """

    name = 'iossd'

    description = "Provides SSD bandwidth"

    SSD_READ = 'Read'
    SSD_WRITE = 'Write'
    DEFAULT_CATEGORIES = [
        SSD_WRITE,
        SSD_READ,
    ]

    SCRIPT_NAME = 'iossd.sh'
    SCRIPT = textwrap.dedent("""\
    #!/bin/bash
    #mac: 1m, linux 1M

    function benchmark_write {
        echo "Writing benchmark"
        sync; dd if=/dev/zero of=tempfile bs=1m count=1024; sync
    }

    function benchmark_read {
        echo "Reading benchmark"
        # flash the ddr to be sure we are using the IO
        # /sbin/sysctl -w vm.drop_caches=3;
        dd if=/dev/zero of=tempfile bs=1m count=1024
    }

    if [ $1 = "Write" ]; then
        benchmark_write
    else
        benchmark_read
    fi
    """)

    def __init__(self):
        super(IOSSD, self).__init__(
            attributes=dict(
                categories=[
                    IOSSD.SSD_READ,
                    IOSSD.SSD_WRITE,
                ],
            )
        )

    @property
    def execution_matrix(self):
        for category in self.attributes['categories']:
            yield dict(
                category=category,
                command=['./' + IOSSD.SCRIPT_NAME, category],
            )

    @cached_property
    def metrics_extractors(self):
        return {
            IOSSD.SSD_READ: IOSSDReadExtractor(),
            IOSSD.SSD_WRITE: IOSSDWriteExtractor(),
        }

    def pre_execute(self, execution):
        del execution  # unused
        with open(IOSSD.SCRIPT_NAME, 'w') as ostr:
            ostr.write(IOSSD.SCRIPT)
        st = os.stat(IOSSD.SCRIPT_NAME)
        os.chmod(IOSSD.SCRIPT_NAME, st.st_mode | stat.S_IEXEC)
