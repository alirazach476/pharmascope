"""OpenFDA skip/limit pagination helpers.

OpenFDA documents skip + limit pagination on JSON API endpoints.
See: https://open.fda.gov/apis/paging/
Maximum skip is documented as 25,000; beyond that use search/date windows
or bulk downloads.
"""

from __future__ import annotations

from dataclasses import dataclass


OPENFDA_MAX_SKIP = 25_000


@dataclass(frozen=True)
class PageRequest:
    """A single paginated request window."""

    skip: int
    limit: int


@dataclass(frozen=True)
class PagePlan:
    """Planned page requests for a bounded extraction."""

    pages: tuple[PageRequest, ...]
    total_requested: int
    truncated_by_skip_limit: bool


def plan_openfda_pages(
    *,
    total_records: int,
    page_size: int,
    max_skip: int = OPENFDA_MAX_SKIP,
) -> PagePlan:
    """Plan skip/limit pages for an OpenFDA extraction.

    Parameters
    ----------
    total_records:
        Desired number of records (already bounded by caller).
    page_size:
        Records per page (OpenFDA allows up to 1000).
    max_skip:
        OpenFDA documented maximum skip value.
    """
    if total_records <= 0:
        return PagePlan(pages=(), total_requested=0, truncated_by_skip_limit=False)
    if page_size <= 0:
        raise ValueError("page_size must be positive")

    max_reachable = max_skip + page_size
    truncated = total_records > max_reachable
    target = min(total_records, max_reachable)

    pages: list[PageRequest] = []
    fetched = 0
    skip = 0
    while fetched < target:
        limit = min(page_size, target - fetched)
        if skip > max_skip:
            truncated = True
            break
        pages.append(PageRequest(skip=skip, limit=limit))
        fetched += limit
        skip += limit

    return PagePlan(
        pages=tuple(pages),
        total_requested=fetched,
        truncated_by_skip_limit=truncated,
    )
