__all__ = [
    'AllConfContext',
    'AlvissContext',
]

from batstencil.structs import *
from allconf import quickloader
from batutils.tpu import iters
from pathlib import Path
import logging
log = logging.getLogger(__name__)


class AllConfContext(IContext):
    """A context loaded from an AllConf (JSON/YAML) file, with all of AllConf's
    bells and whistles (includes, extensions, internal references,
    `${__ENV__:...}`, `${__PY__:...}` etc.)."""
    def __init__(self, file_name: Union[str, Path], **kwargs):
        self._file_name = str(file_name)
        self._data = quickloader.autoload(self._file_name)

    @property
    def file_name(self) -> str:
        return self._file_name

    def update(self, key: str, value: Any):
        self.as_dict()[key] = value

    def nested_update(self, key_tuple: Union[str, Sequence[str]], value: Any):
        log.debug(f'nested_update({key_tuple=}, {value=})')
        if isinstance(key_tuple, str):
            key_tuple = key_tuple.split('.')
        iters.nested_set(self.as_dict(), list(key_tuple), value)

    def as_dict(self) -> Dict:
        return self._data.as_dict(unmaksed=True)


AlvissContext = AllConfContext
"""Deprecated alias of `AllConfContext` (from back when AllConf was Alviss)"""
