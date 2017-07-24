import collections
import copy
import errno
import os
import os.path as osp

import six
import yaml
from yaml import Loader


class nameddict(dict):
    """ Provides dictionary whose keys are accessible via the property
    syntax: `obj.key`
    """
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.__dict__ = self
        self.__namify(self.__dict__)

    def __namify(self, a_dict):
        for key in a_dict.keys():
            if type(a_dict[key]) == dict:
                a_dict[key] = nameddict(a_dict[key])

    def __setitem__(self, key, value):
        if type(value) == dict:
            value = nameddict(value)
        super(nameddict, self).__setitem__(key, value)

    def __setattr__(self, key, value):
        if key != '__dict__' and type(value) == dict:
            value = nameddict(value)
        super(nameddict, self).__setattr__(key, value)

    def __deepcopy__(self, memo):
        cls = self.__class__
        content = dict()
        for k, v in self.iteritems():
            content[k] = copy.deepcopy(v, memo)
        result = cls.__new__(cls)
        result.__init__(content)
        return result


class Configuration(nameddict):
    @classmethod
    def from_file(cls, path):
        if not osp.exists(path) and not osp.isabs(path):
            path = osp.join(osp.dirname(osp.abspath(__file__)), path)
        with open(path, 'r') as istr:
            return Configuration(yaml.load(istr, Loader=Loader))

    @classmethod
    def from_env(cls, envvars, default, default_config):
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
        except IOError as e:
            if e.errno in [errno.ENOENT, errno.ENOTDIR]:
                config = default_config
            else:
                raise
        return config


def flatten_dict(d, parent_key='', sep='.'):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.MutableMapping):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)
