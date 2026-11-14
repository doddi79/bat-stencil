__all__ = [
    'guess_template_by_argument',
    'guess_context_by_argument',
]

from batstencil.context import *
from batstencil.template import *
from batstencil.structs import *

from pathlib import Path


def guess_template_by_argument(template: Union[T_PATH, ITemplate], renderer: Optional[IRenderer] = None) -> ITemplate:
    """Guesses the template type from the argument:

    - An `ITemplate` is returned as-is
    - A `Path` is a `FileTemplate`
    - A multi-line `str` is a `StringTemplate`
    - A single line `str` is a `FileTemplate` if it's a template name the
      renderer can load (from its search paths) or a path to an existing file,
      otherwise a `StringTemplate`
    """
    if isinstance(template, ITemplate):
        return template

    if isinstance(template, Path):
        return FileTemplate(file_path=template)

    if len(template.splitlines()) > 1:
        return StringTemplate(template_string=template)

    if renderer and template and isinstance(template, str):
        try:
            if renderer.is_template_loadable(template):
                return FileTemplate(file_path=template)
        except (OSError, ValueError, jinja2.TemplateError):
            pass
    try:
        as_path = Path(template)
        if template and as_path.is_file():
            return FileTemplate(file_path=template)
    except (OSError, ValueError, TypeError, NotImplementedError):
        pass  # All of these are likely if this wasn't actually a proper path!

    return StringTemplate(template_string=template)


def guess_context_by_argument(context: Union[None, T_PATH, Mapping, IContext]) -> IContext:
    """Guesses the context type from the argument:

    - An `IContext` is returned as-is
    - `None` is an empty `DictContext`
    - A `dict` (or other `Mapping`) is a `DictContext`
    - A `str` or `Path` is an `AllConfContext` (i.e. the path to a JSON or
      YAML file)
    """
    if isinstance(context, IContext):
        return context
    if context is None:
        return DictContext()
    if isinstance(context, Mapping):
        return DictContext(context_map=dict(context))
    return AllConfContext(file_name=context)
