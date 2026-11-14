__all__ = [
    'SetFilenameExtension',
]

from jinja2 import nodes
from jinja2.ext import Extension
from batstencil.structs import *
import logging
log = logging.getLogger(__name__)


class SetFilenameExtension(Extension):
    """Adds the `{% setfilename %}...{% endsetfilename %}` tag that sets the
    name of the rendered file (or directory, in `__stencil_meta__` files) to
    whatever its body renders as (stripped)."""
    tags = {'setfilename'}

    def __init__(self, environment):
        super().__init__(environment)
        environment.extend(stencil_renderer=None)

    @property
    def renderer(self) -> IRenderer:
        return self.environment.stencil_renderer  # noqa

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        body = parser.parse_statements(('name:endsetfilename',), drop_needle=True)
        return nodes.CallBlock(self.call_method('_set_filename', [nodes.Const(parser.filename)]),
                               [], [], body).set_lineno(lineno)

    def _set_filename(self, source_file: Optional[str], caller):
        name = caller().strip()
        if not name:
            log.warning(f'The setfilename tag in {source_file or "a template"} rendered an empty file name'
                        f' (check the template code and context), so it is ignored and the default name is used')
        self.renderer.output_file_name = name
        return ''
