# encoding: utf-8
"""Extra tools for working with functions and callable objects
"""
import functools
from itertools import islice


def compose(*functions):
    """Define functions composition like f ∘ g ∘ h
    :return: callable object that will perform
    function composition of callables given in argument.
    """

    def _compose2(f, g):  # pylint: disable=invalid-name
        return lambda x: f(g(x))

    return functools.reduce(_compose2, functions, lambda x: x)


def chunks(iterator, size):
    """Split an iterator into chunks with `size` elements each.
    Warning:
        ``size`` must be an actual iterator, if you pass this a
        concrete sequence will get you repeating elements.
        So ``chunks(iter(range(1000)), 10)`` is fine, but
        ``chunks(range(1000), 10)`` is not.
    Example:
        # size == 2
        >>> x = chunks(iter([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]), 2)
        >>> list(x)
        [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9], [10]]
        # size == 3
        >>> x = chunks(iter([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]), 3)
        >>> list(x)
        [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10]]
    """
    for item in iterator:
        yield [item] + list(islice(iterator, size - 1))


def listify(func=None, wrapper=list):
    """
    A decorator which wraps a function's return value in ``list(...)``.
    Useful when an algorithm can be expressed more cleanly as a generator but
    the function should return an list.
    Example::
        >>> @listify
        ... def get_lengths(iterable):
        ...     for i in iterable:
        ...         yield len(i)
        >>> get_lengths(["spam", "eggs"])
        [4, 4]
        >>>
        >>> @listify(wrapper=tuple)
        ... def get_lengths_tuple(iterable):
        ...     for i in iterable:
        ...         yield len(i)
        >>> get_lengths_tuple(["foo", "bar"])
        (3, 3)
    """

    def _listify_return(func):
        @functools.wraps(func)
        def _listify_helper(*args, **kw):
            return wrapper(func(*args, **kw))

        return _listify_helper

    if func is None:
        return _listify_return
    return _listify_return(func)
