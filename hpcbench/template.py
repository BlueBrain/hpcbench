import os.path as osp
import shutil

from cookiecutter import exceptions
from cookiecutter.main import cookiecutter


def plugins_dir():
    return osp.join(osp.dirname(__file__), 'templates', 'plugins')


def plugin_path(name):
    return osp.join(plugins_dir(), name)


def config_path(name):
    return osp.join(plugin_path(name), 'cookiecutter.json')


def has_plugin(name):
    return osp.isfile(config_path(name))


def ensure_exists(name):
    if not has_plugin(name):
        raise Exception('Unknown plugin: ' + name)


def generate_config(name, path):
    ensure_exists(name)
    shutil.copy(config_path(name), path)


def generate_template(name, **kwargs):
    ensure_exists(name)
    try:
        cookiecutter(plugin_path(name), **kwargs)
    except exceptions.FailedHookException:
        return False
