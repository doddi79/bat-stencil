__all__ = [
    'FileTemplate',
]

from batstencil.structs import *
from pathlib import Path

from ._base import *


class FileTemplate(_BaseTemplate):
    """A template file.

    If `file_path` is a `str` it's first looked up as a template name in the
    renderer's search paths (the current working directory, the script's
    directory and the `STENCIL_TEMPLATE_PATH` environment variable), otherwise
    it's read as a path.
    """
    def __init__(self, file_path: T_PATH, **kwargs):
        super().__init__(**kwargs)
        self._file_path: T_PATH = file_path

    @property
    def file_name(self) -> str:
        return str(self.get_file_path().name)

    def _read_file(self) -> str:
        as_path = self.get_file_path()

        if not as_path.is_file():
            raise TemplateNotFoundError(f'File {as_path} does not exist')

        with open(as_path, 'r', encoding='utf-8') as fin:
            return fin.read()

    def get_file_path(self) -> Path:
        if isinstance(self._file_path, str):
            return Path(self._file_path)
        return self._file_path

    def get_jinja_template(self) -> jinja2.Template:
        env = self.renderer.jinja_environment
        if isinstance(self._file_path, str):
            try:
                return env.get_template(self._file_path)
            except jinja2.exceptions.TemplateNotFound:
                pass
        path = self.get_file_path()
        # Compiling with the file name (instead of `from_string`) gives errors
        # and tracebacks the template's file name and lets `{% embed %}` find
        # files relative to the template
        code = env.compile(self._read_file(), name=path.name, filename=str(path.absolute()))
        return env.template_class.from_code(env, code, env.make_globals(None))
