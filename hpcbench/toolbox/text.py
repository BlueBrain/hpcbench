import os


def get_last_traceback():
    """Retrieve the last traceback as an `unicode` string."""
    import traceback
    from StringIO import StringIO
    tb = StringIO()
    traceback.print_exc(file=tb)
    return to_unicode(tb.getvalue())


def to_unicode(text, charset=None):
    """Convert input to an `unicode` object.
    For a `str` object, we'll first try to decode the bytes using the given
    `charset` encoding (or UTF-8 if none is specified), then we fall back to
    the latin1 encoding which might be correct or not, but at least preserves
    the original byte sequence by mapping each byte to the corresponding
    unicode code point in the range U+0000 to U+00FF.
    For anything else, a simple `unicode()` conversion is attempted,
    with special care taken with `Exception` objects.
    """
    if isinstance(text, str):
        try:
            return unicode(text, charset or 'utf-8')
        except UnicodeDecodeError:
            return unicode(text, 'latin1')
    elif isinstance(text, Exception):
        if os.name == 'nt' and \
                isinstance(text, (OSError, IOError)):  # pragma: no cover
            # the exception might have a localized error string encoded with
            # ANSI codepage if OSError and IOError on Windows
            try:
                return unicode(str(text), 'mbcs')
            except UnicodeError:
                pass
        # two possibilities for storing unicode strings in exception data:
        try:
            # custom __str__ method on the exception (e.g. PermissionError)
            return unicode(text)
        except UnicodeError:
            # unicode arguments given to the exception (e.g. parse_date)
            return ' '.join([to_unicode(arg) for arg in text.args])
    return unicode(text)


def exception_to_unicode(e, traceback=False):
    """Convert an `Exception` to an `unicode` object.
    In addition to `to_unicode`, this representation of the exception
    also contains the class name and optionally the traceback.
    """
    message = '%s: %s' % (e.__class__.__name__, to_unicode(e))
    if traceback:
        traceback_only = get_last_traceback().split('\n')[:-2]
        message = '\n%s\n%s' % (to_unicode('\n'.join(traceback_only)), message)
    return message
