import unittest

from batstencil.stencils import *
from batstencil.context import AlvissContext
from batstencil.structs import *

import pathlib
import tempfile

_HERE = pathlib.Path(__file__).parent.resolve()


class TestDictContexts(unittest.TestCase):
    def _check(self, ctx):
        ctx.update('top', 1)
        self.assertEqual(1, ctx.as_dict()['top'])

        ctx.nested_update('a.b.c', 'dotted')
        self.assertEqual({'b': {'c': 'dotted'}}, ctx.as_dict()['a'])

        ctx.nested_update(('x', 'y', 'z'), 'tuple')
        self.assertEqual('tuple', ctx.as_dict()['x']['y']['z'])

        ctx.nested_update(['p', 'q'], 'list')
        self.assertEqual({'q': 'list'}, ctx.as_dict()['p'])

        # Existing intermediate dicts are kept
        ctx.nested_update('a.b.d', 'more')
        self.assertEqual({'c': 'dotted', 'd': 'more'}, ctx.as_dict()['a']['b'])

        # A single (undotted) key works too
        ctx.nested_update('single', 5)
        self.assertEqual(5, ctx.as_dict()['single'])

    def test_dict_context(self):
        self._check(DictContext())

    def test_dict_context_with_initial_map(self):
        ctx = DictContext({'k': 'v'})
        self.assertEqual({'k': 'v'}, ctx.as_dict())
        ctx.update('k', 'w')
        self.assertEqual('w', ctx.as_dict()['k'])

    def test_keyword_context(self):
        ctx = KeyWordArgumentContext(foo='bar', n=1)
        self.assertEqual({'foo': 'bar', 'n': 1}, ctx.as_dict())
        self._check(ctx)

    def test_nested_update_overrides_existing_value(self):
        ctx = DictContext({'app': {'name': 'old'}})
        ctx.nested_update('app.name', 'new')
        self.assertEqual({'app': {'name': 'new'}}, ctx.as_dict())


class TestAllConfContext(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.file = pathlib.Path(self._tmp.name) / 'ctx.yaml'
        with open(self.file, 'w', encoding='utf-8') as fout:
            fout.write('app:\n  name: foo\n  ref: ${app.name}-ref\n')

    def test_loads_yaml(self):
        ctx = AllConfContext(self.file)
        self.assertEqual('foo', ctx.as_dict()['app']['name'])
        self.assertEqual('foo-ref', ctx.as_dict()['app']['ref'])
        self.assertEqual(str(self.file), ctx.file_name)

    def test_loads_from_str_path(self):
        ctx = AllConfContext(str(self.file))
        self.assertEqual('foo', ctx.as_dict()['app']['name'])

    def test_update(self):
        ctx = AllConfContext(self.file)
        ctx.update('extra', 'value')
        self.assertEqual('value', ctx.as_dict()['extra'])
        ctx.update('extra', 'changed')
        self.assertEqual('changed', ctx.as_dict()['extra'])

    def test_nested_update(self):
        ctx = AllConfContext(self.file)
        ctx.nested_update('app.color.favorite', 'red')
        ctx.nested_update(('new', 'deep', 'key'), 1)
        ctx.nested_update(['app', 'name'], 'bar')
        d = ctx.as_dict()
        self.assertEqual('red', d['app']['color']['favorite'])
        self.assertEqual(1, d['new']['deep']['key'])
        self.assertEqual('bar', d['app']['name'])

    def test_updates_are_used_when_rendering(self):
        ctx = AllConfContext(self.file)
        ctx.nested_update('app.name', 'changed')
        self.assertEqual('changed', render_stencil('{{ app.name }}', ctx))

    def test_alviss_alias(self):
        self.assertIs(AlvissContext, AllConfContext)
