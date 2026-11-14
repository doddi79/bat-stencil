__all__ = [
    'DirectoryRenderer',
]

from batstencil.structs import *
from pathlib import Path

from ._base import *
from ._string import *
from batstencil.template import DirectoryTemplate, FileTemplate
import shutil
import logging

log = logging.getLogger(__name__)


class _Instance(NamedTuple):
    """One rendering of a template (there are several with `{% repeat_for %}`)"""
    result: Optional[str]  # None if skipped via `{% skip_if %}`
    file_name: Optional[str]  # From `{% setfilename %}` (if any)
    extra_context: Dict[str, Any]
    loops: List[Dict[str, Any]]


class DirectoryRenderer(_BaseRenderer):
    """Renders an entire `DirectoryTemplate` (a directory tree of templates)
    into the `output_path` directory.

    - Every file is rendered as a template (with `{% skip_if %}`,
      `{% setfilename %}` and `{% repeat_for %}` support)
    - A `__stencil_meta__` file in a (non root) directory is rendered to decide
      the directory's name (`{% setfilename %}`), whether to skip it
      (`{% skip_if %}`) and whether to render it once per item in a list
      (`{% repeat_for %}`)
    - The `__stencil__` variable in templates has info about the template being
      rendered (paths, names and `{% repeat_for %}` loop info)

    `render()` returns the list of absolute paths of the files written.

    If `purge` is set (the default) the output path is deleted before
    rendering, unless it's a path that should never be deleted (the current
    working directory or any of its parents, the home directory, a file system
    root or a path containing the template), in which case `UnsafePurgeError`
    is raised.
    """
    _VALID_TEMPLATES = (DirectoryTemplate,)

    def __init__(self, output_path: T_PATH,
                 context: Optional[IContext] = None,
                 template: Optional[DirectoryTemplate] = None,
                 overwrite: bool = True,
                 purge: bool = True,
                 new_line_char: str = '\n',
                 **kwargs):
        self._overwrite = overwrite
        self._purge = purge
        self._new_line_char = new_line_char
        self._output_path: Path = Path(output_path)
        self._rendered: List[str] = []
        super().__init__(context, template, **kwargs)

    @property
    def output_path(self) -> Path:
        return self._output_path

    # ---------------------------------------------------------------- Output root

    def _ensure_root(self):
        self._do_purge()
        if not self._output_path.exists():
            log.debug(f'Creating target output root path: {self._output_path}...')
            self._output_path.mkdir(parents=True, exist_ok=True)

    def _check_purge_is_safe(self):
        out = self._output_path.resolve()
        reason = None
        cwd = Path.cwd().resolve()
        tpl = self.template.absolute_source_path.resolve()  # noqa
        if out == Path(out.anchor):
            reason = 'it is a file system root'
        elif out == Path.home().resolve():
            reason = 'it is the home directory'
        elif out == cwd or out in cwd.parents:
            reason = 'it is the current working directory (or one of its parents)'
        elif out == tpl or out in tpl.parents:
            reason = 'it contains the template directory'
        if reason:
            raise UnsafePurgeError(f'Refusing to purge the output path {out} because {reason}.'
                                   f' Use another output path or disable purging (--no-purge / purge=False)')

    def _do_purge(self):
        if self._purge:
            if self._output_path.exists():
                if not self._overwrite:
                    raise OutputFileExistsError(f'Purge is enabled but the target output path already exists and overwriting is disabled: {self._output_path}')
                self._check_purge_is_safe()
                log.debug(f'Purging output path: {self._output_path}...')
                shutil.rmtree(self._output_path.absolute(), ignore_errors=True)

    # ---------------------------------------------------------------- Rendering

    def render(self) -> List[str]:
        self._pre_flight()
        self._rendered = []
        self._ensure_root()
        self._render_dir(self.template, Path('.'), {}, [])  # noqa
        return list(self._rendered)

    def _make_info(self, dir_template: DirectoryTemplate, target_dir: Path,
                   loops: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            'template_root': str(self.template.absolute_source_path),  # noqa
            'source_dir': dir_template.source_path.as_posix(),
            'output_root': str(self._output_path.absolute()),
            'output_dir': target_dir.as_posix(),
            'loop': loops[-1] if loops else None,
            'loops': list(loops),
        }

    def _string_renderer(self, template: FileTemplate, extra_context: Dict[str, Any],
                         info: Dict[str, Any], repeat_mode: str) -> StringRenderer:
        r = StringRenderer(context=self.context, template=template)
        r.extra_context = dict(extra_context)
        r.stencil_info = dict(info)
        r.repeat_mode = repeat_mode
        return r

    @staticmethod
    def _run(renderer: StringRenderer) -> Optional[str]:
        try:
            return renderer.render()
        except (StencilError, RepeatRendering):
            raise
        except Exception as ex:
            path = renderer.describe_template()
            line = f' (line {ex.lineno})' if getattr(ex, 'lineno', None) else ''
            raise TemplateRenderError(f'Failed to render template {path}{line}: {ex.__class__.__name__}: {ex}',
                                      template_path=path) from ex

    @staticmethod
    def _unpack(names: List[str], item: Any, template: FileTemplate) -> Dict[str, Any]:
        if len(names) == 1:
            return {names[0]: item}
        try:
            values = list(item)
        except TypeError:
            values = None
        if values is None or len(values) != len(names):
            raise TemplateRenderError(f'Can not unpack {item!r} into {", ".join(names)} in the repeat_for tag'
                                      f' of {template.get_file_path()}', str(template.get_file_path()))
        return dict(zip(names, values))

    def _render_instances(self, template: FileTemplate, dir_template: DirectoryTemplate, target_dir: Path,
                          extra_context: Dict[str, Any], loops: List[Dict[str, Any]],
                          relative_path: str) -> List[_Instance]:
        def _info(loop_list):
            info = self._make_info(dir_template, target_dir, loop_list)
            info['template_relative_path'] = relative_path
            return info

        r = self._string_renderer(template, extra_context, _info(loops), 'raise')
        try:
            result = self._run(r)
            return [_Instance(result, r._output_file_name, extra_context, loops)]  # noqa
        except RepeatRendering as rep:
            items = rep.items
            log.debug(f'Repeating {relative_path} for {len(items)} items')
            instances = []
            for i, item in enumerate(items):
                loop = {
                    'index': i + 1,
                    'index0': i,
                    'first': i == 0,
                    'last': i == len(items) - 1,
                    'length': len(items),
                    'item': item,
                }
                new_extra = dict(extra_context)
                new_extra.update(self._unpack(rep.target_names, item, template))
                new_loops = loops + [loop]
                r = self._string_renderer(template, new_extra, _info(new_loops), 'ignore')
                result = self._run(r)
                instances.append(_Instance(result, r._output_file_name, new_extra, new_loops))  # noqa

            names = [i.file_name for i in instances if i.result is not None]
            if len(set(names)) != len(names):
                raise TemplateRenderError(f'The repeat_for tag in {template.get_file_path()} renders more than one'
                                          f' copy with the same name ({", ".join(str(n) for n in names)}),'
                                          f' use the setfilename tag to give each one a unique name',
                                          str(template.get_file_path()))
            return instances

    def _safe_target(self, relative: Path, template: FileTemplate) -> Path:
        root = self._output_path.absolute().resolve()
        target = (root / relative).resolve()
        if target != root and root not in target.parents:
            raise TemplateRenderError(f'Output path {relative} (from {template.get_file_path()}) is outside'
                                      f' of the output directory {root}', str(template.get_file_path()))
        return target

    def _write(self, relative: Path, content: str, template: FileTemplate):
        target = self._safe_target(relative, template)
        if target.exists() and not self._overwrite:
            raise OutputFileExistsError(f'The target output file already exists and overwriting is'
                                        f' disabled: {target}')
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, 'w', newline=self._new_line_char, encoding='utf-8') as fout:
            fout.write(content)
        log.debug(f'Rendered: {relative}')
        self._rendered.append(str(target))

    def _render_dir(self, dir_template: DirectoryTemplate, target_dir: Path,
                    extra_context: Dict[str, Any], loops: List[Dict[str, Any]]):
        for f in dir_template.files:
            relative_path = (dir_template.source_path / f.file_name).as_posix()
            for inst in self._render_instances(f, dir_template, target_dir, extra_context, loops, relative_path):
                if inst.result is None:
                    log.debug(f'Skipped rendering {relative_path} due to skip_if tag...')
                    continue
                self._write(target_dir / (inst.file_name or f.file_name), inst.result, f)

        for d in dir_template.directories:
            meta = d.meta_template
            if meta is None:
                instances = [_Instance('', None, extra_context, loops)]
            else:
                meta.set_renderer(self)
                relative_path = (d.source_path / DirectoryTemplate.META_FILE_NAME).as_posix()
                instances = self._render_instances(meta, d, target_dir, extra_context, loops, relative_path)

            for inst in instances:
                if inst.result is None:
                    log.debug(f'Skipping directory {d.source_path.as_posix()} due to skip_if tag...')
                    continue
                sub_dir = target_dir / (inst.file_name or d.source_name)
                full_path = self._safe_target(sub_dir, meta or FileTemplate(d.absolute_source_path))
                log.debug(f'Creating directory: {full_path}...')
                full_path.mkdir(parents=True, exist_ok=True)
                self._render_dir(d, sub_dir, inst.extra_context, inst.loops)

    def _output_rendered_results(self, rendered_string: str) -> str:
        raise NotImplementedError('DirectoryRenderer renders directories via render()')

    def _render_as_string(self) -> str:
        raise NotImplementedError('DirectoryRenderer renders directories via render()')

    @property
    def output_file_name(self) -> Optional[str]:
        return None

    @output_file_name.setter
    def output_file_name(self, value: str):
        pass
