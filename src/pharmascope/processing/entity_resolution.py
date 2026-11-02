"""Medicine entity resolution — identifier-first matching.

Never merge two products merely because their names look similar.
Fuzzy matching is reserved for unresolved candidates and must carry a
confidence score and explainable reason.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from pharmascope.ml.evaluation import ClassificationMetrics, binary_classification_metrics
from pharmascope.processing.normalization import normalize_medicine_name, normalize_ndc


@dataclass(frozen=True)
class MatchResult:
    left_key: str
    right_key: str
    matching_method: str
    matching_confidence: float
    matching_reason: str
    verification_status: str  # auto_matched | needs_review | unmatched


@dataclass(frozen=True)
class PairRecord:
    left_ndc: str | None
    right_ndc: str | None
    left_name: str | None
    right_name: str | None
    is_match: bool  # manually verified label for evaluation


def exact_ndc_match(left_ndc: str | None, right_ndc: str | None) -> MatchResult | None:
    ln = normalize_ndc(left_ndc)
    rn = normalize_ndc(right_ndc)
    if not ln or not rn:
        return None
    if ln == rn:
        return MatchResult(
            left_key=ln,
            right_key=rn,
            matching_method="exact_ndc",
            matching_confidence=1.0,
            matching_reason="Normalized NDC digits identical",
            verification_status="auto_matched",
        )
    return None


def exact_normalized_name_match(
    left_name: str | None,
    right_name: str | None,
) -> MatchResult | None:
    ln = normalize_medicine_name(left_name)
    rn = normalize_medicine_name(right_name)
    if not ln or not rn:
        return None
    if ln == rn:
        return MatchResult(
            left_key=ln,
            right_key=rn,
            matching_method="exact_normalized_name",
            matching_confidence=0.9,
            matching_reason="Normalized medicine names identical",
            verification_status="auto_matched",
        )
    return None


def fuzzy_name_candidate(
    left_name: str | None,
    right_name: str | None,
    *,
    threshold: float = 0.92,
) -> MatchResult | None:
    """Propose a fuzzy name match for manual review — never auto-merge."""
    ln = normalize_medicine_name(left_name)
    rn = normalize_medicine_name(right_name)
    if not ln or not rn:
        return None
    score = SequenceMatcher(None, ln, rn).ratio()
    if score >= threshold:
        return MatchResult(
            left_key=ln,
            right_key=rn,
            matching_method="fuzzy_name",
            matching_confidence=round(score, 4),
            matching_reason=f"SequenceMatcher ratio={score:.4f} >= {threshold}",
            verification_status="needs_review",
        )
    return None


def resolve_pair(
    *,
    left_ndc: str | None,
    right_ndc: str | None,
    left_name: str | None,
    right_name: str | None,
    fuzzy_threshold: float = 0.92,
    auto_accept_fuzzy: bool = False,
) -> MatchResult:
    """Ordered matching pipeline: NDC → normalized name → fuzzy (review)."""
    ndc = exact_ndc_match(left_ndc, right_ndc)
    if ndc:
        return ndc
    name = exact_normalized_name_match(left_name, right_name)
    if name:
        return name
    fuzzy = fuzzy_name_candidate(left_name, right_name, threshold=fuzzy_threshold)
    if fuzzy:
        if auto_accept_fuzzy:
            return MatchResult(
                left_key=fuzzy.left_key,
                right_key=fuzzy.right_key,
                matching_method=fuzzy.matching_method,
                matching_confidence=fuzzy.matching_confidence,
                matching_reason=fuzzy.matching_reason + " (auto_accept_fuzzy=True)",
                verification_status="auto_matched",
            )
        return fuzzy
    left = normalize_medicine_name(left_name) or normalize_ndc(left_ndc) or ""
    right = normalize_medicine_name(right_name) or normalize_ndc(right_ndc) or ""
    return MatchResult(
        left_key=left,
        right_key=right,
        matching_method="unmatched",
        matching_confidence=0.0,
        matching_reason="No exact NDC/name match; fuzzy below threshold",
        verification_status="unmatched",
    )


def evaluate_matching(
    pairs: list[PairRecord],
    *,
    count_needs_review_as_positive: bool = False,
) -> ClassificationMetrics:
    """Evaluate matcher against a manually labeled pair set.

    By default only ``auto_matched`` predictions count as positive predictions.
    Fuzzy ``needs_review`` pairs are treated as non-matches unless
    ``count_needs_review_as_positive`` is True.
    """
    y_true: list[int] = []
    y_pred: list[int] = []
    for pair in pairs:
        result = resolve_pair(
            left_ndc=pair.left_ndc,
            right_ndc=pair.right_ndc,
            left_name=pair.left_name,
            right_name=pair.right_name,
        )
        y_true.append(1 if pair.is_match else 0)
        if result.verification_status == "auto_matched":
            y_pred.append(1)
        elif result.verification_status == "needs_review" and count_needs_review_as_positive:
            y_pred.append(1)
        else:
            y_pred.append(0)
    return binary_classification_metrics(y_true, y_pred)
