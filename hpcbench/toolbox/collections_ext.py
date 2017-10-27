"""Extra collections utilities
"""
import collections
import copy
import errno
import os
import os.path as osp
import sys

import six
import yaml


class nameddict(dict):  # pragma pylint: disable=invalid-name
    """ Provides dictionary whose keys are accessible via the property
    syntax: `obj.key`
    """
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.__dict__ = self
        self.__namify(self.__dict__)

    @classmethod
    def __namify(cls, a_dict):
        for key in a_dict.keys():
            if isinstance(a_dict[key], dict):
                a_dict[key] = nameddict(a_dict[key])

    def __setitem__(self, key, value):
        if isinstance(value, dict):
            value = nameddict(value)
        super(nameddict, self).__setitem__(key, value)

    def __setattr__(self, key, value):
        if key != '__dict__' and isinstance(value, dict):
            value = nameddict(value)
        super(nameddict, self).__setattr__(key, value)

    def __deepcopy__(self, memo):
        cls = self.__class__
        content = dict()
        for key, value in self.items():
            content[key] = copy.deepcopy(value, memo)
        result = cls.__new__(cls)
        result.__init__(content)
        return result


class Configuration(nameddict):
    """nameddict reflecting a YAML file
    """
    @classmethod
    def from_file(cls, path):
        """Create a ``Configuration`` from a file

        :param path: path to YAML file
        :return: new configuration
        :rtype: ``Configuration``
        """
        if path == '-':
            return Configuration(yaml.safe_load(sys.stdin))
        if not osp.exists(path) and not osp.isabs(path):
            path = osp.join(osp.dirname(osp.abspath(__file__)), path)
        with open(path, 'r') as istr:
            return Configuration(yaml.safe_load(istr))

    @classmethod
    def from_env(cls, envvars, default, default_config):
        """Create a ``Configuration``

        :param envvars: list of environment variable name where to look
        for a YAML filename
        :param default: default path to YAML file if not found in ``envvars``
        :param default_config: Default ``Configuration`` if not found
        in above methods.
        :return: new configuration
        :rtype: ``Configuration``
        """
        try:
            if isinstance(envvars, six.string_types):
                envvars = [envvars]
            config_file = default
            for envvar in envvars:
                envvalue = os.getenv(envvar)
                if envvalue is not None:
                    config_file = envvalue
                    break
            config = Configuration.from_file(config_file)
        except IOError as exc:
            if exc.errno in [errno.ENOENT, errno.ENOTDIR]:
                config = default_config
            else:
                raise
        return config


def flatten_dict(dic, parent_key='', sep='.'):
    """Flatten sub-keys of a dictionary
    """
    items = []
    for key, value in dic.items():
        new_key = parent_key + sep + key if parent_key else key
        if isinstance(value, collections.MutableMapping):
            items.extend(flatten_dict(value, new_key, sep=sep).items())
        else:
            items.append((new_key, value))
    return dict(items)


def dict_merge(dct, merge_dct):
    """ Recursive dict merge. Inspired by :meth:``dict.update()``, instead of
    updating only top-level keys, dict_merge recurses down into dicts nested
    to an arbitrary depth, updating keys. The ``merge_dct`` is merged into
    ``dct``.
    :param dct: dict onto which the merge is executed
    :param merge_dct: dct merged into dct
    :return: None
    """
    for key in merge_dct.keys():
        if (key in dct and isinstance(dct[key], dict)
                and isinstance(merge_dct[key], collections.Mapping)):
            dict_merge(dct[key], merge_dct[key])
        else:
            dct[key] = merge_dct[key]


def dict_map_kv(obj, func):
    if isinstance(obj, collections.Mapping):
        return {
            func(k): dict_map_kv(v, func)
            for k, v in six.iteritems(obj)
        }
    elif isinstance(obj, list):
        return [dict_map_kv(e, func) for e in obj]
    else:
        return func(obj)
