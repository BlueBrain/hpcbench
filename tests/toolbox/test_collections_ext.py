import os
import tempfile
import shutil
import unittest

from hpcbench.toolbox.collections_ext import (
    Configuration,
    dict_merge,
    flatten_dict,
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
            e.foo

    def test_nested_dict(self):
        data = {
            'foo': {
                'bar': {
                    'pika': 'value'
                }
            },
        }
        e = nameddict(data)
        self.assertEqual(e.foo, {'bar': {'pika': 'value'}})
        self.assertEqual(e.foo.bar, {'pika': 'value'})
        self.assertEqual(e.foo.bar.pika, 'value')

        e['pika'] = {
            'key': 'value'
        }
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
            e.foo
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
            flatten_dict({
                'foo': 42,
                'bar': {
                    'foo': 43
                }
            }),
            {
                'foo': 42,
                'bar.foo': 43
            }
        )

    @unittest.skip("not implemented")
    def test_conflict(self):
        self.assertEqual(
            flatten_dict({
                'bar.foo': 42,
                'bar': {
                    'foo': 43
                }
            }),
            {
                'bar.foo': 42,
                'bar.foo.2': 43,
            }
        )

    @unittest.skip("not implemented")
    def test_list(self):
        self.assertEqual(
            flatten_dict({
                'foo': [
                    dict(bar=42),
                    dict(pika='plop'),
                    dict(bar=43),
                ]
            }),
            {
                'foo.0.bar': 42,
                'foo.1.pika': 'plop',
                'foo.2.bar': 43,
            }
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


if __name__ == '__main__':
    unittest.main()
