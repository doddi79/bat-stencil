import contextlib
import io
import os
import pathlib
import tempfile
import unittest
from unittest import mock

import batstencil
from batstencil.cli.bat_stencil.main import main


def write(path: pathlib.Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as fout:
        fout.write(content)


def run_cli(*args):
    """Runs the CLI, returns (exit code or None, stdout, stderr)"""
    out, err = io.StringIO(), io.StringIO()
    code = None
    with mock.patch('sys.argv', ['bat-stencil', *args]), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            main()
        except SystemExit as e:
            code = e.code
    return code, out.getvalue(), err.getvalue()


class TestCli(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = pathlib.Path(self._tmp.name)

    def test_string_template_with_arg(self):
        code, out, err = run_cli('-s', 'Hi {{a.b}}', '-a', 'a.b=3')
        self.assertIsNone(code)
        self.assertEqual('Hi 3\n', out)
        self.assertEqual('', err)

    def test_multiple_args_and_value_with_equals(self):
        code, out, err = run_cli('-s', '{{x}}|{{y}}', '-a', 'x=1', '-a', 'y=a=b')
        self.assertIsNone(code)
        self.assertEqual('1|a=b\n', out)

    def test_bad_arg_exits_3(self):
        code, out, err = run_cli('-s', 'Hi {{a}}', '-a', 'bad')
        self.assertEqual(3, code)
        self.assertEqual('', out)
        self.assertIn('bad', err)

    def test_empty_arg_key_exits_3(self):
        code, out, err = run_cli('-s', 'Hi', '-a', '=value')
        self.assertEqual(3, code)

    def test_version(self):
        code, out, err = run_cli('--version')
        self.assertEqual(0, code)
        self.assertIn(batstencil.__version__, out + err)

    def test_directory_without_output_exits_3(self):
        tpl = self.tmp / 'tpl'
        write(tpl / 'f.txt', 'x')
        code, out, err = run_cli('-d', str(tpl))
        self.assertEqual(3, code)
        self.assertIn('output', err.lower())

    def test_no_template_option_is_a_usage_error(self):
        code, out, err = run_cli('-a', 'a=1')
        self.assertEqual(2, code)

    def test_input_file(self):
        ctx = self.tmp / 'ctx.yaml'
        write(ctx, 'app:\n  name: from_file\n  other: x\n')
        code, out, err = run_cli('-s', '{{app.name}} {{app.other}}', '-i', str(ctx), '-a', 'app.other=y')
        self.assertIsNone(code)
        self.assertEqual('from_file y\n', out)

    def test_template_file_to_output_file(self):
        tpl = self.tmp / 'tpl.txt'
        write(tpl, 'Hello {{who}}')
        target = self.tmp / 'out' / 'result.txt'
        code, out, err = run_cli('-t', str(tpl), '-o', str(target), '-a', 'who=you')
        self.assertIsNone(code)
        self.assertIn('Wrote file:', out)
        self.assertTrue(out.strip().endswith('result.txt'))
        with open(target, 'r', encoding='utf-8') as fin:
            self.assertEqual('Hello you', fin.read())

    def test_skipped_output(self):
        target = self.tmp / 'result.txt'
        code, out, err = run_cli('-s', '{% skip_if true %}x', '-o', str(target))
        self.assertIsNone(code)
        self.assertIn('Skipped', out)
        self.assertFalse(target.exists())

    def test_no_overwrite(self):
        target = self.tmp / 'result.txt'
        write(target, 'old')
        code, out, err = run_cli('-s', 'new', '-o', str(target), '--no-overwrite')
        self.assertEqual(3, code)
        with open(target, 'r', encoding='utf-8') as fin:
            self.assertEqual('old', fin.read())

    def test_template_syntax_error_exits_3(self):
        code, out, err = run_cli('-s', '{{ foo }')
        self.assertEqual(3, code)
        self.assertIn('Template error', err)

    def test_directory_render(self):
        tpl = self.tmp / 'tpl'
        write(tpl / 'top.txt', 'top {{name}}')
        write(tpl / 'sub' / 'renamed.txt', '{% setfilename %}real_{{name}}.txt{% endsetfilename %}sub {{name}}')
        write(tpl / 'sub' / 'plain.txt', 'plain')
        ctx = self.tmp / 'ctx.yaml'
        write(ctx, 'name: Dir\n')
        out_dir = self.tmp / 'out'

        code, out, err = run_cli('-i', str(ctx), '-d', str(tpl), '-o', str(out_dir))
        self.assertIsNone(code, err)

        lines = [ln for ln in out.splitlines() if ln.startswith('Wrote file:')]
        self.assertEqual(3, len(lines), out)
        written = [pathlib.Path(ln[len('Wrote file:'):].strip()) for ln in lines]
        self.assertEqual(['top.txt', 'plain.txt', 'real_Dir.txt'], [p.name for p in written])
        for p in written:
            self.assertTrue(p.is_file(), p)
        self.assertFalse((out_dir / 'sub' / 'renamed.txt').exists())
        with open(out_dir / 'sub' / 'real_Dir.txt', 'r', encoding='utf-8') as fin:
            self.assertEqual('sub Dir', fin.read())

    def test_directory_render_purges_by_default_and_no_purge_keeps(self):
        tpl = self.tmp / 'tpl'
        write(tpl / 'f.txt', 'x')
        out_dir = self.tmp / 'out'
        write(out_dir / 'old.txt', 'old')

        code, out, err = run_cli('-d', str(tpl), '-o', str(out_dir), '--no-purge')
        self.assertIsNone(code, err)
        self.assertTrue((out_dir / 'old.txt').exists())

        code, out, err = run_cli('-d', str(tpl), '-o', str(out_dir))
        self.assertIsNone(code, err)
        self.assertFalse((out_dir / 'old.txt').exists())
        self.assertTrue((out_dir / 'f.txt').exists())

    def test_directory_render_refuses_to_purge_cwd(self):
        tpl = self.tmp / 'tpl'
        write(tpl / 'f.txt', 'x')
        work = self.tmp / 'work'
        write(work / 'precious.txt', 'keep')
        cwd = os.getcwd()
        os.chdir(work)
        try:
            code, out, err = run_cli('-d', str(tpl), '-o', '.')
        finally:
            os.chdir(cwd)
        self.assertEqual(3, code)
        self.assertTrue((work / 'precious.txt').exists())

    def test_directory_template_error_exits_3(self):
        tpl = self.tmp / 'tpl'
        write(tpl / 'broken.txt', '{{ foo }')
        code, out, err = run_cli('-d', str(tpl), '-o', str(self.tmp / 'out'))
        self.assertEqual(3, code)
        self.assertIn('broken.txt', err)
