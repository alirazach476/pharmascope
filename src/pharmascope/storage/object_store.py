"""Optional S3-compatible object storage interface.

Local filesystem is the default for development. This module defines a minimal
interface so remote deployment can be added without rewriting pipelines.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ObjectStore(Protocol):
    def upload_file(self, local_path: Path, remote_key: str) -> None: ...

    def download_file(self, remote_key: str, local_path: Path) -> None: ...


class LocalObjectStore:
    """Filesystem-backed stand-in that copies files under a root prefix."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def upload_file(self, local_path: Path, remote_key: str) -> None:
        dest = self.root / remote_key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(Path(local_path).read_bytes())

    def download_file(self, remote_key: str, local_path: Path) -> None:
        src = self.root / remote_key
        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(src.read_bytes())
