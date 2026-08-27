from __future__ import annotations

import csv
import json
from pathlib import Path

from tcg.domain.models import TestType as ScenarioType
from tcg.infrastructure.export import export_run
from tcg.infrastructure.security import SensitiveDataScanner

from .test_sample_pipeline import build_sample_run


def test_scanner_returns_field_path_without_secret_value() -> None:
    scanner = SensitiveDataScanner()
    findings = scanner.scan({"test_steps": [{"action": "Use sk-test-secret-value"}]})

    assert findings
    assert "root.test_steps[0].action:api_key" in findings
    assert all("sk-test-secret-value" not in finding for finding in findings)


def test_exporters_write_json_csv_and_xlsx(pipeline, project_root: Path, tmp_path: Path) -> None:
    run_id = build_sample_run(pipeline, project_root)
    pipeline.generate(run_id, {ScenarioType.POSITIVE})
    pipeline.validate_cases(run_id)
    run = pipeline.get_run(run_id)

    json_result = export_run(run, "json", tmp_path / "cases.json", pipeline.scanner)
    csv_result = export_run(run, "csv", tmp_path / "cases.csv", pipeline.scanner)
    xlsx_result = export_run(run, "xlsx", tmp_path / "cases.xlsx", pipeline.scanner)

    assert json_result["case_count"] == 11
    json_case = json.loads((tmp_path / "cases.json").read_text(encoding="utf-8"))[0]
    assert json_case["schema_version"] == "1.0"
    assert json_case["test_case_number"] == "TC-001"
    with (tmp_path / "cases.csv").open(encoding="utf-8-sig", newline="") as handle:
        assert len(next(csv.reader(handle))) == 19
    assert Path(xlsx_result["output_path"]).exists()
    assert csv_result["blocked_case_count"] == 0


def test_redactor_replaces_secrets() -> None:
    scanner = SensitiveDataScanner()
    redacted, count = scanner.redact("token sk-test-secret-value")

    assert redacted == "token [REDACTED]"
    assert count == 1
