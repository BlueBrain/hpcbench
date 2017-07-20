import collections
import copy
import errno
import os
import os.path as osp

import six
import yaml
from yaml import Loader

from . yaml_ext import load_all_yaml_constructors

load_all_yaml_constructors()


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


def flatten_dict(d, prefix='', sep='.'):
    """In place dict flattening.
    """
    def apply_and_resolve_conflicts(dest, item, prefix):
        for k, v in flatten_dict(item, prefix=prefix, sep=sep).items():
            new_key = k
            i = 2
            while new_key in d:
                new_key = '{key}{sep}{index}'.format(key=k, sep=sep, index=i)
                i += 1
            dest[new_key] = v

    for key in list(d.keys()):
        if any(unicode(prefix)):
            new_key = u'{p}{sep}{key}'.format(p=prefix, key=key, sep=sep)
        else:
            new_key = key
        if isinstance(d[key], (dict, collections.Mapping)):
            apply_and_resolve_conflicts(d, d.pop(key), new_key)
        elif isinstance(d[key], six.string_types):
            d[new_key] = d.pop(key)
        elif isinstance(d[key], (list, collections.Mapping)):
            array = d.pop(key)
            for i in range(len(array)):
                index_key = '{key}{sep}{i}'.format(key=key, sep=sep, i=i)
                while index_key in d:
                    i += 1
                apply_and_resolve_conflicts(d, array[i], index_key)
        else:
            d[new_key] = d.pop(key)
    return d


class hashabledict(dict):
    def __hash__(self):
        flatdict = flatten_dict(copy.deepcopy(self))
        return hash(tuple(sorted(flatdict.items())))
