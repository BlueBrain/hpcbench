"""hpcbench package to specify and execute benchmarks
"""
from jinja2 import Environment, PackageLoader, select_autoescape
from pkg_resources import get_distribution

__version__ = get_distribution(__name__).version

jinja_environment = Environment(
    loader=PackageLoader('hpcbench', 'templates'),
    autoescape=select_autoescape(
        disabled_extensions=('txt',), default_for_string=False, default=False
    ),
)
