import os
import shutil
import tempfile
import unittest

from hpcbench.toolbox.collections_ext import (
    Configuration,
    dict_map_kv,
    dict_merge,
    flatten_dict,
    FrozenDict,
    FrozenList,
    nameddict,
)


class TestNamedDict(unittest.TestCase):
    def test_init(self):
        e = nameddict()
        self.assertEqual(len(e), 0)
        e = nameddict([('foo', 'bar'), ('pika', 'lol')])
        self.assertTrue(len(e), e)
        self.assertEqual(e['foo'], 'bar')
        self.assertEqual(e.foo, 'bar')

    def test_add_key(self):
        e = nameddict()
        e['foo'] = 'bar'
        self.assertEqual(e.foo, 'bar')
        e = nameddict()
        e.foo = 'bar'
        self.assertEqual(e['foo'], 'bar')

    def test_del_key(self):
        e = nameddict([('foo', 'bar')])
        self.assertEqual(e.foo, 'bar')
        del e['foo']
        self.assertEqual(len(e), 0)
        with self.assertRaises(AttributeError):
            self.assertIsNotNone(e.foo)

    def test_nested_dict(self):
        data = {'foo': {'bar': {'pika': 'value'}}}
        e = nameddict(data)
        self.assertEqual(e.foo, {'bar': {'pika': 'value'}})
        self.assertEqual(e.foo.bar, {'pika': 'value'})
        self.assertEqual(e.foo.bar.pika, 'value')

        e['pika'] = {'key': 'value'}
        self.assertEqual(e.pika, {'key': 'value'})
        self.assertEqual(e.pika.key, 'value')

        e = nameddict()
        e.foo = {'key': 'value'}
        self.assertEqual(e.foo.key, 'value')

    def test_nested_assignment(self):
        """ nested assignment is not supported"""
        e = nameddict()
        with self.assertRaises(AttributeError):
            e.foo.bar = 'pika'

    def test_uppercase_keys(self):
        e = nameddict({'FOO': 'bar'})
        self.assertFalse('foo' in e)
        with self.assertRaises(AttributeError):
            self.assertIsNotNone(e.foo)
        self.assertEqual(e['FOO'], 'bar')
        self.assertEqual(e.FOO, 'bar')


class TestConfiguration(unittest.TestCase):
    def test_env_error(self):
        try:
            tmpdir = tempfile.mkdtemp()
            envvar = 'TestConfigurationSettings'
            os.environ[envvar] = tmpdir
            with self.assertRaises(IOError):
                Configuration.from_env(envvar, None, {})
        finally:
            shutil.rmtree(tmpdir)


class TestFlattenDict(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(flatten_dict({}), {})

    def test_nested_dict(self):
        self.assertEqual(
            flatten_dict({'foo': 42, 'bar': {'foo': 43}}), {'foo': 42, 'bar.foo': 43}
        )

    @unittest.skip("not implemented")
    def test_conflict(self):
        self.assertEqual(
            flatten_dict({'bar.foo': 42, 'bar': {'foo': 43}}),
            {'bar.foo': 42, 'bar.foo.2': 43},
        )

    @unittest.skip("not implemented")
    def test_list(self):
        self.assertEqual(
            flatten_dict({'foo': [dict(bar=42), dict(pika='plop'), dict(bar=43)]}),
            {'foo.0.bar': 42, 'foo.1.pika': 'plop', 'foo.2.bar': 43},
        )


class TestDictMerge(unittest.TestCase):
    def test_dm_empty(self):
        d1 = {}
        dict_merge(d1, {})
        self.assertEqual(d1, {})
        dict_merge(d1, dict(foo=42))
        self.assertEqual(d1, dict(foo=42))
        dict_merge(d1, dict(foo=43))
        self.assertEqual(d1, dict(foo=43))

    def test_dm_rec(self):
        d1 = dict(foo=dict(bar=42))
        dict_merge(d1, dict(foo=dict(foo=44)))
        self.assertEqual(d1, dict(foo=dict(bar=42, foo=44)))
        dict_merge(d1, dict(foo=dict(foo=42)))
        self.assertEqual(d1, dict(foo=dict(bar=42, foo=42)))


class TestDictMapKV(unittest.TestCase):
    def test_empty_dict(self):
        self.assertMapKVEquals({}, str, {})

    def test_none(self):
        self.assertMapKVEquals(None, str, 'None')

    def test_list(self):
        self.assertMapKVEquals([1, 2], str, ["1", "2"])

    def test_simple_dict(self):
        self.assertMapKVEquals({'foo': 42, 1: 'bar'}, str, {'foo': '42', '1': 'bar'})

    def test_nested_dict(self):
        self.assertMapKVEquals(
            {42: {1: [43, {2: 44, 3: [45, 46]}]}, 43: 47},
            str,
            {'42': {'1': ['43', {'2': '44', '3': ['45', '46']}]}, '43': '47'},
        )

    def assertMapKVEquals(self, obj, func, result):
        self.assertEqual(dict_map_kv(obj, func), result)


class TestFrozenDataStructures(unittest.TestCase):
    def test_dict(self):
        d = FrozenDict()
        self.assertEqual(len(d), 0)
        self.assertEqual(d, {})
        self.assertEqual(str(d), '{}')
        self.assertEqual(d, eval(repr(d)))

        d = FrozenDict(foo=42)
        self.assertEqual(len(d), 1)
        self.assertEqual(d, dict(foo=42))
        self.assertEqual(str(d), "{'foo': 42}")
        self.assertEqual(d, eval(repr(d)))

        d = FrozenDict(d)
        self.assertEqual(len(d), 1)
        self.assertEqual(d, dict(foo=42))
        self.assertEqual(str(d), "{'foo': 42}")
        self.assertEqual(d, eval(repr(d)))

        self.assertEqual(d.foo, 42)
        self.assertEqual(d['foo'], 42)
        with self.assertRaises(TypeError):
            d['foo'] = 43

    def test_list(self):
        fl = FrozenList()
        self.assertEqual(len(fl), 0)
        self.assertEqual(fl, [])
        self.assertEqual(str(fl), '[]')
        self.assertEqual(fl, eval(repr(fl)))

        fl = FrozenList([42])
        self.assertEqual(len(fl), 1)
        self.assertEqual(fl, [42])
        self.assertEqual(str(fl), '[42]')
        self.assertEqual(fl, eval(repr(fl)))

        self.assertEqual(fl[0], 42)
        with self.assertRaises(TypeError):
            fl[0] = 43
        with self.assertRaises(TypeError):
            fl += [42]


if __name__ == '__main__':
    unittest.main()
