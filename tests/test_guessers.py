import unittest
import os
import pathlib
import tempfile
from types import MappingProxyType

from batstencil.stencils import *
from batstencil.utils import guess_template_by_argument, guess_context_by_argument
from batstencil.structs import *

_HERE = pathlib.Path(__file__).parent.resolve()
_RES = _HERE / 'res' / 'basic'


class _EnvMixin:
    @classmethod
    def setUpClass(cls):
        os.environ['STENCIL_TEMPLATE_PATH'] = str(_RES)

    @classmethod
    def tearDownClass(cls):
        if 'STENCIL_TEMPLATE_PATH' in os.environ:
            del os.environ['STENCIL_TEMPLATE_PATH']


class TestGuessTemplate(_EnvMixin, unittest.TestCase):
    def test_path_is_file_template(self):
        t = guess_template_by_argument(_RES / 'hello.txt')
        self.assertIsInstance(t, FileTemplate)
        self.assertEqual('hello.txt', t.file_name)

    def test_path_is_file_template_even_if_missing(self):
        t = guess_template_by_argument(pathlib.Path('does_not_exist.txt'))
        self.assertIsInstance(t, FileTemplate)

    def test_multi_line_str_is_string_template(self):
        self.assertIsInstance(guess_template_by_argument('one\ntwo', StringRenderer()), StringTemplate)

    def test_multi_line_str_that_looks_like_a_file_name(self):
        self.assertIsInstance(guess_template_by_argument('hello.txt\nfoo', StringRenderer()), StringTemplate)

    def test_loadable_template_name_is_file_template(self):
        t = guess_template_by_argument('hello.txt', StringRenderer())
        self.assertIsInstance(t, FileTemplate)

    def test_name_without_renderer_is_string_template(self):
        # Not an existing file relative to cwd, and no renderer to look it up with
        self.assertIsInstance(guess_template_by_argument('hello.txt'), StringTemplate)

    def test_existing_file_path_is_file_template(self):
        t = guess_template_by_argument(str(_RES / 'hello.txt'))
        self.assertIsInstance(t, FileTemplate)
        t = guess_template_by_argument(str(_RES / 'hello.txt'), StringRenderer())
        self.assertIsInstance(t, FileTemplate)

    def test_other_str_is_string_template(self):
        for s in ('Hello {{ name }}', 'no_such_template.txt', '', '*?<>|', 'a' * 5000):
            self.assertIsInstance(guess_template_by_argument(s, StringRenderer()), StringTemplate, s[:20])

    def test_template_is_passed_through(self):
        t = StringTemplate('x')
        self.assertIs(t, guess_template_by_argument(t))
        f = FileTemplate(_RES / 'hello.txt')
        self.assertIs(f, guess_template_by_argument(f, StringRenderer()))


class TestGuessContext(unittest.TestCase):
    def test_none_is_empty_dict_context(self):
        c = guess_context_by_argument(None)
        self.assertIsInstance(c, DictContext)
        self.assertEqual({}, c.as_dict())

    def test_none_gives_new_context_each_time(self):
        a = guess_context_by_argument(None)
        a.update('x', 1)
        self.assertEqual({}, guess_context_by_argument(None).as_dict())

    def test_mapping_is_dict_context(self):
        c = guess_context_by_argument({'a': 1})
        self.assertIsInstance(c, DictContext)
        self.assertEqual({'a': 1}, c.as_dict())

        c = guess_context_by_argument(MappingProxyType({'b': 2}))
        self.assertIsInstance(c, DictContext)
        self.assertEqual({'b': 2}, c.as_dict())

    def test_context_is_passed_through(self):
        c = DictContext({'a': 1})
        self.assertIs(c, guess_context_by_argument(c))

    def test_str_and_path_are_allconf_contexts(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = pathlib.Path(tmp) / 'ctx.yaml'
            with open(f, 'w', encoding='utf-8') as fout:
                fout.write('a: 1\n')
            for arg in (str(f), f):
                c = guess_context_by_argument(arg)
                self.assertIsInstance(c, AllConfContext)
                self.assertEqual(1, c.as_dict()['a'])


class TestRenderStencil(_EnvMixin, unittest.TestCase):
    def test_no_context(self):
        self.assertEqual('Hello world', render_stencil('Hello world'))
        self.assertEqual('Hello ', render_stencil('Hello {{ name }}'))

    def test_string_with_dict(self):
        self.assertEqual('Hello Bob', render_stencil('Hello {{ name }}', {'name': 'Bob'}))

    def test_template_name(self):
        self.assertEqual('Hello Bob', render_stencil('hello.txt', {'name': 'Bob'}))

    def test_template_path(self):
        self.assertEqual('Hello Bob', render_stencil(_RES / 'hello.txt', {'name': 'Bob'}))

    def test_template_object_and_context_object(self):
        res = render_stencil(StringTemplate('{{ a }}'), KeyWordArgumentContext(a='kw'))
        self.assertEqual('kw', res)

    def test_context_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = pathlib.Path(tmp) / 'ctx.yaml'
            with open(f, 'w', encoding='utf-8') as fout:
                fout.write('name: Yaml\n')
            self.assertEqual('Hello Yaml', render_stencil('hello.txt', f))
            self.assertEqual('Hello Yaml', render_stencil('hello.txt', str(f)))

    def test_skipped_returns_none(self):
        self.assertIsNone(render_stencil('{% skip_if true %}nope'))


class TestStencilVariable(unittest.TestCase):
    def test_string_template(self):
        import batstencil
        res = render_stencil('{{ __stencil__.version }}|{{ __stencil__.template_name }}|{{ __stencil__.template_path }}')
        self.assertEqual(f'{batstencil.__version__}|None|None', res)

    def test_file_template(self):
        import batstencil
        with tempfile.TemporaryDirectory() as tmp:
            f = pathlib.Path(tmp) / 'my_template.txt'
            with open(f, 'w', encoding='utf-8') as fout:
                fout.write('{{ __stencil__.version }}|{{ __stencil__.template_name }}|{{ __stencil__.template_path }}')
            res = render_stencil(f)
            version, name, path = res.split('|')
            self.assertEqual(batstencil.__version__, version)
            self.assertEqual('my_template.txt', name)
            self.assertEqual(f.absolute(), pathlib.Path(path))

    def test_stencil_variable_does_not_leak_into_context(self):
        ctx = DictContext({'a': 1})
        render_stencil('{{ __stencil__.version }}', ctx)
        self.assertEqual({'a': 1}, ctx.as_dict())
