from __future__ import annotations

import hashlib
from pathlib import Path


class FileValidationError(ValueError):
    """Raised when an uploaded source fails a non-sensitive preflight check."""


class FileValidator:
    """Perform bounded, extension-independent checks before a parser reads a file."""

    _magic = {
        ".xlsx": (b"PK\x03\x04",),
        ".pdf": (b"%PDF-",),
        ".md": (),
    }

    def __init__(self, max_bytes: int) -> None:
        self.max_bytes = max_bytes

    def validate(self, path: Path, declared_kind: str) -> str:
        if not path.exists() or not path.is_file():
            raise FileValidationError("Source file is missing or unreadable")
        size = path.stat().st_size
        if size == 0:
            raise FileValidationError("Source file is empty")
        if size > self.max_bytes:
            raise FileValidationError("Source file exceeds the configured size limit")
        suffix = path.suffix.lower()
        if declared_kind == "brd" and suffix != ".xlsx":
            raise FileValidationError("BRD input must use the .xlsx format")
        if declared_kind == "flow" and suffix != ".pdf":
            raise FileValidationError("Flow input must use the .pdf format")
        if declared_kind == "jira" and suffix not in {".md", ".markdown", ".txt"}:
            raise FileValidationError("JIRA input must use Markdown or text format")
        prefix = path.read_bytes()[:8]
        if (
            suffix in self._magic
            and self._magic[suffix]
            and not any(prefix.startswith(item) for item in self._magic[suffix])
        ):
            raise FileValidationError("Source content does not match its declared file type")
        return hashlib.sha256(path.read_bytes()).hexdigest()
