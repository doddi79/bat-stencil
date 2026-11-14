__all__ = [
    'FileRenderer',
]

from batstencil.structs import *
from pathlib import Path
from ._string import *
import logging
log = logging.getLogger(__name__)


class FileRenderer(StringRenderer):
    """Renders the template to a file.

    The `output_path` is treated as a directory if it ends with a slash (or
    backslash) or is an existing directory, in which case the file name is the
    one set via the `{% setfilename %}` tag or else the template's file name.
    Otherwise it's the file to write (unless `{% setfilename %}` overrides the
    name).

    `render()` returns the absolute path of the file written, or `None` if
    rendering was skipped via `{% skip_if %}`.
    """
    def __init__(self, output_path: T_PATH,
                 context: Optional[IContext] = None, template: Optional[ITemplate] = None,
                 overwrite: bool = True,
                 new_line_char: str = '\n',
                 **kwargs):
        self._overwrite = overwrite
        self._new_line_char = new_line_char
        self._explicit_file_name: Optional[str] = None
        super().__init__(context, template, **kwargs)
        log.debug(f'{output_path=}')
        is_dir = False
        if isinstance(output_path, str):
            if output_path.endswith('\\') or output_path.endswith('/'):
                is_dir = True
            output_path = Path(output_path)
        if output_path.is_dir():
            is_dir = True

        if not is_dir:
            self._explicit_file_name = str(output_path.name)
            self._output_path = output_path.parent
        else:
            self._output_path = output_path

        log.debug(f'{self._output_path=}')
        log.debug(f'{self.output_file_name=}')

    def render(self) -> Optional[str]:
        return super().render()

    def _output_rendered_results(self, rendered_string: str) -> str:
        fout_path = self.output_file()
        if fout_path.exists() and not self._overwrite:
            raise OutputFileExistsError(f'The target output file already exists and overwriting is'
                                        f' disabled: {fout_path.absolute()}')
        fout_path.parent.mkdir(parents=True, exist_ok=True)

        with open(fout_path, 'w', newline=self._new_line_char, encoding='utf-8') as fout:
            fout.write(rendered_string)
        return str(fout_path.absolute())

    def output_file(self) -> Path:
        name = self.output_file_name
        if name is None:
            raise NoOutputFileNameError('no output file name set or found')
        return self._output_path / Path(name)

    def _default_output_file_name(self) -> Optional[str]:
        return self._explicit_file_name or super()._default_output_file_name()
