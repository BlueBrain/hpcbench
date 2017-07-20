"""
Provides utilities related to PyYaml
"""
import os


def envvar_constructor(loader, node):
    """Tag constructor to use environment variables in YAML files. Usage:

    - !TAG VARIABLE
        raise while loading the document if variable does not exists
    - !TAG VARIABLE:=DEFAULT_VALUE

    For instance:

        credentials:
            user: !env USER:=root
            group: !env GROUP:= root
    """
    value = loader.construct_python_unicode(node)
    data = value.split(':=', 1)
    if len(data) == 2:
        var, default = data
        return os.environ.get(var, default)
    else:
        return os.environ[value]


def load_all_yaml_constructors():
    import yaml
    yaml.add_constructor(u'!env', envvar_constructor)
