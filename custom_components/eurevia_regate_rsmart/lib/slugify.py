"""String helpers for zone keys."""

from __future__ import annotations

import re
import unicodedata


def slugify_snake(value: str) -> str:
    """Normalize a human label into a stable snake_case key."""
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().strip()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or "zone"
