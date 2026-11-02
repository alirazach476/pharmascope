"""Matching evaluation against a manually labeled SYNTHETIC pair set."""

from pharmascope.processing.entity_resolution import PairRecord, evaluate_matching, resolve_pair


def _labeled_pairs() -> list[PairRecord]:
    return [
        # True matches via NDC
        PairRecord("0001-0001", "00010001", "Alpha", "Alpha Extra", True),
        PairRecord("1234-5678", "12345678", "Beta", "Beta", True),
        # True match via normalized name only
        PairRecord(None, None, "Gamma Tab", "gamma tab", True),
        # True non-matches
        PairRecord("1111-1111", "2222-2222", "Delta", "Epsilon", False),
        PairRecord(None, None, "Zeta", "Eta", False),
        # Borderline fuzzy — labeled non-match for auto_matched metric
        PairRecord(None, None, "acetaminophen", "acetaminophenn", False),
    ]


def test_resolve_pair_prefers_ndc() -> None:
    result = resolve_pair(
        left_ndc="0001-0001",
        right_ndc="00010001",
        left_name="Different",
        right_name="Names",
    )
    assert result.matching_method == "exact_ndc"
    assert result.verification_status == "auto_matched"


def test_evaluate_matching_reports_f1() -> None:
    metrics = evaluate_matching(_labeled_pairs(), count_needs_review_as_positive=False)
    # Measured on this fixed labeled set — not a production accuracy claim
    assert 0.0 <= metrics.f1 <= 1.0
    assert metrics.support_positive == 3
    assert metrics.precision >= 0.9
    assert metrics.recall >= 0.9
