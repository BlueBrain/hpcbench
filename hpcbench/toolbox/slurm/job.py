import collections
import datetime
import os
import subprocess

from ClusterShell.NodeSet import NodeSet

from ..process import find_executable


SACCT_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'
SACCT = find_executable('sacct', required=False)


class Job(
    collections.namedtuple('Job', ['id', 'exit_code', 'nodes', 'cpus', 'start', 'end'])
):
    @classmethod
    def fromid(cls, jobid):
        environ = dict(os.environ)
        # Override any system-specific time format setting
        environ['SLURM_TIME_FORMAT'] = SACCT_DATE_FORMAT
        output = subprocess.check_output(
            [
                SACCT,
                '-n',
                '-X',
                '-P',
                '-o',
                "Node,NCPUs,ExitCode,Start,End",
                '-j',
                str(jobid),
            ],
            env=environ,
        ).decode()
        nodes, cpus, exit_code, start, end = output.strip().split('|', 5)
        start = datetime.datetime.strptime(start, SACCT_DATE_FORMAT)
        if end == 'Unknown':
            end = datetime.datetime.now()
        else:
            end = datetime.datetime.strptime(end, SACCT_DATE_FORMAT)
        exit_code = exit_code.split(':')[0]
        return cls(
            id=str(jobid),
            nodes=NodeSet(nodes),
            cpus=int(cpus),
            exit_code=int(exit_code),
            start=start,
            end=end,
        )

    @classmethod
    def finished(cls, jobid):
        """Check whether a SLURM job is finished or not"""
        output = subprocess.check_output(
            [SACCT, '-n', '-X', '-o', "end", '-j', str(jobid)]
        )
        end = output.strip().decode()
        return end not in {'Unknown', ''}
