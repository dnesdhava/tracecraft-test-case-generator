from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from tcg.application.pipeline import GeneratorPipeline
from tcg.config.settings import load_settings


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def settings(tmp_path: Path, project_root: Path):
    base = load_settings(project_root)
    return replace(
        base,
        ai_provider="deterministic",
        storage_dir=tmp_path / "storage",
        audit_log_path=tmp_path / "audit.jsonl",
        security_audit_log_path=tmp_path / "security.jsonl",
    )


@pytest.fixture
def pipeline(settings) -> GeneratorPipeline:
    return GeneratorPipeline(settings)
