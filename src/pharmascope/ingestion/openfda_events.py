"""OpenFDA Drug Adverse Event (FAERS) ingestion client.

Documentation: https://open.fda.gov/apis/drug/event/

Adverse-event reports do not prove that a medicine caused an event.
This client extracts reported records for analytical research only.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pharmascope.config.logging_config import get_logger
from pharmascope.config.settings import Settings, get_settings
from pharmascope.ingestion.base_client import BaseAPIClient
from pharmascope.ingestion.checkpoints import CheckpointStore
from pharmascope.ingestion.manifests import ExtractionManifest
from pharmascope.ingestion.pagination import plan_openfda_pages

logger = get_logger("ingestion.openfda_events")

SOURCE_NAME = "openfda_events"


class OpenFDAEventsClient(BaseAPIClient):
    """Paginated client for OpenFDA drug adverse-event reports."""

    def __init__(
        self,
        settings: Settings | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(settings=settings, **kwargs)
        self.source_cfg = self.get_source_config(SOURCE_NAME)
        self.endpoint = str(self.source_cfg["api_endpoint"])

    def _auth_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if self.settings.openfda_api_key:
            params["api_key"] = self.settings.openfda_api_key
        return params

    def fetch_page(
        self,
        *,
        skip: int,
        limit: int,
        search: str | None = None,
    ) -> dict[str, Any]:
        params = self._auth_params()
        params["skip"] = skip
        params["limit"] = limit
        if search:
            params["search"] = search
        return self.request_json("GET", self.endpoint, params=params)

    def extract(
        self,
        *,
        limit: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
        extraction_mode: str = "bounded_sample",
    ) -> ExtractionManifest:
        """Extract adverse-event records into the raw layer with a manifest.

        By default uses ``PHARMASCOPE_DEV_RECORD_LIMIT`` to avoid large downloads.
        Set ``PHARMASCOPE_ALLOW_FULL_DOWNLOAD=true`` and pass an explicit large
        limit (or None with allow_full) only when intentionally downloading more.
        """
        settings = self.settings or get_settings()
        page_size = page_size or min(
            int(self.source_cfg.get("default_limit_per_page", 100)),
            int(self.source_cfg.get("max_limit_per_page", 1000)),
        )

        if limit is None:
            if settings.allow_full_download:
                # Still bound by OpenFDA skip limit for API pagination
                limit = 25_000 + page_size
                extraction_mode = "full"
            else:
                limit = settings.dev_record_limit
                extraction_mode = "bounded_sample"

        if not settings.allow_full_download and limit > settings.dev_record_limit:
            logger.warning(
                "Requested limit %s exceeds dev_record_limit %s; capping. "
                "Set PHARMASCOPE_ALLOW_FULL_DOWNLOAD=true to override.",
                limit,
                settings.dev_record_limit,
            )
            limit = settings.dev_record_limit
            extraction_mode = "bounded_sample"

        manifest = ExtractionManifest(
            source_name=SOURCE_NAME,
            official_url=self.source_cfg.get("official_url"),
            api_endpoint=self.endpoint,
            license_terms=self.source_cfg.get("license_terms"),
            data_format="json",
            schema_version=self.source_cfg.get("schema_version"),
            extraction_mode=extraction_mode,
            query_parameters={
                "limit": limit,
                "page_size": page_size,
                "search": search,
            },
            notes=[
                "FAERS reports are spontaneous and do not prove causation.",
                "OpenFDA API skip is capped at 25000; use bulk downloads for larger extracts.",
            ],
        )
        manifest.mark_running()

        raw_dir = settings.layer_path("raw") / SOURCE_NAME
        extraction_date = datetime.now(UTC).strftime("%Y-%m-%d")
        batch_id = manifest.manifest_id
        out_dir = raw_dir / f"extraction_date={extraction_date}" / f"batch_id={batch_id}"
        out_dir.mkdir(parents=True, exist_ok=True)

        meta_dir = settings.layer_path("metadata") / "manifests"
        checkpoint_store = CheckpointStore(settings.layer_path("metadata") / "checkpoints")

        plan = plan_openfda_pages(total_records=limit, page_size=page_size)
        if plan.truncated_by_skip_limit:
            manifest.notes.append(
                f"Requested {limit} records but OpenFDA skip limit truncated to "
                f"{plan.total_requested}."
            )

        all_results: list[dict[str, Any]] = []
        try:
            for page in plan.pages:
                payload = self.fetch_page(skip=page.skip, limit=page.limit, search=search)
                results = payload.get("results") or []
                if not isinstance(results, list):
                    raise ValueError("OpenFDA response 'results' was not a list")
                all_results.extend(results)
                manifest.page_count += 1
                meta = payload.get("meta", {})
                logger.info(
                    "Fetched page skip=%s limit=%s got=%s meta_total=%s",
                    page.skip,
                    page.limit,
                    len(results),
                    (meta.get("results") or {}).get("total"),
                )
                if len(results) < page.limit:
                    break

            manifest.raw_record_count = len(all_results)
            out_path = out_dir / "events.jsonl"
            with out_path.open("w", encoding="utf-8") as fh:
                for record in all_results:
                    # Preserve raw payload; add ingestion metadata alongside
                    envelope = {
                        "_ingestion": {
                            "source": SOURCE_NAME,
                            "batch_id": batch_id,
                            "ingested_at": datetime.now(UTC).isoformat(),
                            "schema_version": self.source_cfg.get("schema_version"),
                            "synthetic": False,
                        },
                        "payload": record,
                    }
                    fh.write(json.dumps(envelope, ensure_ascii=False) + "\n")

            manifest.add_output(out_path)
            manifest.compute_checksum(out_path)
            manifest.mark_finished(status="success")

            checkpoint = checkpoint_store.load(SOURCE_NAME)
            checkpoint.last_batch_id = batch_id
            checkpoint.last_skip = plan.pages[-1].skip if plan.pages else 0
            checkpoint.metadata["last_record_count"] = manifest.raw_record_count
            checkpoint_store.save(checkpoint)

        except Exception as exc:
            logger.exception("OpenFDA events extraction failed")
            # Persist partial results if any
            if all_results:
                partial_path = out_dir / "events_partial.jsonl"
                with partial_path.open("w", encoding="utf-8") as fh:
                    for record in all_results:
                        envelope = {
                            "_ingestion": {
                                "source": SOURCE_NAME,
                                "batch_id": batch_id,
                                "ingested_at": datetime.now(UTC).isoformat(),
                                "partial": True,
                                "synthetic": False,
                            },
                            "payload": record,
                        }
                        fh.write(json.dumps(envelope, ensure_ascii=False) + "\n")
                manifest.add_output(partial_path)
                manifest.raw_record_count = len(all_results)
                manifest.mark_finished(status="partial", error_details=str(exc))
            else:
                # Write structured error log
                err_dir = settings.layer_path("metadata") / "errors"
                err_dir.mkdir(parents=True, exist_ok=True)
                err_path = err_dir / f"error_{SOURCE_NAME}_{uuid4()}.json"
                err_path.write_text(
                    json.dumps(
                        {
                            "source": SOURCE_NAME,
                            "error": str(exc),
                            "timestamp": datetime.now(UTC).isoformat(),
                            "query": manifest.query_parameters,
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                manifest.mark_finished(status="failed", error_details=str(exc))
            raise
        finally:
            manifest_path = manifest.save(meta_dir)
            logger.info("Wrote manifest to %s", manifest_path)

        return manifest


def run_openfda_events_extraction(
    *,
    limit: int | None = None,
    search: str | None = None,
) -> ExtractionManifest:
    """Convenience entry point used by CLI scripts."""
    with OpenFDAEventsClient() as client:
        return client.extract(limit=limit, search=search)
