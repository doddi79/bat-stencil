__all__ = [
    'StencilError',

    'TemplateError',
    'TemplateNotFoundError',

    'ContextError',

    'RenderError',
    'NoTemplateSetError',
    'InvalidContextTypeForRendererError',
    'InvalidTemplateTypeForRendererError',
    'OutputFileExistsError',
    'NoOutputFileNameError',
    'EmbedFileNotFound',
    'TemplateRenderError',
    'UnsafePurgeError',

    'CancelRendering',
    'RepeatRendering',
]
from typing import *


class StencilError(Exception):
    pass


class TemplateError(StencilError):
    pass


class TemplateNotFoundError(TemplateError, FileNotFoundError):
    pass


class ContextError(StencilError):
    pass


class RenderError(StencilError):
    pass


class NoTemplateSetError(RenderError, ValueError):
    pass


class InvalidContextTypeForRendererError(RenderError, TypeError):
    pass


class InvalidTemplateTypeForRendererError(RenderError, TypeError):
    pass


class OutputFileExistsError(RenderError, FileExistsError):
    pass


class NoOutputFileNameError(RenderError, ValueError):
    pass


class EmbedFileNotFound(RenderError, FileNotFoundError):
    pass


class TemplateRenderError(RenderError):
    """Raised by the `DirectoryRenderer` when a template (or `__stencil_meta__`
    file) fails to render, naming the template that failed. The original
    (usually Jinja2) exception is chained as `__cause__`."""
    def __init__(self, message: str, template_path: Optional[str] = None):
        super().__init__(message)
        self.template_path = template_path


class UnsafePurgeError(RenderError):
    """Raised when the `DirectoryRenderer` is asked to purge an output path that
    it should never delete (e.g. the current working directory, one of its
    parents, the user's home directory or the template directory itself)."""


class CancelRendering(Exception):
    """Raised by the `{% skip_if %}` tag (and caught by the renderers) to skip
    rendering a template"""


class RepeatRendering(Exception):
    """Raised by the `{% repeat_for %}` tag (and caught by the
    `DirectoryRenderer`) to render a template or directory once per item"""
    def __init__(self, target_names: List[str], items: Iterable):
        super().__init__(f'Repeat rendering for {", ".join(target_names)}')
        self.target_names = target_names
        self.items = list(items)
