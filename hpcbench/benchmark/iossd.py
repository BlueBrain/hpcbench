"""IO SSD Bandwidth measurement using linux tool
   WRITE: sync; dd if=/dev/zero of=tempfile bs=1M count=1024; sync
   FLASH THE CASH: sudo /sbin/sysctl -w vm.drop_caches=3
   READ: dd if=tempfile of=/dev/null bs=1M count=1024

"""
from abc import abstractmethod
import re

from cached_property import cached_property

from hpcbench.api import (
    Benchmark,
    Metrics,
    MetricsExtractor,
)
from hpcbench.toolbox.process import find_executable


class IOSSDExtractor(MetricsExtractor):
    """Ignore stdout until this line"""
    STDOUT_IGNORE_PRIOR = "1024+0 records out"
    METRICS = dict(
        bandwidth=Metrics.MegaBytesPerSecond,
    )
    METRICS_NAMES = set(METRICS)

    BANDWIDTH = re.compile(
        r'^\s*\d+\s\w+\s\w+\s\w+\s[0-9]*\.?[0-9]+\s\w+\s[(](\d+)'
    )
    @property
    def metrics(self):
        """ The metrics to be extracted.
            This property can not be replaced, but can be mutated as required
        """
        return self.METRICS

    def extract(self, outdir, metas):
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
            self.s_bandwidth.add(float(int(search.group(1))/(1024*1024)))

    def epilog(self):
        metrics = {}
        metrics["bandwidth"] = max(self.s_bandwidth)
        # ensure all metrics have been extracted
        unset_attributes = self.METRICS_NAMES - set(metrics)
        if any(unset_attributes):
            error = \
                'Could not extract some metrics: %s\n' \
                'metrics setted are: %s'
            raise Exception(error % (' ,'.join(unset_attributes),
                                     ' ,'.join(set(metrics))))
        return metrics

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
    DEFAULT_EXECUTABLE = 'to define'
    SSD_READ = 'Read'
    SSD_WRITE = 'Write'
    DEFAULT_CATEGORIES = [
        SSD_WRITE,
        SSD_READ,
    ]

    def __init__(self):
        super(IOSSD, self).__init__(
            attributes=dict(
                data="",
                executable=IOSSD.DEFAULT_EXECUTABLE,
                categories=[
                    IOSSD.SSD_READ,
                    IOSSD.SSD_WRITE,
                ],
            )
        )
    name = 'iossd'

    description = "Provides bandwidth of the ssd"

    @cached_property
    def executable(self):
        """Get absolute path to executable
        """
        return find_executable(self.attributes['executable'])

    @property
    def execution_matrix(self):
        for category in self.attributes['categories']:
            yield dict(
                category=category,
                command=[self.executable, category],
            )

    @cached_property
    def metrics_extractors(self):
        return {
            IOSSD.SSD_READ: IOSSDReadExtractor(),
            IOSSD.SSD_WRITE: IOSSDWriteExtractor(),
        }
