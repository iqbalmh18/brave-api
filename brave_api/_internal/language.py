"""Query language detection based on bundled stopword lists."""

from __future__ import annotations

import json
from functools import cache
from importlib.resources import files


@cache
def _load_stopwords(name: str) -> frozenset[str]:
    data = files("brave_api").joinpath("_data", name).read_text(encoding="utf-8")
    return frozenset(json.loads(data))


_PUNCTUATION = ".,!?()[]{}\"':;/\\"


def detect_query_language(query: str) -> tuple[str, str]:
    """Best-effort language detection returning ``(language, ui_lang)``.

    Counts stopword hits for Indonesian and English and returns the language
    with the higher score. Defaults to ``("en", "en-us")``.
    """
    tokens = [token.strip(_PUNCTUATION) for token in query.lower().split() if token.strip()]
    if not tokens:
        return "en", "en-us"

    stopwords_en = _load_stopwords("stopwords-en.json")
    stopwords_id = _load_stopwords("stopwords-id.json")

    id_score = sum(1 for token in tokens if token in stopwords_id)
    en_score = sum(1 for token in tokens if token in stopwords_en)

    if id_score > en_score:
        return "id", "id-id"
    return "en", "en-us"


__all__ = ["detect_query_language"]
