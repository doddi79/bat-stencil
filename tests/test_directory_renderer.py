import unittest

from batstencil.stencils import *
from batstencil.structs import *

import os
import pathlib
import tempfile

_SETFILENAME_LOGGER = 'batstencil.jinjaext.extensions._setfilename'


def write(path: pathlib.Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as fout:
        fout.write(content)


def read(path) -> str:
    with open(path, 'r', encoding='utf-8', newline='') as fin:
        return fin.read()


def tree(root: pathlib.Path) -> dict:
    """All files under root as {posix relative path: content}"""
    return {p.relative_to(root).as_posix(): read(p) for p in sorted(root.rglob('*')) if p.is_file()}


class _DirBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = pathlib.Path(self._tmp.name).resolve()
        self.tpl = self.tmp / 'tpl'
        self.tpl.mkdir()
        self.out = self.tmp / 'out'

    def render(self, context=None, **kwargs):
        r = DirectoryRenderer(self.out, context=DictContext(context or {}),
                              template=DirectoryTemplate(self.tpl), **kwargs)
        return r.render()

    def rel(self, paths):
        return [pathlib.Path(p).resolve().relative_to(self.out).as_posix() for p in paths]


class TestDirectoryTemplate(_DirBase):
    def test_missing_dir(self):
        with self.assertRaises(TemplateNotFoundError):
            DirectoryTemplate(self.tmp / 'nope')

    def test_not_a_dir(self):
        write(self.tmp / 'file.txt', 'x')
        with self.assertRaises(TemplateNotFoundError):
            DirectoryTemplate(self.tmp / 'file.txt')

    def test_meta_in_root_raises(self):
        write(self.tpl / '__stencil_meta__', '')
        with self.assertRaises(TemplateError):
            DirectoryTemplate(self.tpl)

    def test_structure_is_sorted(self):
        for n in ('c.txt', 'a.txt', 'b.txt'):
            write(self.tpl / n, n)
        for n in ('z', 'm', 'a'):
            write(self.tpl / n / 'f.txt', n)
        t = DirectoryTemplate(self.tpl)
        self.assertEqual(['a.txt', 'b.txt', 'c.txt'], [f.file_name for f in t.files])
        self.assertEqual(['a', 'm', 'z'], [d.source_name for d in t.directories])
        self.assertTrue(t.is_root)
        self.assertFalse(t.directories[0].is_root)
        self.assertIs(t, t.directories[0].parent)

    def test_meta_is_not_a_file(self):
        write(self.tpl / 'sub' / '__stencil_meta__', '')
        write(self.tpl / 'sub' / 'f.txt', 'x')
        t = DirectoryTemplate(self.tpl)
        sub = t.directories[0]
        self.assertEqual(['f.txt'], [f.file_name for f in sub.files])
        self.assertIsNotNone(sub.meta_file)
        self.assertIsNotNone(sub.meta_template)
        self.assertIsNone(t.meta_template)

    def test_get_jinja_template_is_an_error(self):
        with self.assertRaises(TemplateError):
            DirectoryTemplate(self.tpl).get_jinja_template()

    def test_renderer_only_accepts_directory_templates(self):
        r = DirectoryRenderer(self.out)
        with self.assertRaises(InvalidTemplateTypeForRendererError):
            r.template = StringTemplate('x')

    def test_no_template_raises(self):
        with self.assertRaises(NoTemplateSetError):
            DirectoryRenderer(self.out).render()


class TestDirectoryRenderer(_DirBase):
    def test_renders_files_and_nested_dirs(self):
        write(self.tpl / 'top.txt', 'top {{ name }}')
        write(self.tpl / 'a' / 'one.txt', 'one {{ name }}')
        write(self.tpl / 'a' / 'b' / 'two.txt', 'two {{ name }}')
        write(self.tpl / 'empty_dir' / '.keep', '')
        res = self.render({'name': 'X'})
        self.assertEqual(
            {'top.txt': 'top X', 'a/one.txt': 'one X', 'a/b/two.txt': 'two X', 'empty_dir/.keep': ''},
            tree(self.out))
        self.assertEqual(4, len(res))
        for p in res:
            self.assertTrue(pathlib.Path(p).is_absolute())
            self.assertTrue(pathlib.Path(p).is_file())

    def test_output_root_is_created(self):
        write(self.tpl / 'f.txt', 'x')
        self.out = self.tmp / 'deep' / 'er' / 'out'
        self.render()
        self.assertEqual('x', read(self.out / 'f.txt'))

    def test_empty_dir_is_created(self):
        (self.tpl / 'sub').mkdir()
        write(self.tpl / 'f.txt', 'x')
        self.render()
        self.assertTrue((self.out / 'sub').is_dir())

    def test_returned_paths_are_sorted_deterministically(self):
        for n in ('b.txt', 'c.txt', 'a.txt'):
            write(self.tpl / n, n)
        for d in ('z', 'm'):
            write(self.tpl / d / 'y.txt', d)
            write(self.tpl / d / 'x.txt', d)
            write(self.tpl / d / 'sub' / 'k.txt', d)
        expected = ['a.txt', 'b.txt', 'c.txt',
                    'm/x.txt', 'm/y.txt', 'm/sub/k.txt',
                    'z/x.txt', 'z/y.txt', 'z/sub/k.txt']
        for _ in range(3):
            self.assertEqual(expected, self.rel(self.render()))

    def test_unix_line_endings(self):
        write(self.tpl / 'f.txt', 'a\nb\n')
        self.render()
        with open(self.out / 'f.txt', 'rb') as fin:
            self.assertEqual(b'a\nb\n', fin.read())

    def test_meta_setfilename_renames_dir(self):
        write(self.tpl / 'placeholder' / '__stencil_meta__', '{% setfilename %}{{ name }}_dir{% endsetfilename %}')
        write(self.tpl / 'placeholder' / 'f.txt', 'x')
        write(self.tpl / 'placeholder' / 'inner' / 'g.txt', 'y')
        res = self.render({'name': 'real'})
        self.assertEqual({'real_dir/f.txt': 'x', 'real_dir/inner/g.txt': 'y'}, tree(self.out))
        self.assertEqual(['real_dir/f.txt', 'real_dir/inner/g.txt'], self.rel(res))

    def test_meta_file_is_not_rendered(self):
        write(self.tpl / 'sub' / '__stencil_meta__', '')
        write(self.tpl / 'sub' / 'f.txt', 'x')
        self.render()
        self.assertEqual({'sub/f.txt': 'x'}, tree(self.out))

    def test_meta_skip_if_skips_dir_and_contents(self):
        write(self.tpl / 'skipme' / '__stencil_meta__', '{% skip_if skip %}')
        write(self.tpl / 'skipme' / 'f.txt', 'x')
        write(self.tpl / 'skipme' / 'inner' / 'g.txt', 'y')
        write(self.tpl / 'keep' / '__stencil_meta__', '{% skip_if skip %}')
        write(self.tpl / 'keep' / 'f.txt', 'z')
        self.render({'skip': False})
        self.assertEqual({'skipme/f.txt': 'x', 'skipme/inner/g.txt': 'y', 'keep/f.txt': 'z'}, tree(self.out))
        self.render({'skip': True})
        self.assertEqual({}, tree(self.out))
        self.assertFalse((self.out / 'skipme').exists())

    def test_meta_skip_if_only_skips_that_dir(self):
        write(self.tpl / 'skipme' / '__stencil_meta__', '{% skip_if true %}')
        write(self.tpl / 'skipme' / 'f.txt', 'x')
        write(self.tpl / 'keep' / 'f.txt', 'z')
        write(self.tpl / 'top.txt', 't')
        self.render()
        self.assertEqual({'keep/f.txt': 'z', 'top.txt': 't'}, tree(self.out))

    def test_file_skip_if(self):
        write(self.tpl / 'gone.txt', '{% skip_if true %}x')
        write(self.tpl / 'here.txt', 'x')
        res = self.render()
        self.assertEqual(['here.txt'], self.rel(res))
        self.assertFalse((self.out / 'gone.txt').exists())

    def test_render_returns_actual_paths_with_setfilename(self):
        write(self.tpl / 'a.txt', '{% setfilename %}renamed_{{ name }}.txt{% endsetfilename %}content')
        write(self.tpl / 'sub' / 'b.txt', '{% setfilename %}other.cfg{% endsetfilename %}content b')
        write(self.tpl / 'sub' / 'c.txt', 'plain')
        res = self.render({'name': 'N'})
        self.assertEqual(['renamed_N.txt', 'sub/c.txt', 'sub/other.cfg'], sorted(self.rel(res)))
        for p in res:
            self.assertTrue(pathlib.Path(p).is_file(), p)
        self.assertEqual({'renamed_N.txt': 'content', 'sub/other.cfg': 'content b', 'sub/c.txt': 'plain'},
                         tree(self.out))

    def test_empty_setfilename_warns_and_keeps_name(self):
        write(self.tpl / 'a.txt', '{% setfilename %}{{ nothing }}{% endsetfilename %}content')
        with self.assertLogs(_SETFILENAME_LOGGER, level='WARNING'):
            res = self.render()
        self.assertEqual(['a.txt'], self.rel(res))

    def test_broken_template_raises_template_render_error(self):
        write(self.tpl / 'good.txt', 'fine')
        write(self.tpl / 'sub' / 'broken.txt', 'line one\n{{ foo }\n')
        with self.assertRaises(TemplateRenderError) as cm:
            self.render()
        err = cm.exception
        self.assertIn('broken.txt', str(err))
        self.assertIn('line 2', str(err))
        self.assertIsNotNone(err.template_path)
        self.assertEqual(self.tpl / 'sub' / 'broken.txt', pathlib.Path(err.template_path))
        self.assertIsInstance(err.__cause__, jinja2.TemplateSyntaxError)
        self.assertIsInstance(err, RenderError)

    def test_failing_template_at_runtime_raises_template_render_error(self):
        write(self.tpl / 'bad.txt', '{{ 1 / 0 }}')
        with self.assertRaises(TemplateRenderError) as cm:
            self.render()
        self.assertIn('bad.txt', str(cm.exception))
        self.assertIsInstance(cm.exception.__cause__, ZeroDivisionError)

    def test_broken_meta_names_meta_file(self):
        write(self.tpl / 'sub' / '__stencil_meta__', '{% setfilename %}x')
        write(self.tpl / 'sub' / 'f.txt', 'x')
        with self.assertRaises(TemplateRenderError) as cm:
            self.render()
        self.assertIn('__stencil_meta__', str(cm.exception))
        self.assertIn('__stencil_meta__', cm.exception.template_path)
        self.assertIsInstance(cm.exception.__cause__, jinja2.TemplateError)

    def test_stencil_errors_are_not_wrapped(self):
        write(self.tpl / 'e.txt', "{% embed 'no_such_file_anywhere.txt' %}")
        with self.assertRaises(EmbedFileNotFound):
            self.render()

    def test_no_overwrite(self):
        write(self.tpl / 'f.txt', 'new')
        write(self.out / 'f.txt', 'old')
        with self.assertRaises(OutputFileExistsError):
            self.render(purge=False, overwrite=False)
        self.assertEqual('old', read(self.out / 'f.txt'))

    def test_no_overwrite_with_purge_and_existing_output_raises(self):
        write(self.tpl / 'f.txt', 'new')
        write(self.out / 'f.txt', 'old')
        with self.assertRaises(OutputFileExistsError):
            self.render(purge=True, overwrite=False)
        self.assertEqual('old', read(self.out / 'f.txt'))

    def test_no_overwrite_into_new_dir(self):
        write(self.tpl / 'f.txt', 'new')
        self.render(overwrite=False)
        self.assertEqual('new', read(self.out / 'f.txt'))

    def test_setfilename_escaping_output_dir_raises(self):
        write(self.tpl / 'a.txt', '{% setfilename %}../x.txt{% endsetfilename %}content')
        with self.assertRaises(TemplateRenderError):
            self.render()
        self.assertFalse((self.tmp / 'x.txt').exists())

    def test_setfilename_escaping_output_dir_in_subdir_raises(self):
        write(self.tpl / 'sub' / 'a.txt', '{% setfilename %}../../x.txt{% endsetfilename %}content')
        with self.assertRaises(TemplateRenderError):
            self.render()
        self.assertFalse((self.tmp / 'x.txt').exists())

    def test_meta_setfilename_escaping_output_dir_raises(self):
        write(self.tpl / 'sub' / '__stencil_meta__', '{% setfilename %}../escaped{% endsetfilename %}')
        write(self.tpl / 'sub' / 'f.txt', 'x')
        with self.assertRaises(TemplateRenderError):
            self.render()
        self.assertFalse((self.tmp / 'escaped').exists())

    def test_setfilename_with_subpath_inside_output_is_ok(self):
        write(self.tpl / 'a.txt', '{% setfilename %}deeper/a.txt{% endsetfilename %}content')
        res = self.render()
        self.assertEqual(['deeper/a.txt'], self.rel(res))


class TestPurge(_DirBase):
    def test_purge_deletes_previous_output(self):
        write(self.tpl / 'new.txt', 'new')
        write(self.out / 'old.txt', 'old')
        write(self.out / 'olddir' / 'old.txt', 'old')
        self.render()
        self.assertEqual({'new.txt': 'new'}, tree(self.out))
        self.assertFalse((self.out / 'olddir').exists())

    def test_no_purge_keeps_other_files(self):
        write(self.tpl / 'new.txt', 'new')
        write(self.out / 'old.txt', 'old')
        write(self.out / 'olddir' / 'old.txt', 'old')
        self.render(purge=False)
        self.assertEqual({'new.txt': 'new', 'old.txt': 'old', 'olddir/old.txt': 'old'}, tree(self.out))

    def test_purge_is_default(self):
        write(self.tpl / 'new.txt', 'new')
        write(self.out / 'old.txt', 'old')
        DirectoryRenderer(self.out, template=DirectoryTemplate(self.tpl)).render()
        self.assertEqual({'new.txt': 'new'}, tree(self.out))

    def test_purging_cwd_is_refused(self):
        write(self.tpl / 'new.txt', 'new')
        work = self.tmp / 'work'
        write(work / 'precious.txt', 'keep me')
        cwd = os.getcwd()
        os.chdir(work)
        try:
            for out in (pathlib.Path('.'), work, work.parent):
                r = DirectoryRenderer(out, template=DirectoryTemplate(self.tpl))
                with self.assertRaises(UnsafePurgeError):
                    r.render()
        finally:
            os.chdir(cwd)
        self.assertEqual('keep me', read(work / 'precious.txt'))

    def test_purging_dir_containing_template_is_refused(self):
        write(self.tpl / 'new.txt', 'new')
        for out in (self.tpl, self.tmp):
            r = DirectoryRenderer(out, template=DirectoryTemplate(self.tpl))
            with self.assertRaises(UnsafePurgeError):
                r.render()
        self.assertEqual('new', read(self.tpl / 'new.txt'))

    def test_no_purge_into_cwd_is_allowed(self):
        write(self.tpl / 'new.txt', 'new')
        work = self.tmp / 'work'
        write(work / 'precious.txt', 'keep me')
        cwd = os.getcwd()
        os.chdir(work)
        try:
            DirectoryRenderer(work, template=DirectoryTemplate(self.tpl), purge=False).render()
        finally:
            os.chdir(cwd)
        self.assertEqual({'precious.txt': 'keep me', 'new.txt': 'new'}, tree(work))

    def test_unsafe_purge_is_a_render_error(self):
        self.assertTrue(issubclass(UnsafePurgeError, RenderError))


class TestStencilInfoInDirectories(_DirBase):
    INFO = ('version={{ __stencil__.version }}\n'
            'template_name={{ __stencil__.template_name }}\n'
            'template_path={{ __stencil__.template_path }}\n'
            'template_root={{ __stencil__.template_root }}\n'
            'source_dir={{ __stencil__.source_dir }}\n'
            'output_root={{ __stencil__.output_root }}\n'
            'output_dir={{ __stencil__.output_dir }}\n'
            'template_relative_path={{ __stencil__.template_relative_path }}\n'
            'loop={{ __stencil__.loop }}\n'
            'loops={{ __stencil__.loops }}\n')

    @staticmethod
    def parse(text: str) -> dict:
        return dict(line.split('=', 1) for line in text.splitlines())

    def test_info(self):
        import batstencil
        write(self.tpl / 'top.txt', self.INFO)
        write(self.tpl / 'sub' / 'deeper' / 'inner.txt', self.INFO)
        self.render()

        top = self.parse(read(self.out / 'top.txt'))
        self.assertEqual(batstencil.__version__, top['version'])
        self.assertEqual('top.txt', top['template_name'])
        self.assertEqual(self.tpl / 'top.txt', pathlib.Path(top['template_path']))
        self.assertEqual(self.tpl, pathlib.Path(top['template_root']))
        self.assertEqual(self.out, pathlib.Path(top['output_root']))
        self.assertEqual(pathlib.Path('.'), pathlib.Path(top['source_dir']))
        self.assertEqual(pathlib.Path('.'), pathlib.Path(top['output_dir']))
        self.assertEqual('top.txt', top['template_relative_path'])
        self.assertEqual('None', top['loop'])
        self.assertEqual('[]', top['loops'])

        inner = self.parse(read(self.out / 'sub' / 'deeper' / 'inner.txt'))
        self.assertEqual('inner.txt', inner['template_name'])
        self.assertEqual(self.tpl / 'sub' / 'deeper' / 'inner.txt', pathlib.Path(inner['template_path']))
        self.assertEqual(self.tpl, pathlib.Path(inner['template_root']))
        self.assertEqual(self.out, pathlib.Path(inner['output_root']))
        self.assertEqual('sub/deeper', inner['source_dir'])
        self.assertEqual('sub/deeper', inner['output_dir'])
        self.assertEqual('sub/deeper/inner.txt', inner['template_relative_path'])

    def test_output_dir_follows_renamed_dir(self):
        write(self.tpl / 'src' / '__stencil_meta__', '{% setfilename %}dst{% endsetfilename %}')
        write(self.tpl / 'src' / 'f.txt', self.INFO)
        self.render()
        info = self.parse(read(self.out / 'dst' / 'f.txt'))
        self.assertEqual('src', info['source_dir'])
        self.assertEqual('dst', info['output_dir'])

    def test_meta_has_info_too(self):
        write(self.tpl / 'sub' / '__stencil_meta__',
              '{% setfilename %}{{ __stencil__.template_name }}-{{ __stencil__.template_relative_path|replace("/", "_") }}'
              '{% endsetfilename %}')
        write(self.tpl / 'sub' / 'f.txt', 'x')
        self.render()
        self.assertEqual({'__stencil_meta__-sub___stencil_meta__/f.txt': 'x'}, tree(self.out))


class TestRepeatFor(_DirBase):
    def test_meta_repeats_directory(self):
        write(self.tpl / 'proto' / '__stencil_meta__',
              '{% repeat_for name in names %}{% setfilename %}svc_{{ name }}{% endsetfilename %}')
        write(self.tpl / 'proto' / 'file.txt', 'service {{ name }}')
        write(self.tpl / 'proto' / 'nested' / 'deep.txt', 'deep {{ name }}')
        res = self.render({'names': ['alpha', 'beta']})
        self.assertEqual({
            'svc_alpha/file.txt': 'service alpha',
            'svc_alpha/nested/deep.txt': 'deep alpha',
            'svc_beta/file.txt': 'service beta',
            'svc_beta/nested/deep.txt': 'deep beta',
        }, tree(self.out))
        self.assertEqual(['svc_alpha/file.txt', 'svc_alpha/nested/deep.txt',
                          'svc_beta/file.txt', 'svc_beta/nested/deep.txt'], self.rel(res))

    def test_meta_repeat_does_not_leak_loop_variable_to_siblings(self):
        write(self.tpl / 'proto' / '__stencil_meta__',
              '{% repeat_for name in names %}{% setfilename %}{{ name }}{% endsetfilename %}')
        write(self.tpl / 'proto' / 'f.txt', '[{{ name }}]')
        write(self.tpl / 'sibling' / 'f.txt', '[{{ name }}]')
        self.render({'names': ['a']})
        self.assertEqual('[a]', read(self.out / 'a' / 'f.txt'))
        self.assertEqual('[]', read(self.out / 'sibling' / 'f.txt'))

    def test_unpacking(self):
        write(self.tpl / 'dirs' / '__stencil_meta__',
              '{% repeat_for key, value in d.items() %}{% setfilename %}{{ key }}{% endsetfilename %}')
        write(self.tpl / 'dirs' / 'f.txt', '{{ key }}={{ value }}')
        self.render({'d': {'x': 1, 'y': 2}})
        self.assertEqual({'x/f.txt': 'x=1', 'y/f.txt': 'y=2'}, tree(self.out))

    def test_unpacking_wrong_size_raises(self):
        write(self.tpl / 'f.txt', '{% repeat_for a, b in items %}{% setfilename %}{{ a }}{% endsetfilename %}x')
        with self.assertRaises(TemplateRenderError):
            self.render({'items': [[1, 2], [3]]})

    def test_file_repeats(self):
        write(self.tpl / 'sub' / 'item.txt',
              '{% repeat_for item in items %}{% setfilename %}item_{{ item }}.txt{% endsetfilename %}'
              'This is {{ item }}')
        res = self.render({'items': ['one', 'two', 'three']})
        self.assertEqual({'sub/item_one.txt': 'This is one',
                          'sub/item_two.txt': 'This is two',
                          'sub/item_three.txt': 'This is three'}, tree(self.out))
        self.assertEqual(['sub/item_one.txt', 'sub/item_two.txt', 'sub/item_three.txt'], self.rel(res))

    def test_file_repeats_with_unpacking(self):
        write(self.tpl / 'kv.txt',
              '{% repeat_for k, v in d.items() %}{% setfilename %}{{ k }}.txt{% endsetfilename %}{{ k }}: {{ v }}')
        self.render({'d': {'a': 1, 'b': 2}})
        self.assertEqual({'a.txt': 'a: 1', 'b.txt': 'b: 2'}, tree(self.out))

    def test_loop_info(self):
        write(self.tpl / 'f.txt',
              '{% repeat_for x in items %}{% setfilename %}f{{ __stencil__.loop.index }}.txt{% endsetfilename %}'
              '{% set l = __stencil__.loop %}'
              '{{ l.index }} {{ l.index0 }} {{ l.first }} {{ l.last }} {{ l.length }} {{ l.item }} {{ x }}')
        self.render({'items': ['a', 'b', 'c']})
        self.assertEqual({
            'f1.txt': '1 0 True False 3 a a',
            'f2.txt': '2 1 False False 3 b b',
            'f3.txt': '3 2 False True 3 c c',
        }, tree(self.out))

    def test_loop_item_is_the_whole_item_when_unpacking(self):
        write(self.tpl / 'f.txt',
              '{% repeat_for k, v in d.items() %}{% setfilename %}{{ k }}{% endsetfilename %}{{ __stencil__.loop.item }}')
        self.render({'d': {'k1': 'v1'}})
        self.assertEqual("('k1', 'v1')", read(self.out / 'k1'))

    def test_nested_loops(self):
        write(self.tpl / 'outer' / '__stencil_meta__',
              '{% repeat_for o in outer %}{% setfilename %}{{ o }}{% endsetfilename %}')
        write(self.tpl / 'outer' / 'inner.txt',
              '{% repeat_for i in inner %}{% setfilename %}{{ o }}{{ i }}.txt{% endsetfilename %}'
              '{{ __stencil__.loops|length }} {{ __stencil__.loops[0].item }} {{ __stencil__.loops[1].item }}'
              ' {{ __stencil__.loop.item }} {{ __stencil__.loops[0].index }} {{ __stencil__.loops[1].index }}')
        write(self.tpl / 'outer' / 'plain.txt', '{{ __stencil__.loops|length }} {{ __stencil__.loop.item }}')
        self.render({'outer': ['A', 'B'], 'inner': [1, 2]})
        self.assertEqual({
            'A/A1.txt': '2 A 1 1 1 1',
            'A/A2.txt': '2 A 2 2 1 2',
            'A/plain.txt': '1 A',
            'B/B1.txt': '2 B 1 1 2 1',
            'B/B2.txt': '2 B 2 2 2 2',
            'B/plain.txt': '1 B',
        }, tree(self.out))

    def test_nested_directory_loops(self):
        write(self.tpl / 'a' / '__stencil_meta__',
              '{% repeat_for x in xs %}{% setfilename %}x{{ x }}{% endsetfilename %}')
        write(self.tpl / 'a' / 'b' / '__stencil_meta__',
              '{% repeat_for y in ys %}{% setfilename %}y{{ y }}{% endsetfilename %}')
        write(self.tpl / 'a' / 'b' / 'f.txt', '{{ x }}{{ y }}')
        self.render({'xs': [1, 2], 'ys': ['p', 'q']})
        self.assertEqual({'x1/yp/f.txt': '1p', 'x1/yq/f.txt': '1q',
                          'x2/yp/f.txt': '2p', 'x2/yq/f.txt': '2q'}, tree(self.out))

    def test_duplicate_names_raise(self):
        write(self.tpl / 'f.txt', '{% repeat_for x in items %}{{ x }}')
        with self.assertRaises(TemplateRenderError) as cm:
            self.render({'items': [1, 2]})
        self.assertIn('f.txt', str(cm.exception))
        self.assertIn('f.txt', cm.exception.template_path)

    def test_duplicate_names_via_setfilename_raise(self):
        write(self.tpl / 'f.txt', '{% repeat_for x in items %}{% setfilename %}same.txt{% endsetfilename %}{{ x }}')
        with self.assertRaises(TemplateRenderError):
            self.render({'items': [1, 2]})

    def test_duplicate_directory_names_raise(self):
        write(self.tpl / 'd' / '__stencil_meta__', '{% repeat_for x in items %}')
        write(self.tpl / 'd' / 'f.txt', 'x')
        with self.assertRaises(TemplateRenderError):
            self.render({'items': [1, 2]})

    def test_single_item_without_setfilename_is_ok(self):
        write(self.tpl / 'f.txt', '{% repeat_for x in items %}{{ x }}')
        self.render({'items': ['only']})
        self.assertEqual({'f.txt': 'only'}, tree(self.out))

    def test_empty_list_renders_nothing(self):
        write(self.tpl / 'f.txt', '{% repeat_for x in items %}{{ x }}')
        write(self.tpl / 'd' / '__stencil_meta__', '{% repeat_for x in items %}{% setfilename %}{{ x }}{% endsetfilename %}')
        write(self.tpl / 'd' / 'g.txt', 'g')
        write(self.tpl / 'keep.txt', 'keep')
        res = self.render({'items': []})
        self.assertEqual({'keep.txt': 'keep'}, tree(self.out))
        self.assertEqual(['keep.txt'], self.rel(res))
        self.assertFalse((self.out / 'd').exists())

    def test_undefined_list_renders_nothing(self):
        write(self.tpl / 'f.txt', '{% repeat_for x in nothing_here %}{{ x }}')
        self.assertEqual([], self.render())

    def test_skip_if_inside_repeated_file(self):
        write(self.tpl / 'f.txt',
              '{% repeat_for x in items %}{% setfilename %}f{{ x }}{% endsetfilename %}{% skip_if x == 2 %}{{ x }}')
        self.render({'items': [1, 2, 3]})
        self.assertEqual({'f1': '1', 'f3': '3'}, tree(self.out))

    def test_repeat_for_in_string_render_raises(self):
        with self.assertRaises(RenderError):
            render_stencil('{% repeat_for x in [1, 2] %}{{ x }}')
        with self.assertRaises(RenderError):
            render_stencil('{% repeat_for x in items %}{{ x }}', {'items': [1]})

    def test_repeat_for_bad_target_is_a_syntax_error(self):
        with self.assertRaises(jinja2.TemplateSyntaxError):
            render_stencil('{% repeat_for x.y in [1] %}')
