"""Extraction of the signed request token from Brave's ``__data.json`` payload.

Brave serves the page data as a compacted JSON "pool" where repeated values are
indexed once and referenced by integer index. :func:`decode_pool` expands that
structure, and :func:`find_token` locates the ``{q, nonce, sig}`` token inside
it.
"""

from __future__ import annotations

from typing import Any, cast

from ..exceptions import TokenExtractionError
from ..models import TokenModel


def decode_pool(pool: list[Any]) -> Any:
    """Expand a compacted data pool into its plain representation."""
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
            mapping = cast(dict[Any, Any], value)
            return {key: expand(item) for key, item in mapping.items()}
        if isinstance(value, list):
            sequence = cast(list[Any], value)
            return [expand(item) for item in sequence]
        return value

    return expand(pool[0])


def find_token(payload: dict[str, Any]) -> TokenModel:
    """Locate the ``token = {q, nonce, sig}`` structure in the page data."""
    nodes = payload.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise TokenExtractionError("Payload __data.json does not contain a nodes list")

    for node in cast(list[Any], nodes):
        if not isinstance(node, dict):
            continue
        typed_node = cast(dict[str, Any], node)
        if typed_node.get("type") != "data":
            continue
        data = typed_node.get("data")
        if not isinstance(data, list):
            continue
        expanded = decode_pool(cast(list[Any], data))
        if not isinstance(expanded, dict):
            continue
        token = cast(dict[str, Any], expanded).get("token")
        if not isinstance(token, dict):
            continue
        typed_token = cast(dict[str, Any], token)
        q = typed_token.get("q")
        nonce = typed_token.get("nonce")
        sig = typed_token.get("sig")
        if (
            isinstance(q, str)
            and isinstance(nonce, str)
            and isinstance(sig, str)
            and q
            and nonce
            and sig
        ):
            return TokenModel(q=q, nonce=nonce, sig=sig)

    raise TokenExtractionError("Block `token = {q, nonce, sig}` not found in payload __data.json")


__all__ = ["decode_pool", "find_token"]
