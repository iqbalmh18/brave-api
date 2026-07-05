from __future__ import annotations

import base64
import secrets
import string

from .._internal.constants import AES_KEY_BASE64_LENGTH, AES_KEY_BYTES

_BASE64URL_ALPHABET: frozenset[str] = frozenset(string.ascii_letters + string.digits + "-_")


def generate_symmetric_key() -> str:
    raw_key = secrets.token_bytes(AES_KEY_BYTES)
    encoded = base64.urlsafe_b64encode(raw_key)
    return encoded.rstrip(b"=").decode("ascii")


def is_valid_symmetric_key(candidate: object) -> bool:
    if not isinstance(candidate, str) or not candidate:
        return False
    
    if len(candidate) != AES_KEY_BASE64_LENGTH:
        return False
    
    if any(char not in _BASE64URL_ALPHABET for char in candidate):
        return False
    
    padded = candidate + "=" * (-len(candidate) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded)
    except Exception:
        return False
    
    return len(decoded) == AES_KEY_BYTES


__all__ = ["generate_symmetric_key", "is_valid_symmetric_key"]
