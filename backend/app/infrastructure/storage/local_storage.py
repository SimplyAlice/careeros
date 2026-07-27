"""Local filesystem storage adapter.

Implements `FileStorage` (`app/application/documents/ports.py`) by
writing to a local directory — an interim adapter until Azure Blob
Storage (already documented as the eventual home for generated documents
in `docs/architecture/cloud-architecture.md`) is wired up. Swapping to a
`AzureBlobFileStorage` later means writing one new adapter class; nothing
above this layer changes, since both implement the same `save`/`read`
shape.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

_SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


class LocalFileStorage:
    """Saves/reads files under a configured base directory."""

    def __init__(self, base_dir: str) -> None:
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, *, filename: str, content: bytes) -> str:
        safe_name = _SAFE_FILENAME_PATTERN.sub("_", filename)
        safe_name = safe_name.replace("..", "_")  # belt-and-suspenders: no path-traversal-looking sequences
        # A short random prefix avoids collisions if the same logical name
        # (e.g. two resumes generated for the same job) is saved twice —
        # each generation is a new versioned row (see
        # `GeneratedResumeRepository.create`'s docstring), so the file it
        # points to must also be distinct.
        unique_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
        path = self._base_dir / unique_name
        path.write_bytes(content)
        return str(path)

    def read(self, *, path: str) -> bytes:
        return Path(path).read_bytes()
