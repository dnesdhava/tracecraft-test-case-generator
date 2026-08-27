from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, cast

from openpyxl import Workbook

from tcg.config.schema_registry import SchemaRegistry
from tcg.domain.models import RunState, TestCase, jsonable
from tcg.domain.ports import SensitiveScanner


def _cases(run: RunState, approved_only: bool) -> list[TestCase]:
    if approved_only:
        return [case for case in run.cases if case.review_status.value == "APPROVED"]
    return list(run.cases)


def _payload(case: TestCase) -> dict[str, Any]:
    value = jsonable(case)
    if not isinstance(value, dict):
        raise TypeError("Test case serialization must produce an object")
    return cast(dict[str, Any], value)


def export_run(
    run: RunState,
    fmt: str,
    output_path: Path,
    scanner: SensitiveScanner,
    approved_only: bool = False,
) -> dict[str, Any]:
    cases = _cases(run, approved_only)
    safe_cases = [case for case in cases if not scanner.scan(case)]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    normalized = fmt.lower()
    if normalized == "json":
        output_path.write_text(
            json.dumps([_payload(case) for case in safe_cases], indent=2), encoding="utf-8"
        )
    elif normalized == "csv":
        _write_csv(safe_cases, output_path)
    elif normalized in {"xlsx", "excel"}:
        _write_xlsx(safe_cases, output_path)
    else:
        raise ValueError("Supported export formats are JSON, CSV, and XLSX")
    return {
        "output_path": str(output_path),
        "case_count": len(safe_cases),
        "blocked_case_count": len(cases) - len(safe_cases),
        "format": normalized,
        "schema_version": run.cases[0].schema_version
        if run.cases
        else SchemaRegistry.current_version(),
    }


def _write_csv(cases: list[TestCase], path: Path) -> None:
    columns = SchemaRegistry.get_csv_columns(SchemaRegistry.current_version())
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for case in cases:
            payload = _payload(case)
            metadata = payload["generation_metadata"]
            row = {column: "" for column in columns}
            row.update(
                {
                    "test_case_id": case.test_case_id,
                    "test_case_number": case.test_case_number,
                    "schema_version": case.schema_version,
                    "requirement_id": case.requirement_id,
                    "jira_story_id": case.jira_story_id or "",
                    "scenario": case.scenario,
                    "preconditions": json.dumps(payload["preconditions"]),
                    "test_data": json.dumps(payload["test_data"]),
                    "test_steps": json.dumps(payload["test_steps"]),
                    "expected_results": json.dumps(payload["expected_results"]),
                    "priority": case.priority.value,
                    "test_type": case.test_type.value,
                    "source_references": " | ".join(
                        reference["label"] for reference in payload["source_references"]
                    ),
                    "review_status": case.review_status.value,
                    "validation_status": case.validation_status.value,
                    "assumptions": json.dumps(payload["assumptions"]),
                    "open_questions": json.dumps(payload["open_questions"]),
                    "generation_run_id": metadata["run_id"],
                    "generated_at": metadata["generated_at"],
                }
            )
            writer.writerow(row)


def _write_xlsx(cases: list[TestCase], path: Path) -> None:
    workbook = Workbook()
    sheet = cast(Any, workbook.active)
    sheet.title = "Test_Cases"
    columns = SchemaRegistry.get_csv_columns(SchemaRegistry.current_version())
    sheet.append(columns)
    for case in cases:
        payload = _payload(case)
        metadata = payload["generation_metadata"]
        sheet.append(
            [
                case.test_case_id,
                case.test_case_number,
                case.schema_version,
                case.requirement_id,
                case.jira_story_id or "",
                case.scenario,
                json.dumps(payload["preconditions"]),
                json.dumps(payload["test_data"]),
                json.dumps(payload["test_steps"]),
                json.dumps(payload["expected_results"]),
                case.priority.value,
                case.test_type.value,
                " | ".join(reference["label"] for reference in payload["source_references"]),
                case.review_status.value,
                case.validation_status.value,
                json.dumps(payload["assumptions"]),
                json.dumps(payload["open_questions"]),
                metadata["run_id"],
                metadata["generated_at"],
            ]
        )
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    workbook.save(path)
