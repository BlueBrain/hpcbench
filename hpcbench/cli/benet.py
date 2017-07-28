"""ben-et

Usage:
  ben-et [-v | -vv ] CAMPAIGN_FILE
  ben-et (-h | --help)
  ben-et --version

Options:
  -h --help   Show this screen
  --version   Show version
  -v -vv -vvv Increase program verbosity
"""

from hpcbench.net import BeNet

from . import cli_common


def main(argv=None):
    """ben-et entry point"""
    arguments = cli_common(__doc__, argv=argv)
    benet = BeNet(arguments['CAMPAIGN_FILE'])
    benet.run()
    if argv is not None:
        return benet


if __name__ == '__main__':
    main()
