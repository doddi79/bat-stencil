import unittest

from batstencil.stencils import *
from batstencil.structs import *

import os
import pathlib
import tempfile

_HERE = pathlib.Path(__file__).parent.resolve()
_SETFILENAME_LOGGER = 'batstencil.jinjaext.extensions._setfilename'


def write(path: pathlib.Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as fout:
        fout.write(content)


def read(path: pathlib.Path) -> str:
    with open(path, 'r', encoding='utf-8', newline='') as fin:
        return fin.read()


class TestFileRenderer(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = pathlib.Path(self._tmp.name)
        self.tpl = self.tmp / 'in' / 'tpl.txt'
        write(self.tpl, 'Hello {{ name }}')
        self.out = self.tmp / 'out'
        self.ctx = DictContext({'name': 'World'})

    def _renderer(self, output, template=None, **kwargs):
        return FileRenderer(output, context=self.ctx, template=template or FileTemplate(self.tpl), **kwargs)

    def test_writes_file_and_returns_absolute_path(self):
        target = self.out / 'result.txt'
        res = self._renderer(target).render()
        self.assertTrue(pathlib.Path(res).is_absolute())
        self.assertEqual(target.absolute(), pathlib.Path(res))
        self.assertEqual('Hello World', read(target))

    def test_relative_output_path_returns_absolute(self):
        cwd = os.getcwd()
        os.chdir(self.tmp)
        try:
            res = self._renderer('rel.txt').render()
        finally:
            os.chdir(cwd)
        self.assertTrue(pathlib.Path(res).is_absolute())
        self.assertEqual('Hello World', read(self.tmp / 'rel.txt'))

    def test_trailing_slash_uses_template_file_name(self):
        res = self._renderer(str(self.out) + '/').render()
        self.assertEqual((self.out / 'tpl.txt').absolute(), pathlib.Path(res))
        self.assertEqual('Hello World', read(self.out / 'tpl.txt'))

    def test_existing_directory_uses_template_file_name(self):
        self.out.mkdir()
        res = self._renderer(self.out).render()
        self.assertEqual((self.out / 'tpl.txt').absolute(), pathlib.Path(res))

    def test_setfilename_with_directory_output(self):
        write(self.tpl, '{% setfilename %}  named_{{ name }}.txt  {% endsetfilename %}body')
        res = self._renderer(str(self.out) + '/').render()
        self.assertEqual((self.out / 'named_World.txt').absolute(), pathlib.Path(res))
        self.assertEqual('body', read(self.out / 'named_World.txt'))

    def test_setfilename_overrides_explicit_file_name(self):
        write(self.tpl, '{% setfilename %}override.txt{% endsetfilename %}body')
        res = self._renderer(self.out / 'explicit.txt').render()
        self.assertEqual((self.out / 'override.txt').absolute(), pathlib.Path(res))
        self.assertFalse((self.out / 'explicit.txt').exists())

    def test_empty_setfilename_warns_and_uses_explicit_name(self):
        write(self.tpl, '{% setfilename %}{{ missing }}{% endsetfilename %}body')
        with self.assertLogs(_SETFILENAME_LOGGER, level='WARNING') as logs:
            res = self._renderer(self.out / 'explicit.txt').render()
        self.assertTrue(any('empty file name' in m for m in logs.output))
        self.assertEqual((self.out / 'explicit.txt').absolute(), pathlib.Path(res))
        self.assertEqual('body', read(self.out / 'explicit.txt'))

    def test_empty_setfilename_falls_back_to_template_name(self):
        write(self.tpl, '{% setfilename %}  {% endsetfilename %}body')
        with self.assertLogs(_SETFILENAME_LOGGER, level='WARNING'):
            res = self._renderer(str(self.out) + '/').render()
        self.assertEqual((self.out / 'tpl.txt').absolute(), pathlib.Path(res))

    def test_string_template_without_name_raises(self):
        r = FileRenderer(str(self.out) + '/', context=self.ctx, template=StringTemplate('x'))
        with self.assertRaises(NoOutputFileNameError):
            r.render()

    def test_string_template_with_explicit_file(self):
        r = FileRenderer(self.out / 'x.txt', context=self.ctx, template=StringTemplate('Hi {{ name }}'))
        res = r.render()
        self.assertEqual('Hi World', read(pathlib.Path(res)))

    def test_overwrite_true_by_default(self):
        target = self.out / 'result.txt'
        self._renderer(target).render()
        write(self.tpl, 'Changed')
        self._renderer(target).render()
        self.assertEqual('Changed', read(target))

    def test_no_overwrite_raises(self):
        target = self.out / 'result.txt'
        self._renderer(target).render()
        write(self.tpl, 'Changed')
        with self.assertRaises(OutputFileExistsError):
            self._renderer(target, overwrite=False).render()
        self.assertEqual('Hello World', read(target))

    def test_no_overwrite_writes_new_file(self):
        res = self._renderer(self.out / 'new.txt', overwrite=False).render()
        self.assertIsNotNone(res)

    def test_skip_if_returns_none_and_writes_nothing(self):
        write(self.tpl, '{% skip_if name == "World" %}Hello')
        target = self.out / 'result.txt'
        self.assertIsNone(self._renderer(target).render())
        self.assertFalse(target.exists())
        self.assertFalse(self.out.exists())

    def test_skip_if_false_renders(self):
        write(self.tpl, '{% skip_if name == "Nope" %}Hello')
        target = self.out / 'result.txt'
        self.assertIsNotNone(self._renderer(target).render())
        self.assertEqual('Hello', read(target))

    def test_unix_line_endings(self):
        write(self.tpl, 'line one\nline two\n')
        target = self.out / 'result.txt'
        self._renderer(target).render()
        with open(target, 'rb') as fin:
            self.assertEqual(b'line one\nline two\n', fin.read())

    def test_custom_line_endings(self):
        write(self.tpl, 'line one\nline two\n')
        target = self.out / 'result.txt'
        self._renderer(target, new_line_char='\r\n').render()
        with open(target, 'rb') as fin:
            self.assertEqual(b'line one\r\nline two\r\n', fin.read())

    def test_utf8_output(self):
        write(self.tpl, 'Halló {{ name }} ✓')
        target = self.out / 'result.txt'
        self._renderer(target).render()
        with open(target, 'rb') as fin:
            self.assertEqual('Halló World ✓'.encode('utf-8'), fin.read())

    def test_template_is_rendered_only_once(self):
        calls = []

        def counter():
            calls.append(1)
            return len(calls)

        write(self.tpl, '{% setfilename %}f{{ counter() }}.txt{% endsetfilename %}{{ counter() }}')
        ctx = DictContext({'counter': counter})
        res = FileRenderer(str(self.out) + '/', context=ctx, template=FileTemplate(self.tpl)).render()
        self.assertEqual(2, len(calls))
        self.assertEqual((self.out / 'f1.txt').absolute(), pathlib.Path(res))
        self.assertEqual('2', read(self.out / 'f1.txt'))

    def test_no_template_raises(self):
        with self.assertRaises(NoTemplateSetError):
            FileRenderer(self.out / 'x.txt').render()

    def test_repeat_for_is_an_error(self):
        write(self.tpl, '{% repeat_for x in [1, 2] %}{{ x }}')
        with self.assertRaises(RenderError):
            self._renderer(self.out / 'x.txt').render()
        self.assertFalse((self.out / 'x.txt').exists())


class TestStringRendererErrors(unittest.TestCase):
    def test_repeat_for_in_string_renderer_raises(self):
        with self.assertRaises(RenderError):
            render_stencil('{% repeat_for x in [1, 2] %}{{ x }}')

    def test_repeat_for_in_stdout_renderer_raises(self):
        r = StdOutRenderer(template=StringTemplate('{% repeat_for x in [1, 2] %}{{ x }}'))
        with self.assertRaises(RenderError):
            r.render()
