import collections
import csv
import re
import subprocess

from cached_property import cached_property

from .. functools_ext import listify
from .. process import find_executable


SINFO = find_executable('sinfo', required=False)


class SlurmCluster:
    def __init__(self, partitions=None):
        self.partitions = partitions or self.__class__.discover_partitions()

    @cached_property
    @listify()
    def nodes(self):
        for partition_nodes in self.partitions.values():
            for node in partition_nodes:
                yield node

    @classmethod
    def discover_partitions(cls):
        command = [SINFO, '--Node', '--format', '%all']
        output = subprocess.check_output(command)
        reader = csv.DictReader(output.splitlines(), delimiter='|')
        sanitizer_re = re.compile('[^0-9a-zA-Z]+')

        def sanitize(field):
            return sanitizer_re.sub('_', field.strip()).lower()
        commasplit_fields = {'available_features', 'active_features'}
        int_fields = {
            'sockets', 'cpus', 'prio_tier', 'threads', 'cores', 'nodes',
            'tmp_disk', 'weigth', 'free_mem', 'prio_job_factor', 'memory'
        }
        float_fields = {'cpu_load'}
        reader.fieldnames = [sanitize(field) for field in reader.fieldnames]

        class Node(collections.namedtuple('Node', set(reader.fieldnames))):
            @property
            def name(self):
                return self.hostnames

            def __str__(self):
                return self.name

        partitions = dict()
        for row in reader:
            for key in row:
                row[key] = row[key].strip()
                conv_type = None
                if key in commasplit_fields:
                    row[key] = row[key].split()
                elif key in int_fields:
                    conv_type = int
                elif key in float_fields:
                    conv_type = float
                if conv_type:
                    try:
                        row[key] = conv_type(row[key])
                    except ValueError:
                        pass
            partitions.setdefault(row['partition'], []).append(Node(**row))
        return partitions
