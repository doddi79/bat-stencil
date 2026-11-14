__all__ = [
    'IContext',
]
from batutils.structs import *


class IContext(abc.ABC):
    @abc.abstractmethod
    def __init__(self, **kwargs):
        pass

    @abc.abstractmethod
    def update(self, key: str, value: Any):
        """Sets a top level key of the context"""

    @abc.abstractmethod
    def nested_update(self, key_tuple: Union[str, Sequence[str]], value: Any):
        """Sets a nested key of the context, either given as a dotted string
        (e.g. `'app.colors.favorite'`) or a sequence of keys, creating any
        missing intermediate dicts"""

    @abc.abstractmethod
    def as_dict(self) -> Dict:
        """The context as a dict (the context variables used when rendering)"""
