from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from tcg.domain.models import (
    Requirement,
    RunState,
    SourceExtraction,
    SourceType,
    TestType,
)


@runtime_checkable
class SourceParser(Protocol):
    source_types: tuple[SourceType, ...]

    def accepts(self, source_type: SourceType) -> bool:
        """Return whether the parser handles the declared source type."""

    def parse(self, path: Path, source_id: str) -> SourceExtraction:
        """Parse a source into domain extraction models."""


@runtime_checkable
class RunStorage(Protocol):
    def create_run(self, run: RunState) -> None:
        """Persist a new generation run."""

    def load_run(self, run_id: str) -> RunState:
        """Load a generation run by identifier."""

    def save_run(self, run: RunState) -> None:
        """Persist the current state of a generation run."""


@runtime_checkable
class AIProvider(Protocol):
    def generate(
        self,
        requirement: Requirement,
        test_type: TestType,
        context: str,
    ) -> dict[str, object]:
        """Generate a structured draft from evidence-grounded context."""


@runtime_checkable
class SensitiveScanner(Protocol):
    def scan(self, value: object) -> list[str]:
        """Return field paths containing sensitive data patterns."""

    def redact(self, text: str) -> tuple[str, int]:
        """Return redacted text and replacement count."""


@runtime_checkable
class Exporter(Protocol):
    def export(self, run: RunState, output_path: Path, approved_only: bool = False) -> Path:
        """Export a run and return the written output path."""


__all__ = ["AIProvider", "Exporter", "RunStorage", "SensitiveScanner", "SourceParser"]
