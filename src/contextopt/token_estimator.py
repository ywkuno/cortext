from __future__ import annotations

from math import ceil


def estimate_tokens(text: str, *, chars_per_token: int = 4) -> int:
    if not text:
        return 0
    return ceil(len(text) / chars_per_token)
