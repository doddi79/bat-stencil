__all__ = [
    'base64',
]

import base64 as _base64
from typing import *


def base64(value: Union[str, bytes]) -> str:
    """Base64 encodes a value (e.g. for Kubernetes Secrets) as a single line"""
    if not isinstance(value, bytes):
        value = str(value).encode('utf-8')
    return _base64.b64encode(value).decode('ascii')
