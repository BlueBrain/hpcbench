import os
from string import Template


class TemplateWithDefaults(Template):
    idpattern = r'(?:\#)?[_a-z][_a-z0-9]*(?::?-[^}]*)?'

    # Modified from python2.7/string.py
    def substitute(self, mapping):
        # Helper function for .sub()
        def convert(mo):
            # Check the most common path first.
            named = mo.group('named') or mo.group('braced')
            if named is not None:
                if named.startswith('#'):
                    var = named[1:]
                    return str(len(mapping.get(var)))
                if ':-' in named:
                    var, _, default = named.partition(':-')
                    return mapping.get(var) or default
                if '-' in named:
                    var, _, default = named.partition('-')
                    return mapping.get(var, default)
                val = mapping[named]
                return '%s' % (val,)
            if mo.group('escaped') is not None:
                return self.delimiter
            if mo.group('invalid') is not None:
                self._invalid(mo)
            raise ValueError('Unrecognized named group in pattern', self.pattern)

        return self.pattern.sub(convert, self.template)


def expandvars(s, vars=None):
    """Perform variable substitution on the given string

    Supported syntax:
    * $VARIABLE
    * ${VARIABLE}
    * ${#VARIABLE}
    * ${VARIABLE:-default}

    :param s: message to expand
    :type s: str

    :param vars: dictionary of variables. Default is ``os.environ``
    :type vars: dict

    :return: expanded string
    :rtype: str
    """
    tpl = TemplateWithDefaults(s)
    return tpl.substitute(vars or os.environ)
