from __future__ import annotations

from pathlib import Path

from tcg.domain.models import TestType as ScenarioType
from tcg.interfaces.web.app import _active_signals, create_app


def test_web_api_exposes_sample_workflow(settings, project_root: Path) -> None:
    app = create_app(settings)
    client = app.test_client()

    initial = client.get("/api/state")
    assert initial.status_code == 200
    assert initial.get_json()["run"] is None

    loaded = client.post("/api/demo/load")
    assert loaded.status_code == 201
    payload = loaded.get_json()
    run_id = payload["run"]["run_id"]
    assert payload["counts"]["requirements"] == 11
    assert payload["cases"] == []
    assert len(payload["flow_paths"]) == 9
    assert len(payload["criteria"]) == 9

    generated = client.post(
        "/api/generate",
        json={"run_id": run_id, "test_types": ["POSITIVE", "BOUNDARY"]},
    )
    assert generated.status_code == 200
    assert generated.get_json()["counts"]["cases"] == 17
    assert generated.get_json()["cases"][0]["test_case_number"] == "TC-001"
    assert generated.get_json()["generation"]["created_cases"] == 17
    assert generated.get_json()["generation"]["failed_count"] == 0

    remaining = client.post(
        "/api/generate",
        json={
            "run_id": run_id,
            "test_types": ["NEGATIVE", "VALIDATION", "EXCEPTION", "INTEGRATION", "END_TO_END"],
        },
    )
    assert remaining.status_code == 200
    assert remaining.get_json()["counts"]["cases"] == 57
    assert remaining.get_json()["generation"]["created_cases"] == 40
    assert remaining.get_json()["generation"]["failed_count"] == 0

    validated = client.post("/api/validate", json={"run_id": run_id})
    assert validated.status_code == 200
    assert validated.get_json()["result"]["blocked"] == 0

    case_id = validated.get_json()["cases"][0]["test_case_id"]
    edited = client.put(
        f"/api/cases/{case_id}",
        json={
            "run_id": run_id,
            "scenario": "Edited evidence review scenario",
            "priority": "CRITICAL",
        },
    )
    assert edited.status_code == 200
    edited_case = next(
        item for item in edited.get_json()["cases"] if item["test_case_id"] == case_id
    )
    assert edited_case["test_case_number"] == "TC-001"
    assert edited_case["priority"] == "CRITICAL"
    reviewed = client.post(
        f"/api/cases/{case_id}/review",
        json={
            "run_id": run_id,
            "action": "approve",
            "actor": "qa-lead",
            "priority": "LOW",
        },
    )
    assert reviewed.status_code == 200
    reviewed_payload = reviewed.get_json()
    assert (
        next(item for item in reviewed_payload["cases"] if item["test_case_id"] == case_id)[
            "review_status"
        ]
        == "APPROVED"
    )
    approved_case = next(
        item for item in reviewed_payload["cases"] if item["test_case_id"] == case_id
    )
    assert approved_case["validation_status"] == "PASSED"
    assert approved_case["priority"] == "LOW"
    assert reviewed_payload["counts"]["approved_cases"] == 1
    assert reviewed_payload["counts"]["awaiting_review_cases"] == 56

    revalidated = client.post("/api/validate", json={"run_id": run_id})
    assert revalidated.status_code == 200
    assert revalidated.get_json()["counts"]["approved_cases"] == 1

    summary = client.get(f"/api/report/summary?run_id={run_id}")
    assert summary.status_code == 200
    distribution = summary.get_json()["priority_distribution"]
    assert set(distribution) == {"CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"}
    assert distribution["LOW"] >= 1
    assert sum(distribution.values()) == 57


def test_review_signals_hide_recovered_generation_failure(settings, project_root: Path) -> None:
    app = create_app(settings)
    pipeline = app.extensions["tcg_pipeline"]
    run_id = pipeline.create_run("Signals test", "Recovered generation", "INTERNAL").run_id
    pipeline.ingest_file(run_id, project_root / "samples/brd/sample_brd.xlsx", "brd")
    pipeline.process(run_id)
    run = pipeline.get_run(run_id)
    run.warnings.extend(
        [
            "Generation failed for BRD-PAY-001/POSITIVE: historical provider failure",
            "GAP: BRD-PAY-001 has no linked JIRA acceptance criterion",
        ]
    )
    run.cases.append(
        run.cases[0]
        if run.cases
        else pipeline._draft_to_case(
            run,
            run.requirements[0],
            pipeline.scenario_service.plan(run.requirements[0], [], {ScenarioType.POSITIVE})[0],
            pipeline.fallback_provider.generate(
                run.requirements[0], ScenarioType.POSITIVE, "evidence"
            ),
            {},
        )
    )

    signals = _active_signals(run)

    assert not any(
        signal.startswith("Generation failed for BRD-PAY-001/POSITIVE") for signal in signals
    )
    assert any(signal.startswith("GAP: ") for signal in signals)
