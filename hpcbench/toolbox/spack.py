from subprocess import check_call, check_output

from .process import find_executable


class SpackCmd:
    @property
    def spack(self):
        return find_executable('spack', required=False)

    def install(self, *args):
        self.cmd('install', '--show-log-on-error', '--verbose', *args)

    def install_dir(self, *args):
        output = self.cmd('location', '--install-dir', *args, output=True)
        return output.strip().decode('utf-8')

    def cmd(self, *args, **kwargs):
        command = [self.spack] + list(args)
        if kwargs.get('output', False):
            func = check_output
        else:
            func = check_call
        return func(command)
