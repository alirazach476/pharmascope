#!/usr/bin/env python
"""Aggregate extraction manifests into a single inventory file."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pharmascope.config.settings import get_settings  # noqa: E402


def main() -> int:
    settings = get_settings()
    manifest_dir = settings.layer_path("metadata") / "manifests"
    inventory = []
    if manifest_dir.exists():
        for path in sorted(manifest_dir.glob("manifest_*.json")):
            inventory.append(json.loads(path.read_text(encoding="utf-8")))
    out = settings.layer_path("metadata") / "data_inventory.json"
    out.write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    print(f"Wrote inventory with {len(inventory)} manifests to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
