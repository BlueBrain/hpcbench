import re
import sys

from jinja2 import Environment, PackageLoader

ENV = Environment(
    loader=PackageLoader('hpcbench', 'templates'),
)
DEFAULT_TEMPLATE = 'report.tex.jinja'


def tex_escape(text):
    """
        :param text: a plain text message
        :return: the message escaped to appear correctly in LaTeX
    """
    conv = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\^{}',
        '\\': r'\textbackslash{}',
        '<': r'\textless ',
        '>': r'\textgreater ',
    }
    regex = re.compile('|'.join(re.escape(unicode(key)) for key in sorted(conv.keys(), key = lambda item: - len(item))))
    return regex.sub(lambda match: conv[match.group()], text)

ENV.filters['texscape'] = tex_escape


def render(campaign, template=None, ostr=None):
    template = template or DEFAULT_TEMPLATE
    ostr = ostr or sys.stdout
    jinja_template = ENV.get_template(template)
    jinja_template.stream(campaign=campaign).dump(ostr)
