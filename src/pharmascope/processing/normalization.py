"""String and identifier normalization utilities.

Never silently guess ambiguous ingredient identities, strengths, or product
equivalence. Original values are retained alongside normalized forms.
"""

from __future__ import annotations

import re
import unicodedata


_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9\s]")


def normalize_text(value: str | None) -> str | None:
    """Lowercase, strip accents, collapse whitespace; return None if empty."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = _WHITESPACE_RE.sub(" ", text)
    return text or None


def normalize_medicine_name(value: str | None) -> str | None:
    """Normalize a medicine/product name for exact-name matching keys."""
    text = normalize_text(value)
    if text is None:
        return None
    text = _NON_ALNUM_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text or None


def normalize_ndc(value: str | None) -> str | None:
    """Normalize NDC by stripping non-digits while retaining original separately.

    Does not invent missing segment padding; ambiguous formats stay unresolved.
    """
    if value is None:
        return None
    digits = re.sub(r"\D", "", str(value))
    return digits or None
