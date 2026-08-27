from __future__ import annotations

from pathlib import Path

from tcg.application.pipeline import GeneratorPipeline
from tcg.domain.models import TestType as ScenarioType
from tcg.domain.models import run_from_dict


def build_sample_run(pipeline: GeneratorPipeline, root: Path) -> str:
    run = pipeline.create_run("Demo Bank Payments", "Sample fund transfer", "INTERNAL")
    pipeline.ingest_file(run.run_id, root / "samples/brd/sample_brd.xlsx", "brd")
    pipeline.ingest_jira_text(
        run.run_id, (root / "samples/jira/sample_jira_user_story.md").read_text(encoding="utf-8")
    )
    pipeline.ingest_file(run.run_id, root / "samples/flow_diagrams/sample_payment_flow.pdf", "flow")
    pipeline.process(run.run_id)
    return run.run_id


def test_sample_sources_normalize_and_generate(
    pipeline: GeneratorPipeline, project_root: Path
) -> None:
    run_id = build_sample_run(pipeline, project_root)
    run = pipeline.generate(run_id, set(ScenarioType))
    result = pipeline.validate_cases(run_id)

    assert len(run.requirements) == 11
    assert len(run.criteria) == 9
    assert len(run.flow_paths) == 9
    assert len(run.cases) == 57
    assert [case.test_case_number for case in run.cases[:3]] == ["TC-001", "TC-002", "TC-003"]
    assert result["blocked"] == 0
    assert all(case.validation_status.value == "PASSED" for case in pipeline.get_run(run_id).cases)


def test_generation_is_idempotent_for_requirement_and_type(
    pipeline: GeneratorPipeline, project_root: Path
) -> None:
    run_id = build_sample_run(pipeline, project_root)
    first = pipeline.generate(run_id, {ScenarioType.POSITIVE})
    second = pipeline.generate(run_id, {ScenarioType.POSITIVE})

    assert len(first.cases) == 11
    assert len(second.cases) == 11


def test_existing_uuid_only_case_gets_stable_display_number() -> None:
    old_run = {
        "run_id": "run-migration",
        "project_name": "Migration test",
        "feature_context": "",
        "classification": "INTERNAL",
        "cases": [
            {
                "test_case_id": "uuid-one",
                "schema_version": "1.0",
                "requirement_id": "BRD-PAY-001",
                "scenario": "A migrated case",
                "preconditions": [],
                "test_data": [],
                "test_steps": [],
                "expected_results": [],
                "priority": "UNKNOWN",
                "test_type": "POSITIVE",
                "source_references": [],
                "review_status": "DRAFT",
                "validation_status": "FAILED",
                "generation_metadata": {},
            }
        ],
    }

    run = run_from_dict(old_run)

    assert run.cases[0].test_case_number == "TC-001"


def test_blocked_case_cannot_be_approved(pipeline: GeneratorPipeline, project_root: Path) -> None:
    run_id = build_sample_run(pipeline, project_root)
    pipeline.generate(run_id, {ScenarioType.POSITIVE})
    run = pipeline.get_run(run_id)
    case = run.cases[0]
    pipeline.edit_case(run_id, case.test_case_id, {"scenario": "Bearer sk-test-secret-value"})
    pipeline.validate_cases(run_id)

    try:
        pipeline.review_case(run_id, case.test_case_id, "approve")
    except Exception as error:
        assert "cannot be approved" in str(error)
    else:
        raise AssertionError("A security-blocked case was approved")


def test_google_failure_uses_labeled_evidence_fallback(settings, project_root: Path) -> None:
    google_settings = settings.__class__(
        **{**settings.__dict__, "ai_provider": "google", "ai_fallback_enabled": True}
    )
    pipeline = GeneratorPipeline(google_settings)

    class FailingProvider:
        def generate(self, requirement, test_type, context):
            raise RuntimeError("Google AI Studio returned non-JSON output")

    pipeline.ai_provider = FailingProvider()
    run_id = build_sample_run(pipeline, project_root)
    generated = pipeline.generate(run_id, {ScenarioType.NEGATIVE, ScenarioType.BOUNDARY})
    expected = sum(
        plan.applicability.value == "APPLICABLE"
        for plan in generated.scenario_plans
        if plan.test_type in {ScenarioType.NEGATIVE, ScenarioType.BOUNDARY}
    )

    assert len(generated.cases) == expected
    assert all(
        case.generation_metadata.provider_name == "deterministic-fallback"
        for case in generated.cases
    )
