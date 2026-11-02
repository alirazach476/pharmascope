"""Multiple-testing correction utilities."""

from __future__ import annotations

import numpy as np


def benjamini_hochberg(pvalues: list[float], *, alpha: float = 0.05) -> list[float]:
    """Return BH-adjusted p-values (positive FDR control).

    Parameters
    ----------
    pvalues:
        Raw p-values in [0, 1].
    alpha:
        Target FDR level (recorded for callers; adjustment itself is alpha-free
        in the classic BH adjusted-p formulation used here).
    """
    del alpha  # retained for API clarity; adjusted p-values are alpha-independent
    if not pvalues:
        return []
    p = np.asarray(pvalues, dtype=float)
    n = len(p)
    order = np.argsort(p)
    ranked = p[order]
    adjusted = np.empty(n, dtype=float)
    prev = 1.0
    for i in range(n - 1, -1, -1):
        rank = i + 1
        val = ranked[i] * n / rank
        prev = min(prev, val)
        adjusted[i] = prev
    out = np.empty(n, dtype=float)
    out[order] = np.clip(adjusted, 0, 1)
    return out.tolist()
