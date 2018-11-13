import collections
import datetime
import csv
import logging
import re
import subprocess

from cached_property import cached_property
from ClusterShell.NodeSet import NodeSet

from ..functools_ext import listify
from ..process import find_executable


RESERVATION_FIELDS = ['name', 'state', 'start', 'end', 'duration', 'nodes']
SINFO = find_executable('sinfo', required=False)
SINFO_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S'
SINFO_ENV = dict(SINFO_TIME_FORMAT=SINFO_TIME_FORMAT)


class Reservation(collections.namedtuple('Reservation', RESERVATION_FIELDS)):
    @property
    def active(self):
        return self.state == 'ACTIVE'

    @classmethod
    def from_sinfo(cls, output):
        fields = output.split()
        return cls(
            name=fields[0],
            state=fields[1],
            start=datetime.datetime.strptime(fields[2], SINFO_TIME_FORMAT),
            end=datetime.datetime.strptime(fields[3], SINFO_TIME_FORMAT),
            duration=fields[4],
            nodes=NodeSet(fields[5]),
        )


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
    def reservation(cls, name):
        """get nodes of a given reservation"""
        return cls.reservations()[name]

    @classmethod
    @listify(wrapper=dict)
    def reservations(self):
        """get nodes of every reservations"""
        command = [SINFO, '--reservation']
        output = subprocess.check_output(command, env=SINFO_ENV)
        output = output.decode()
        it = iter(output.splitlines())
        next(it)
        for line in it:
            rsv = Reservation.from_sinfo(line)
            yield rsv.name, rsv

    @classmethod
    def discover_partitions(cls):
        command = [SINFO, '--Node', '--format', '%all']
        try:
            output = subprocess.check_output(command, env=SINFO_ENV)
        except OSError:
            logging.exception('Could not extract cluster information')
            return dict()
        reader = csv.DictReader(output.decode().splitlines(), delimiter='|')
        sanitizer_re = re.compile('[^0-9a-zA-Z]+')

        def sanitize(field):
            return sanitizer_re.sub('_', field.strip()).lower()

        commasplit_fields = {'available_features', 'active_features'}
        int_fields = {
            'sockets',
            'cpus',
            'prio_tier',
            'threads',
            'cores',
            'nodes',
            'tmp_disk',
            'weigth',
            'free_mem',
            'prio_job_factor',
            'memory',
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
                    row[key] = row[key].split(',')
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
