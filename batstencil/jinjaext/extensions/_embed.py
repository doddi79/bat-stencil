__all__ = [
    'EmbedExtension',
]

from jinja2 import nodes
from jinja2.ext import Extension
from batstencil.structs import *


class EmbedExtension(Extension):
    """Adds the `{% embed 'file' %}` tag that embeds a file "as-is" (not as a
    template), with these optional arguments:

    - `indent=N` to indent every line by N spaces (e.g. for YAML)
    - `allconf=True` to render the file with AllConf first (`alviss=True` is a
      deprecated alias), along with `env=True`, `fidelius=True` and `py=True`
      to resolve `${__ENV__:...}`, `${__FID__:...}` and `${__PY__:...}`
      expressions
    """
    tags = {'embed'}

    def __init__(self, environment):
        super().__init__(environment)
        environment.extend(stencil_renderer=None)

    @property
    def renderer(self) -> IRenderer:
        return self.environment.stencil_renderer  # noqa

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        args = [parser.parse_expression()]
        source_file = parser.filename
        kwargs = [nodes.Keyword('source_file', nodes.Const(source_file))]
        while parser.stream.skip_if('comma'):
            key = parser.stream.expect('name').value
            parser.stream.expect('assign')
            value = parser.parse_expression()
            kwargs.append(nodes.Keyword(key, value))

        return nodes.CallBlock(self.call_method('_render_embed', args, kwargs), [], [], []).set_lineno(lineno)

    def _render_embed(self, file_path, source_file: Optional[str] = None, indent: int = 0,
                      caller=None, **kwargs):

        # Check if file_path is a variable in the context
        if callable(file_path):
            file_path = file_path()

        content = self.renderer.get_embed(file_path, source_file=source_file, **kwargs)

        indent_str = ' ' * int(indent or 0)

        return f'{indent_str}{indent_str.join(content.splitlines(True))}\n'
