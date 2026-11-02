from pharmascope.processing.entity_resolution import (
    exact_ndc_match,
    exact_normalized_name_match,
    fuzzy_name_candidate,
)


def test_exact_ndc() -> None:
    m = exact_ndc_match("0001-0001", "00010001")
    assert m is not None
    assert m.matching_method == "exact_ndc"
    assert m.verification_status == "auto_matched"


def test_exact_name() -> None:
    m = exact_normalized_name_match("Lipitor", "lipitor")
    assert m is not None
    assert m.matching_confidence == 0.9


def test_fuzzy_needs_review() -> None:
    m = fuzzy_name_candidate("acetaminophen", "acetaminophenn", threshold=0.9)
    assert m is not None
    assert m.verification_status == "needs_review"


def test_no_false_merge() -> None:
    assert exact_normalized_name_match("drug a", "drug b") is None
