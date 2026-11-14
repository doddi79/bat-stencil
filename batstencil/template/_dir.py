__all__ = [
    'DirectoryTemplate',
]

from batstencil.structs import *
from pathlib import Path

from ._base import *
from ._file import *

import logging
log = logging.getLogger(__name__)


class DirectoryTemplate(_BaseTemplate):
    """A directory tree of templates (rendered with the `DirectoryRenderer`).

    Every file is a template, except `__stencil_meta__` files, which control
    the name of the directory they're in, whether it's skipped and whether it's
    rendered once per item in a list (not allowed in the root directory).
    """
    META_FILE_NAME = '__stencil_meta__'

    def __init__(self, dir_path: T_PATH, parent: Optional['DirectoryTemplate'] = None, **kwargs):
        super().__init__(**kwargs)
        self._dir_path: Path = Path(dir_path)

        if not self._dir_path.exists():
            raise TemplateNotFoundError(f'Template root does not exist: {self._dir_path}')

        if not self._dir_path.is_dir():
            raise TemplateNotFoundError(f'Template root is not a directory: {self._dir_path}')

        self._directories: List[DirectoryTemplate] = []
        self._files: List[FileTemplate] = []
        self._meta_file: Optional[Path] = None

        self._parent = parent

        self._crawl()

    @property
    def is_root(self) -> bool:
        return self._parent is None

    @property
    def parent(self) -> Optional['DirectoryTemplate']:
        return self._parent

    @property
    def absolute_source_path(self) -> Path:
        """This is the full absolute path to the source template directory!"""
        if self.is_root:
            return self._dir_path.absolute()
        return self._parent.absolute_source_path / self.source_name

    @property
    def source_path(self) -> Path:
        """This is the relative path to the source template directory!"""
        if self.is_root:
            return Path('.')
        return self._parent.source_path / self.source_name

    @property
    def source_name(self) -> str:
        """This is name of the source template directory!"""
        return self._dir_path.name

    def set_renderer(self, renderer: IRenderer):
        super().set_renderer(renderer)
        for d in self._directories:
            d.set_renderer(renderer)

    @property
    def meta_file(self) -> Optional[Path]:
        return self._meta_file

    @property
    def meta_template(self) -> Optional[FileTemplate]:
        if self._meta_file:
            return FileTemplate(file_path=self._meta_file.absolute())
        return None

    @property
    def directories(self) -> List['DirectoryTemplate']:
        return self._directories

    @property
    def files(self) -> List['FileTemplate']:
        return self._files

    def _crawl(self):
        for i in sorted(self._dir_path.iterdir(), key=lambda p: p.name):
            if i.is_dir():
                self._directories.append(DirectoryTemplate(i, parent=self))
            else:
                if i.name == self.META_FILE_NAME:
                    if self._parent is None:
                        raise TemplateError(f'The {self.META_FILE_NAME} file is not allowed in the template root directory')
                    self._meta_file = i
                else:
                    log.debug(f'Adding {self.absolute_source_path} / {i.name}')
                    self._files.append(FileTemplate(self.absolute_source_path / i.name))

    def dump_lines(self) -> List[str]:
        s = []
        if self._parent is None:
            s.append('I AM ROOT:')

        for d in self._directories:
            s.append(f'+- {d.source_name}/{" [meta]" if d.meta_file else ""}')
            for x in d.dump_lines():
                s.append(f'|     {x}')
        for f in self._files:
            s.append(f'+- {f.file_name} [{f.get_file_path()}]')
        return s

    def dump(self) -> str:
        return '\n'.join(self.dump_lines())

    def get_jinja_template(self) -> jinja2.Template:
        raise TemplateError('A DirectoryTemplate is not a single template (use the DirectoryRenderer)')
