from collections import Sequence
import unittest

from requests.structures import CaseInsensitiveDict

from hpcbench.toolbox.edsl import kwargsql

and_ = kwargsql.and_
or_ = kwargsql.or_
xor = kwargsql.xor


class TestKwargSQL(unittest.TestCase):
    d = {
        's': 's_value',
        'i': 3,
        'nested': {'val': 'nested-value', 'another_key': 42},
        'array': [4, 5, 6],
        'exc': Exception("Error: a comprehensive message"),
        'nestedl': [dict(foo=1), dict(foo=2, bar=3)],
    }

    def test_sequence_get(self):
        self.assertEqual(list(kwargsql.get(self.d, 'nestedl__any__foo')), [1, 2])
        # nested elements that produce an error are discarded from the result.
        self.assertEqual(list(kwargsql.get(self.d, 'nestedl__any__bar')), [3])
        self.assertEqual(list(kwargsql.get(self.d, 'nestedl__any__unknown')), [])
        # It makes not difference to call `any` or `each` is `kwargsql.get`
        # because it matters when there is an operation to perform on the
        # result data.
        self.assertEqual(list(kwargsql.get(self.d, 'nestedl__each__foo')), [1, 2])
        self.assertEqual(list(kwargsql.get(self.d, 'nestedl__each__bar')), [3])
        self.assertEqual(list(kwargsql.get(self.d, 'nestedl__any__unknown')), [])

    def test_sequence_logical(self):
        # at least one element of `nestedl` has the `foo` attribute
        self.assertTrue(and_(self.d, nestedl__any__contains='foo'))
        # at least one element of `nestedl` has the `bar` attribute
        self.assertTrue(and_(self.d, nestedl__any__contains='bar'))
        # all elements of `nestedl` have the 'foo' attribute
        self.assertTrue(and_(self.d, nestedl__each__contains='foo'))
        # not all elements of `nestedl` have the 'bar' attribute
        self.assertFalse(and_(self.d, nestedl__each__contains='bar'))
        # can run operation (here equality) on an empty sequence
        self.assertFalse(and_(self.d, nestedl__each__unknown='bar'))
        # can run operation (here equality) on an empty sequence
        self.assertFalse(or_(self.d, nestedl__each__unknown='bar'))

    def test_operations(self):
        self.assertFalse(kwargsql.OPERATIONS['ne']('a', u'a'))
        self.assertTrue(kwargsql.OPERATIONS['ne']('a', 42))
        self.assertFalse(kwargsql.OPERATIONS['lt'](42, 42))
        self.assertTrue(kwargsql.OPERATIONS['lt'](41, 42))
        self.assertTrue(kwargsql.OPERATIONS['lte'](42, 42))
        self.assertFalse(kwargsql.OPERATIONS['gt'](42, 42))
        self.assertTrue(kwargsql.OPERATIONS['gt'](42, 41))
        self.assertTrue(kwargsql.OPERATIONS['gte'](42, 42))
        self.assertTrue(kwargsql.OPERATIONS['in'](1, [2, 3, 1, 4]))
        self.assertTrue(kwargsql.OPERATIONS['nin'](0, [1, 2, 3]))
        self.assertTrue(kwargsql.OPERATIONS['size']([1, 2, 3], 3))
        self.assertTrue(kwargsql.OPERATIONS['iexact']('foo', u'Foo'))
        self.assertTrue(kwargsql.OPERATIONS['contains']('abcde', 'bcd'))
        self.assertTrue(kwargsql.OPERATIONS['icontains']('abcd', 'bCD'))
        self.assertTrue(kwargsql.OPERATIONS['startswith']('abcd', 'abc'))
        self.assertTrue(kwargsql.OPERATIONS['istartswith']('abcd', 'aBc'))
        self.assertTrue(kwargsql.OPERATIONS['endswith']('abcd', 'bcd'))
        self.assertTrue(kwargsql.OPERATIONS['iendswith']('abcd', 'BcD'))
        self.assertTrue(kwargsql.OPERATIONS['isinstance']('abcd', str))
        self.assertTrue(kwargsql.OPERATIONS['issubclass'](str, str))

    def test_seqexp(self):
        d = self.d
        self.assertTrue(and_(d, s='s_value', i=3))
        self.assertFalse(and_(d, s='s_value', i=1))
        self.assertFalse(or_(d, s='not', i='not'))
        self.assertTrue(or_(d, s='s_value', i='not'))
        self.assertTrue(or_(d, s='not', i=3))
        self.assertTrue(or_(d, s='s_value', foo_i=3))
        self.assertTrue(xor(d, foo_i=42, s='s_value'))
        self.assertFalse(xor(d, foo_i=42, s='unknown'))

    def test_simple_op(self):
        d = self.d
        self.assertTrue(and_(d, nested__size=2))

    def test_simple_trailing__(self):
        self.assertTrue(and_(self.d, s__='s_value'))

    def test_not(self):
        d = self.d
        self.assertFalse(and_(d, s__not='s_value'))

    def test_nested(self):
        d = self.d
        self.assertTrue(and_(d, nested__val='nested-value'))
        self.assertTrue(and_(d, exc__istartswith='error: '))

    def test_arrays(self):
        self.assertTrue(and_(self.d, array__1=5))

    def test_invalid(self):
        with self.assertRaises(Exception):
            and_(self.d, __=42)

    def test_exist_operation(self):
        self.assertFalse(and_(self.d, nested__unknown__exists=1))
        self.assertFalse(and_(self.d, exc__unknown__exists=1))
        self.assertTrue(and_(self.d, nested__unknown__exists=False))
        self.assertTrue(and_(self.d, exc__unknown__exists=False))

    def test_get(self):
        self.assertEqual(kwargsql.get(self.d, 'nested__val'), 'nested-value')

    def test_abc_mappings_navigation(self):
        d = dict(foo=CaseInsensitiveDict(bar=CaseInsensitiveDict(pika=42)))
        self.assertEqual(kwargsql.get(d, 'foo__bAr__PiKA'), 42)

    def test_abc_sequence_select(self):
        class DumbSequence(Sequence):
            def __len__(self):
                return 2

            def __getitem__(self, key):
                return key + 1

        self.assertEqual(kwargsql.get(DumbSequence(), '1'), 2)


if __name__ == '__main__':
    unittest.main()
