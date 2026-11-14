__all__ = [
    'SkipIfExtension',
]
from jinja2 import nodes
from jinja2.ext import Extension
from batstencil.structs import *


class SkipIfExtension(Extension):
    """Adds the `{% skip_if <condition> %}` tag that skips rendering the
    template (or directory, in `__stencil_meta__` files) if the condition is
    true."""
    tags = {'skip_if'}

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        # Parse the condition expression
        condition = parser.parse_expression()
        return nodes.CallBlock(self.call_method('_check_condition', [condition]), [], [], []).set_lineno(lineno)

    def _check_condition(self, condition, caller):
        if condition:
            raise CancelRendering('Rendering cancelled due to a skip_if condition being true')
        return ''
