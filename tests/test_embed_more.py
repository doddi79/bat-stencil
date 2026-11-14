import unittest

from batstencil.stencils import *
from batstencil.structs import *

import os
import pathlib
import tempfile

_HERE = pathlib.Path(__file__).parent.resolve()


def fp(file_name: str) -> str:
    return str((_HERE / 'res/embed/' / file_name).absolute())


def read_expected(file_name: str) -> str:
    with open(fp(f'expected/{file_name}'), 'r', newline=None, encoding='utf-8') as fin:
        return fin.read()


def write(path: pathlib.Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as fout:
        fout.write(content)


class TestEmbedMore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ['STENCIL_TEMPLATE_PATH'] = str(_HERE / 'res/embed/')
        os.environ['ENVIRONMENT_VARIABLE_FORTY_TWO'] = '42'

    @classmethod
    def tearDownClass(cls):
        for k in ('STENCIL_TEMPLATE_PATH', 'ENVIRONMENT_VARIABLE_FORTY_TWO'):
            if k in os.environ:
                del os.environ[k]

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = pathlib.Path(self._tmp.name)

    def test_allconf_embed_matches_legacy_alviss_embed(self):
        legacy = render_stencil('template_alviss.yaml', fp('context.yaml'))
        res = render_stencil('template_allconf.yaml', fp('context.yaml'))
        self.assertEqual(legacy, res)
        self.assertEqual(read_expected('alviss.yaml'), res)

    def test_allconf_embed_with_env(self):
        res = render_stencil("{% embed 'alviss_embed.yaml', allconf=True, env=True %}", fp('context.yaml'))
        self.assertIn("value: '42'", res)
        res = render_stencil("{% embed 'alviss_embed.yaml', allconf=True %}", fp('context.yaml'))
        self.assertNotIn("'42'", res)

    def test_plain_embed_is_not_rendered_with_allconf(self):
        write(self.tmp / 'conf.yaml', 'a: 1\nb: ${a}\n')
        res = render_stencil(f"{{% embed '{(self.tmp / 'conf.yaml').as_posix()}' %}}")
        self.assertEqual('a: 1\nb: ${a}\n\n', res)
        res = render_stencil(f"{{% embed '{(self.tmp / 'conf.yaml').as_posix()}', allconf=True %}}")
        self.assertIn('b: 1', res)

    def test_embed_relative_to_the_template_directory(self):
        # The template's directory is NOT in STENCIL_TEMPLATE_PATH (nor the cwd)
        write(self.tmp / 'tpl' / 'main.txt', "before\n{% embed 'sibling.txt' %}after")
        write(self.tmp / 'tpl' / 'sibling.txt', 'sibling content')
        res = render_stencil(self.tmp / 'tpl' / 'main.txt')
        self.assertEqual('before\nsibling content\nafter', res)

    def test_embed_relative_subdirectory_of_template(self):
        write(self.tmp / 'tpl' / 'main.txt', "{% embed 'sub/inner.txt', indent=2 %}")
        write(self.tmp / 'tpl' / 'sub' / 'inner.txt', 'one\ntwo')
        res = render_stencil(self.tmp / 'tpl' / 'main.txt')
        self.assertEqual('  one\n  two\n', res)

    def test_embed_in_directory_template_is_relative_to_each_file(self):
        write(self.tmp / 'tpl' / 'sub' / 'main.txt', "{% embed 'data.txt' %}")
        write(self.tmp / 'tpl' / 'sub' / 'data.txt', 'sub data')
        out = self.tmp / 'out'
        DirectoryRenderer(out, template=DirectoryTemplate(self.tmp / 'tpl')).render()
        with open(out / 'sub' / 'main.txt', 'r', encoding='utf-8') as fin:
            self.assertEqual('sub data\n', fin.read())

    def test_embed_absolute_path(self):
        write(self.tmp / 'abs.txt', 'absolute')
        res = render_stencil(f"{{% embed '{(self.tmp / 'abs.txt').as_posix()}' %}}")
        self.assertEqual('absolute\n', res)

    def test_missing_file_raises(self):
        with self.assertRaises(EmbedFileNotFound):
            render_stencil("{% embed 'no_such_file.txt' %}")

    def test_missing_file_next_to_template_raises(self):
        write(self.tmp / 'tpl' / 'main.txt', "{% embed 'missing.txt' %}")
        with self.assertRaises(EmbedFileNotFound):
            render_stencil(self.tmp / 'tpl' / 'main.txt')

    def test_missing_absolute_file_raises(self):
        with self.assertRaises(EmbedFileNotFound):
            render_stencil(f"{{% embed '{(self.tmp / 'nope.txt').as_posix()}' %}}")

    def test_embed_file_not_found_is_a_file_not_found_error(self):
        self.assertTrue(issubclass(EmbedFileNotFound, FileNotFoundError))
        self.assertTrue(issubclass(EmbedFileNotFound, RenderError))
