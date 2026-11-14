__all__ = [
    'StdOutRenderer',
]

from batstencil.structs import *
from ._string import *


class StdOutRenderer(StringRenderer):
    """Prints the rendered template to stdout (nothing if it was skipped)"""
    def render(self) -> None:
        results = super().render()
        if results is not None:
            print(results)
