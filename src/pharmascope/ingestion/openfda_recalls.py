"""OpenFDA Drug Enforcement / Recalls ingestion client.

Documentation: https://open.fda.gov/apis/drug/enforcement/
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pharmascope.config.logging_config import get_logger
from pharmascope.config.settings import Settings
from pharmascope.ingestion.base_client import BaseAPIClient
from pharmascope.ingestion.checkpoints import CheckpointStore
from pharmascope.ingestion.manifests import ExtractionManifest
from pharmascope.ingestion.pagination import plan_openfda_pages

logger = get_logger("ingestion.openfda_recalls")

SOURCE_NAME = "openfda_recalls"


class OpenFDARecallsClient(BaseAPIClient):
    """Paginated client for OpenFDA drug enforcement/recall records."""

    def __init__(self, settings: Settings | None = None, **kwargs: Any) -> None:
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
        settings = self.settings
        page_size = page_size or min(
            int(self.source_cfg.get("default_limit_per_page", 100)),
            int(self.source_cfg.get("max_limit_per_page", 1000)),
        )

        if limit is None:
            if settings.allow_full_download:
                limit = 25_000 + page_size
                extraction_mode = "full"
            else:
                limit = settings.dev_record_limit
                extraction_mode = "bounded_sample"

        if not settings.allow_full_download and limit > settings.dev_record_limit:
            logger.warning(
                "Capping recalls limit from %s to %s (dev bound).",
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
            schema_version=self.source_cfg.get("schema_version"),
            extraction_mode=extraction_mode,
            query_parameters={"limit": limit, "page_size": page_size, "search": search},
            notes=[
                "Do not infer current recall status from historical records without "
                "verifying the relevant source status field."
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

        all_results: list[dict[str, Any]] = []
        try:
            for page in plan.pages:
                payload = self.fetch_page(skip=page.skip, limit=page.limit, search=search)
                results = payload.get("results") or []
                if not isinstance(results, list):
                    raise ValueError("OpenFDA enforcement 'results' was not a list")
                all_results.extend(results)
                manifest.page_count += 1
                logger.info(
                    "Recalls page skip=%s limit=%s got=%s",
                    page.skip,
                    page.limit,
                    len(results),
                )
                if len(results) < page.limit:
                    break

            out_path = out_dir / "recalls.jsonl"
            with out_path.open("w", encoding="utf-8") as fh:
                for record in all_results:
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

            manifest.raw_record_count = len(all_results)
            manifest.add_output(out_path)
            manifest.compute_checksum(out_path)
            manifest.mark_finished(status="success")

            checkpoint = checkpoint_store.load(SOURCE_NAME)
            checkpoint.last_batch_id = batch_id
            checkpoint.metadata["last_record_count"] = manifest.raw_record_count
            checkpoint_store.save(checkpoint)
        except Exception as exc:
            logger.exception("OpenFDA recalls extraction failed")
            err_dir = settings.layer_path("metadata") / "errors"
            err_dir.mkdir(parents=True, exist_ok=True)
            (err_dir / f"error_{SOURCE_NAME}_{uuid4()}.json").write_text(
                json.dumps(
                    {
                        "source": SOURCE_NAME,
                        "error": str(exc),
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            manifest.mark_finished(status="failed", error_details=str(exc))
            raise
        finally:
            manifest.save(meta_dir)

        return manifest


def run_openfda_recalls_extraction(*, limit: int | None = None) -> ExtractionManifest:
    with OpenFDARecallsClient() as client:
        return client.extract(limit=limit)
