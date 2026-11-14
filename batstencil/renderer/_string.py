__all__ = [
    'StringRenderer',
]

from batstencil.structs import *
from ._base import *


class StringRenderer(_BaseRenderer):
    """Renders the template to a `str` (returned by `render()`, or `None` if
    rendering was skipped via `{% skip_if %}`)"""
    def __init__(self, context: Optional[IContext] = None, template: Optional[ITemplate] = None, **kwargs):
        super().__init__(context, template, **kwargs)

    def render(self) -> Optional[str]:
        return super().render()

    def _render_as_string(self) -> str:
        return self.template.get_jinja_template().render(**self.get_render_context())

    def _output_rendered_results(self, rendered_string: str) -> str:
        return rendered_string
