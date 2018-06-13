# encoding: utf-8
"""
Provides Python Embedded Domain Specific Languages.
"""
from collections import Mapping, Sequence
import functools
import operator

__all__ = ['kwargsql']


class AnySequenceResult(Sequence):
    """Custom list used internally to distinguish
    a list of user-data from a user-data-list with the `isinstance`
    builtin.
    """

    def __init__(self, data, join_operation):
        self.__data = data
        self.join_operation = join_operation

    def __len__(self):
        return len(self.__data)

    def __getitem__(self, key):
        return self.__data[key]


class kwargsql(object):  # pragma pylint: disable=invalid-name
    """Query your Python objects with a `kwargs` syntax.

    Syntax looks like the Mongoengine syntax to query documents.

    Keys in the keyword argument specifies:

    - the attribute's location to test
    - the operation to perform, returning either `True` or `False`
      - first operand is the attribute value
      - second operand if the associated key value.

    For instance:
    - foo=42
    - foo__lt=43

    An extra `not` operator can be specified before the operation,
    for instance: foo__not__gt=0

    To access nested attributes, you can use the '__' separator,
    for instance "foo__bar". This syntax allows you to select:
        - an object attribute
        - value associated to a key in a `dict`.

    It is also possible to select an item of a list, by providing
    the position.


    Example:

    >>> d = {
    >>>    'foo': [
    >>>        { 'bar': 'pika' },
    >>>        { 'bar': 42 },
    >>>    ],
    >>> }
    >>> kwargsql.and_(d, foo__1__bar_gt=41, foo__size=2)
    True
    >>>

    Available operators are as follows:

    ne – not equal to
    lt – less than
    lte – less than or equal to
    gt – greater than
    gte – greater than or equal to
    not – negate a standard check, may be used before other operators
          (e.g. Q(age__not__mod=5))
    in – value is in list (a list of values should be provided)
    nin – value is not in list (a list of values should be provided)
    size – the size of the array, dict, or string is
    exists – value for field exists

    iexact – string field exactly matches value (case insensitive)
    contains – string field contains value
    icontains – string field contains value (case insensitive)
    startswith – string field starts with value
    istartswith – string field starts with value (case insensitive)
    endswith – string field ends with value
    iendswith – string field ends with value (case insensitive)

    isinstance – same as isinstance(field, value)
    issubclass – same as issubclass(field, value)

    any – applies the remaining kwargsql expression to every elements
          of a sequence. The result is `True` if the operation is `True`
          for at least one element.

    each – applies the remaining kwargsql expression to every elements
           of a sequence. The result is `True` if the operation is `True`
           for every element of the sequence.
    """

    OPERATIONS = {
        'ne': operator.ne,
        'lt': operator.lt,
        'lte': operator.le,
        'gt': operator.gt,
        'gte': operator.ge,
        'in': lambda e, c: e in c,
        'nin': lambda e, c: e not in c,
        'size': lambda c, e: len(c) == e,
        'exists': lambda e, cond: e is not None if cond else e is None,
        'iexact': lambda s, e: str(s).lower() == e.lower(),
        'contains': lambda s, e: e in s,
        'icontains': lambda s, e: str(e).lower() in s.lower(),
        'startswith': lambda s, e: str(s).startswith(e),
        'istartswith': lambda s, e: str(s).lower().startswith(e.lower()),
        'endswith': lambda s, e: str(s).endswith(e),
        'iendswith': lambda s, e: str(s).lower().endswith(e.lower()),
        'isinstance': isinstance,
        'issubclass': issubclass,
    }

    SEQUENCE_OPERATIONS = dict(any=operator.or_, each=operator.and_)

    @classmethod
    def and_(cls, obj, **kwargs):
        """Query an object

        :param obj:
          object to test

        :param kwargs: query specified in kwargssql

        :return:
          `True` if all `kwargs` expression are `True`, `False` otherwise.
        :rtype: bool
        """
        return cls.__eval_seqexp(obj, operator.and_, **kwargs)

    @classmethod
    def or_(cls, obj, **kwargs):
        """Query an object

        :param obj:
          object to test

        :param kwargs: query specified in kwargssql

        :return:
          `True` if at leat one `kwargs` expression is `True`,
          `False` otherwise.
        :rtype: bool
        """
        return cls.__eval_seqexp(obj, operator.or_, **kwargs)

    @classmethod
    def xor(cls, obj, **kwargs):
        """Query an object.

        :param obj:
          object to test

        :param kwargs: query specified in kwargssql

        :return:
          `True` if exactly one `kwargs` expression is `True`,
          `False` otherwise.
        :rtype: bool
        """
        return cls.__eval_seqexp(obj, operator.xor, **kwargs)

    @classmethod
    def get(cls, obj, expr):
        """Parse a kwargsql string expression, and return
        the target value in given object.

        Not sure if really needed, except when using kwargsql
        expressions in YAML files for instance.

        :param obj:
          navigation starting point

        :param basestring expr:
          kwargsql expression.

        :return:
          object pointed out by the expression.
        """
        return cls.__resolve_path(obj, expr.split('__'))

    @classmethod
    def _get_operation(cls, opname):
        """Get operation from its name.
        You can override this class method to provide additional
        operations.

        :param basestring opname:
          operation name

        :return:
          binary operator if found, `None` otherwise
        :rtype: callable object
        """
        return cls.OPERATIONS.get(opname)

    @classmethod
    def __resolve_path(cls, obj, path):
        """Follow a kwargsql expression starting from a given object
        and return the deduced object.

        :param obj: the object to start from
        :param list path: list of operations to perform. It does not contain
                          the optional operation of a traditional kwargsql
                          expression.
        :return: the found object if any, `None` otherwise.

        For instance:
        >>> __resolve_path(dict(foo=dict(bar=42)), ['foo', 'bar'])
        >>> 42

        """
        path = [p for p in path if p]
        if any(path):
            pathes = len(path)
            i = 0
            while i < pathes:
                # _get_obj_attr can supersede `i` because it might
                # evaluate the entire expression by itself.
                obj, i = cls._get_obj_attr(obj, path, i)
                i += 1
        else:
            raise Exception("Nothing to do")
        return obj

    @classmethod
    def __eval_seqexp(cls, obj, operation, **kwargs):
        return functools.reduce(
            operation,
            [cls._eval_exp(obj, exp, value) for (exp, value) in kwargs.items()],
        )

    @classmethod
    def _get_obj_attr(cls, obj, path, pos):
        """Resolve one kwargsql expression for a given object and returns
        its result.

        :param obj: the object to evaluate
        :param path: the list of all kwargsql expression, including those
                     previously evaluated.
        :param int pos: provides index of the expression to evaluate in the
                        `path` parameter.
        """
        field = path[pos]
        if isinstance(obj, (dict, Mapping)):
            return obj[field], pos
        elif isinstance(obj, (list, Sequence)):
            join_operation = cls.SEQUENCE_OPERATIONS.get(field)
            if join_operation is not None:
                return (
                    AnySequenceResult(
                        cls._sequence_map(obj, path[pos + 1 :]), join_operation
                    ),
                    len(path) + 1,
                )
            return obj[int(field)], pos
        return getattr(obj, field, None), pos

    @classmethod
    def _sequence_map(cls, seq, path):
        """Apply a kwargsql expression to every item of a sequence,
        and returns it.

        :param seq: the list to transform
        :param path: kwargsql expression to apply to every elements of
                     the given sequence.
        """
        if not any(path):
            # There is no further kwargsql expression
            return seq
        result = []
        for item in seq:
            try:
                result.append(cls.__resolve_path(item, path))
            except (KeyError, IndexError):
                pass
        return result

    @classmethod
    def _not(cls, operation):
        """not operation"""

        def _wrap(*args, **kwargs):
            return not operation(*args, **kwargs)

        return _wrap

    @classmethod
    def _eval_exp(cls, obj, exp, value):
        operation = operator.eq
        tokens = exp.split('__')[::-1]
        _op = cls._get_operation(tokens[0])
        if _op is not None:
            # this is the operator
            operation = _op
            tokens = tokens[1:]
        if tokens[0] == 'not':
            operation = cls._not(operation)
            tokens = tokens[1:]
        try:
            computed = cls.__resolve_path(obj, reversed(tokens))
        except (KeyError, IndexError):
            computed = None
        if isinstance(computed, AnySequenceResult):
            data = [operation(item, value) for item in computed]
            if any(data):
                return functools.reduce(computed.join_operation, data)
            return False
        else:
            return operation(computed, value)
