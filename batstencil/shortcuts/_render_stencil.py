__all__ = [
    'render_stencil',
]


from batstencil.stencils import *
from batstencil.utils import *
from batstencil.structs import *


def render_stencil(template: Union[T_PATH, ITemplate],
                   context: Union[None, Dict, T_PATH, IContext] = None) -> Optional[str]:
    """Renders a template to a `str` (or `None` if skipped via `{% skip_if %}`)
    guessing the template and context types from the arguments (see
    `guess_template_by_argument` and `guess_context_by_argument`)."""
    renderer = StringRenderer()
    renderer.template = guess_template_by_argument(template, renderer)
    renderer.context = guess_context_by_argument(context)
    return renderer.render()
