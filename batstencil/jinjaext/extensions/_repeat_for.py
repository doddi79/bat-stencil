__all__ = [
    'RepeatForExtension',
]
from jinja2 import nodes
from jinja2.ext import Extension
from batstencil.structs import *


class RepeatForExtension(Extension):
    """Adds the `{% repeat_for item in items %}` tag (also
    `{% repeat_for key, value in some_dict.items() %}`) that makes the
    `DirectoryRenderer` render the template, or the directory when used in a
    `__stencil_meta__` file, once per item, with the loop variable(s) added to
    the context (and loop info in `__stencil__.loop`).

    Use `{% setfilename %}` along with it to give each copy a unique name.
    """
    tags = {'repeat_for'}

    def __init__(self, environment):
        super().__init__(environment)
        environment.extend(stencil_renderer=None)

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        target = parser.parse_assign_target(extra_end_rules=('name:in',))
        if isinstance(target, nodes.Name):
            names = [target.name]
        elif isinstance(target, nodes.Tuple) and all(isinstance(n, nodes.Name) for n in target.items):
            names = [n.name for n in target.items]
        else:
            parser.fail('repeat_for expects a variable name (or names) like: repeat_for item in items', lineno)
        parser.stream.expect('name:in')
        iterable = parser.parse_expression()
        return nodes.CallBlock(self.call_method('_repeat_for', [nodes.Const(names), iterable]),  # noqa
                               [], [], []).set_lineno(lineno)

    def _repeat_for(self, names: List[str], iterable, caller):
        renderer = self.environment.stencil_renderer  # noqa
        if getattr(renderer, 'repeat_mode', None) == 'ignore':
            return ''  # The loop item has already been set
        if isinstance(iterable, jinja2.Undefined) or iterable is None:
            iterable = []
        raise RepeatRendering(names, iterable)
