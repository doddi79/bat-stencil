__all__ = [
    'IRenderer',
]
from batutils.structs import *
from ._context import *
from ._template import *
import jinja2


class IRenderer(abc.ABC):
    @abc.abstractmethod
    def __init__(self, context: Optional[IContext] = None, template: Optional[ITemplate] = None, **kwargs):
        pass

    @property
    @abc.abstractmethod
    def context(self) -> Optional[IContext]:
        pass

    @context.setter
    @abc.abstractmethod
    def context(self, value: IContext):
        pass

    @property
    @abc.abstractmethod
    def template(self) -> Optional[ITemplate]:
        pass

    @template.setter
    @abc.abstractmethod
    def template(self, value: ITemplate):
        pass

    @abc.abstractmethod
    def render(self):
        pass

    @property
    @abc.abstractmethod
    def jinja_environment(self) -> jinja2.Environment:
        pass

    @abc.abstractmethod
    def is_template_loadable(self, template_name: str) -> bool:
        pass

    @abc.abstractmethod
    def get_embed(self, file_path: str, source_file: Optional[str] = None, allconf: bool = False,
                  env: bool = False, fidelius: bool = False, py: bool = False, **kwargs) -> str:
        pass

    @property
    @abc.abstractmethod
    def output_file_name(self) -> str:
        pass

    @output_file_name.setter
    @abc.abstractmethod
    def output_file_name(self, value: str):
        pass
