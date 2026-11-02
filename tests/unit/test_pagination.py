from pharmascope.ingestion.pagination import OPENFDA_MAX_SKIP, plan_openfda_pages


def test_plan_pages_basic() -> None:
    plan = plan_openfda_pages(total_records=250, page_size=100)
    assert plan.total_requested == 250
    assert len(plan.pages) == 3
    assert plan.pages[0].skip == 0
    assert plan.pages[1].skip == 100
    assert not plan.truncated_by_skip_limit


def test_plan_pages_respects_skip_cap() -> None:
    plan = plan_openfda_pages(total_records=100_000, page_size=1000)
    assert plan.truncated_by_skip_limit
    assert plan.total_requested <= OPENFDA_MAX_SKIP + 1000
