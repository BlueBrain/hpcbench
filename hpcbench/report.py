"""Generate reports with Jinja templating library from campaign results
"""
import re
import sys

from jinja2 import Environment, PackageLoader
import six


ENV = Environment(
    loader=PackageLoader('hpcbench', 'templates'),
)
DEFAULT_TEMPLATE = 'report.tex.jinja'


def tex_escape(text):
    """Escape string for LaTeX usage
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
    regex = re.compile(
        '|'.join(
            re.escape(six.text_type(key))
            for key in sorted(
                conv.keys(),
                key=lambda item: - len(item)
            )
        )
    )
    return regex.sub(lambda match: conv[match.group()], text)


ENV.filters['texscape'] = tex_escape


def render(campaign_driver, template=None, ostr=None):
    """Generate report from a campaign

    :param campaign_driver: instance of ``hpcbench.driver.CampaignDriver``
    :param template: Jinja template to use, ``DEFAULT_TEMPLATE`` is used
    if not specified
    :param ostr: output file or filename. Default is standard output
    """
    template = template or DEFAULT_TEMPLATE
    ostr = ostr or sys.stdout
    jinja_template = ENV.get_template(template)
    jinja_template.stream(campaign=campaign_driver).dump(ostr)
