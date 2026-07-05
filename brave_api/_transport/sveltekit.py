from __future__ import annotations

from typing import Any

from .._internal.types import TokenDict
from ..exceptions import TokenExtractionError


def decode_pool(pool: list[Any]) -> Any:
    if not pool:
        return None

    pool_length = len(pool)

    def expand(value: Any) -> Any:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            if value < 0 or value >= pool_length:
                return None
            return expand(pool[value])
        if isinstance(value, float):
            return expand(int(value))
        if isinstance(value, dict):
            return {key: expand(val) for key, val in value.items()}
        if isinstance(value, list):
            return [expand(item) for item in value]
        return value

    return expand(pool[0])


def find_token(payload: dict[str, Any]) -> TokenDict:
    nodes = payload.get("nodes") or []
    for node in nodes:
        if node.get("type") != "data":
            continue
        pool = node.get("data")
        if not isinstance(pool, list):
            continue
        expanded = decode_pool(pool)
        if not isinstance(expanded, dict):
            continue
        token = expanded.get("token")
        if not isinstance(token, dict):
            continue
        q_value = token.get("q")
        nonce_value = token.get("nonce")
        sig_value = token.get("sig")
        if (
            isinstance(q_value, str)
            and isinstance(nonce_value, str)
            and isinstance(sig_value, str)
            and q_value
            and nonce_value
            and sig_value
        ):
            return TokenDict(q=q_value, nonce=nonce_value, sig=sig_value)

    raise TokenExtractionError(
        "Block `token = {q, nonce, sig}` not found in payload __data.json"
    )


__all__ = ["decode_pool", "find_token"]
