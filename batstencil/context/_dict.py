__all__ = [
    'DictContext',
]

from batstencil.structs import *
from batutils.tpu import iters
import logging
log = logging.getLogger(__name__)


class DictContext(IContext):
    def __init__(self, context_map: Optional[Dict[str, Any]] = None, **kwargs):
        self._context_map = context_map if context_map is not None else {}

    def update(self, key: str, value: Any):
        self._context_map[key] = value

    def nested_update(self, key_tuple: Union[str, Sequence[str]], value: Any):
        log.debug(f'nested_update({key_tuple=}, {value=})')
        if isinstance(key_tuple, str):
            key_tuple = key_tuple.split('.')
        iters.nested_set(self._context_map, list(key_tuple), value)

    def as_dict(self) -> Dict:
        return self._context_map
