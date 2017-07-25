# encoding: utf-8
"""Extra tools for working with functions and callable objects
"""
import functools


def compose(*functions):
    """Define functions composition like f ∘ g ∘ h
    :return: callable object that will perform
    function composition of callables given in argument.
    """
    def _compose2(f, g):  # pylint: disable=invalid-name
        return lambda x: f(g(x))
    return functools.reduce(_compose2, functions, lambda x: x)
