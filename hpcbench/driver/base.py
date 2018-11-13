import datetime
import errno
import logging
import types
from abc import ABCMeta, abstractmethod, abstractproperty
from collections import namedtuple
from functools import wraps
from os import path as osp

import six
import yaml
from cached_property import cached_property

from hpcbench.api import Cluster
from hpcbench.campaign import YAML_REPORT_FILE
from hpcbench.toolbox.collections_ext import nameddict, FrozenList, FrozenDict
from hpcbench.toolbox.contextlib_ext import pushd, Timer
from hpcbench.toolbox.functools_ext import listify


LOGGER = logging.getLogger('hpcbench')
LOCALHOST = 'localhost'
SEQUENCES = (list, FrozenList)
MAPPINGS = (dict, FrozenDict)
ConstraintTag = namedtuple('ConstraintTag', ['name', 'constraint'])


Top = namedtuple('top', ['campaign', 'node', 'logger', 'root', 'name'])
Top.__new__.__defaults__ = (None,) * len(Top._fields)


def write_yaml_report(func):
    """Decorator used in campaign node post-processing
    """

    @wraps(func)
    def _wrapper(*args, **kwargs):
        now = datetime.datetime.now()
        with Timer() as timer:
            data = func(*args, **kwargs)
            if isinstance(data, (SEQUENCES, types.GeneratorType)):
                report = dict(children=list(map(str, data)))
            elif isinstance(data, MAPPINGS):
                report = data
            else:
                raise Exception('Unexpected data type: %s', type(data))
        report['elapsed'] = timer.elapsed
        report['date'] = now.isoformat()
        if "no_exec" not in kwargs and report is not None:
            with open(YAML_REPORT_FILE, 'w') as ostr:
                yaml.dump(report, ostr, default_flow_style=False)
        return report

    return _wrapper


class Enumerator(six.with_metaclass(ABCMeta, object)):
    """Common class for every campaign node"""

    def __init__(self, parent, name=None, logger=None, catch_child_exception=False):
        """
        :keyword catch_child_exception: if True, then
        report exception raised by children but do not
        propagate it upstream.
        """
        self.parent = parent
        self.campaign = parent.campaign
        self.root = parent.root
        self.node = parent.node
        self.name = name
        self.catch_child_exception = catch_child_exception
        if logger:
            self.logger = logger
        elif name:
            self.logger = parent.logger.getChild(name)
        else:
            self.logger = parent.logger

    @abstractmethod
    def child_builder(self, child):
        """Provides callable object returning child instance.
        """
        raise NotImplementedError  # pragma: no cover

    @abstractproperty
    def children(self):
        """Property to be overriden by subclass to provide child objects"""
        raise NotImplementedError  # pragma: no cover

    @cached_property
    def has_children(self):
        return len(self.children) > 0

    @cached_property
    def report(self):
        """Get object report. Content of ``YAML_REPORT_FILE``
        """
        with open(YAML_REPORT_FILE) as istr:
            return nameddict(yaml.safe_load(istr))

    def children_objects(self):
        for child in self._children:
            yield self.child_builder(child)

    @classmethod
    def _add_child_to_report(cls, child):
        try:
            with open(YAML_REPORT_FILE) as istr:
                data = yaml.safe_load(istr)
        except IOError as e:
            if e.errno != errno.ENOENT:
                raise
            data = {}
        data.setdefault('children', []).append(str(child))
        with open(YAML_REPORT_FILE, 'w') as ostr:
            yaml.dump(data, ostr, default_flow_style=False)

    def _call_without_report(self, **kwargs):
        for child in self._children:
            self._add_child_to_report(child)
            child_obj = self.child_builder(child)
            with pushd(
                str(child),
                cleanup=isinstance(child_obj, Enumerator)
                and not child_obj.has_children,
            ):
                try:
                    child_obj(**kwargs)
                except Exception:
                    self.logger.exception('While executing benchmark')
                    if not self.catch_child_exception:
                        raise
                yield child

    @classmethod
    def call_decorator(cls, func):
        """class function that MUST be specified as decorator
        to the `__call__` method overriden by sub-classes.
        """

        @wraps(func)
        def _wrap(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception:
                self.logger.exception('While executing benchmark')
                if not (self.catch_child_exception or False):
                    raise

        return _wrap

    @write_yaml_report
    def __call__(self, **kwargs):
        return self._call_without_report(**kwargs)

    @property
    def _children(self):
        if osp.isfile(YAML_REPORT_FILE):
            return self.report['children']
        return self.children

    def traverse(self):
        """Enumerate children and build associated objects
        """
        builder = self.child_builder
        for child in self._children:
            with pushd(str(child)):
                yield child, builder(child)


class Leaf(Enumerator):
    """Enumerator class for classes at the bottom of the hierarchy
    """

    def child_builder(self, child):
        del child  # unused

    @cached_property
    def children(self):
        return []


class ClusterWrapper(Cluster):
    def __init__(self, network, tag, node):
        self._network = network
        self._tag = tag
        self._node = node

    @property
    def nodes(self):
        return self._network.nodes(self._tag)

    @property
    def node_pairs(self):
        return self._network.node_pairs(self._tag, self._node)

    @property
    @listify
    def tag_node_pairs(self):
        for node in self._network.nodes(self._tag)[:-1]:
            for pair in self._network.node_pairs(self._tag, node):
                yield pair
