"""Provide metaclass to allow top-hierarchy classes
to access its subclasses
"""

__all__ = [
    'ClassRegistrar'
]


class ClassLibrary(object):
    """ClassRegistrar modify top-level classes so that they extend
    this class.

    This class should not used directly
    """
    @classmethod
    def get_subclass(cls, name):
        """Get a subclass

        :param name: Name of the class to retrieve
        """
        return cls.SUB_CLASSES[name]  # pylint: disable=no-member

    @classmethod
    def get_subclasses(cls):
        """Get list of available classes
        :return: list of class names
        :rtype: list of string
        """
        for clazz in cls.SUB_CLASSES:  # pylint: disable=no-member
            yield clazz

    @classmethod
    def register_subclass(cls, clazz):
        """Register a subclass

        :param clazz: Class to register
        """
        name = getattr(clazz, 'name', clazz.__name__)
        classes = cls.SUB_CLASSES  # pylint: disable=no-member
        if name in classes:
            raise Exception('class %s is already registered' % name)
        classes[name] = clazz


class ClassRegistrar(type):
    """Metaclass that can be specified on top-hierarchy classes
    to track their subclasses.

    Usage:

    >>> class Foo(object):
            __metaclass__ = ClassRegistrar
    >>>    class Bar(Foo): pass
    >>> Foo.get_subclass('Bar')
    <class '__main__.Foo'>

    A custom name can be specified:

    >>> class EmbarassingClassName(Foo):
            name = "awesome-class"
    >>> Foo.get_subclass('awesome-class')
    <class '__main__.EmbarassingClassName'>
    """
    def __new__(mcs, name, bases, attrs):
        if not bases or bases == (object,):
            attrs['SUB_CLASSES'] = {}
            bases = (ClassLibrary,) + bases
        cls = type.__new__(mcs, name, bases, attrs)
        cls.register_subclass(cls)
        return cls
