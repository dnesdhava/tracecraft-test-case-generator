from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

from tcg.application.pipeline import GeneratorPipeline, PipelineError
from tcg.config.logging_config import configure_logging
from tcg.config.settings import Settings, load_settings
from tcg.domain.models import TestType, jsonable
from tcg.infrastructure.export import export_run

SCENARIO_TYPES = [item.value for item in TestType]


def create_app(settings: Settings | None = None) -> Flask:
    project_root = Path(__file__).resolve().parents[4]
    active_settings = settings or load_settings(project_root)
    configure_logging(active_settings)
    pipeline = GeneratorPipeline(active_settings)
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["MAX_CONTENT_LENGTH"] = active_settings.max_upload_bytes * 2
    app.extensions["tcg_pipeline"] = pipeline

    @app.get("/")
    def index() -> Any:
        return render_template("index.html", scenario_types=SCENARIO_TYPES)

    @app.get("/healthz")
    def healthz() -> Any:
        return jsonify({"status": "ok"})

    @app.get("/api/state")
    def state() -> Any:
        return jsonify(_state_payload(pipeline))

    @app.post("/api/run")
    def create_run() -> Any:
        data = request.get_json(silent=True) or {}
        run = pipeline.create_run(
            str(data.get("project_name", "Demo Bank Payments")),
            str(data.get("feature_context", "Fund transfer test design")),
            str(data.get("classification", "INTERNAL")),
        )
        return jsonify(_state_payload(pipeline, run.run_id)), 201

    @app.post("/api/demo/load")
    def load_demo() -> Any:
        run = pipeline.create_run("Demo Bank Payments", "Sample fund transfer", "INTERNAL")
        sample_root = active_settings.project_root / "samples"
        pipeline.ingest_file(run.run_id, sample_root / "brd" / "sample_brd.xlsx", "brd")
        jira_path = sample_root / "jira" / "sample_jira_user_story.md"
        pipeline.ingest_jira_text(
            run.run_id,
            jira_path.read_text(encoding="utf-8"),
            "https://jira.example.com/browse/PAY-101",
        )
        pipeline.ingest_file(
            run.run_id, sample_root / "flow_diagrams" / "sample_payment_flow.pdf", "flow"
        )
        pipeline.process(run.run_id)
        return jsonify(_state_payload(pipeline, run.run_id)), 201

    @app.post("/api/upload")
    def upload() -> Any:
        run_id = request.form.get("run_id", "").strip()
        if not run_id:
            run = pipeline.create_run(
                "New Payment Review", "Uploaded fund transfer evidence", "INTERNAL"
            )
            run_id = run.run_id
        upload_root = active_settings.storage_dir / "uploads" / run_id
        upload_root.mkdir(parents=True, exist_ok=True)
        brd_file = request.files.get("brd_file")
        flow_file = request.files.get("flow_file")
        if brd_file and brd_file.filename:
            filename = secure_filename(brd_file.filename)
            path = upload_root / filename
            brd_file.save(path)
            pipeline.ingest_file(run_id, path, "brd")
        if flow_file and flow_file.filename:
            filename = secure_filename(flow_file.filename)
            path = upload_root / filename
            flow_file.save(path)
            pipeline.ingest_file(run_id, path, "flow")
        jira_content = request.form.get("jira_content", "")
        jira_url = request.form.get("jira_url", "").strip() or None
        if jira_content.strip():
            pipeline.ingest_jira_text(run_id, jira_content, jira_url)
        elif jira_url:
            raise PipelineError(
                "JIRA link captured, but story content or an approved export is required "
                "for offline processing"
            )
        return jsonify(_state_payload(pipeline, run_id)), 201

    @app.post("/api/process")
    def process() -> Any:
        run_id = _run_id()
        pipeline.process(run_id)
        return jsonify(_state_payload(pipeline, run_id))

    @app.post("/api/generate")
    def generate() -> Any:
        run_id = _run_id()
        data = request.get_json(silent=True) or {}
        selected = {TestType(value) for value in data.get("test_types", SCENARIO_TYPES)}
        before = pipeline.get_run(run_id)
        before_case_ids = {case.test_case_id for case in before.cases}
        before_warning_count = len(before.warnings)
        pipeline.generate(run_id, selected)
        after = pipeline.get_run(run_id)
        generation_failures = [
            warning
            for warning in after.warnings[before_warning_count:]
            if warning.startswith("Generation failed for ")
        ]
        created_cases = [case for case in after.cases if case.test_case_id not in before_case_ids]
        fallback_count = sum(
            case.generation_metadata.provider_name == "deterministic-fallback"
            for case in created_cases
        )
        eligible_by_type = {
            test_type.value: sum(
                plan.test_type == test_type and plan.applicability.value == "APPLICABLE"
                for plan in after.scenario_plans
            )
            for test_type in TestType
            if test_type in selected
        }
        payload = _state_payload(pipeline, run_id)
        payload["generation"] = {
            "requested_types": sorted(item.value for item in selected),
            "created_cases": len(created_cases),
            "total_cases": len(after.cases),
            "failed_count": len(generation_failures),
            "failures": generation_failures[-10:],
            "fallback_count": fallback_count,
            "eligible_by_type": eligible_by_type,
            "created_by_type": {
                test_type.value: sum(case.test_type == test_type for case in created_cases)
                for test_type in TestType
            },
        }
        return jsonify(payload)

    @app.post("/api/validate")
    def validate() -> Any:
        run_id = _run_id()
        result = pipeline.validate_cases(run_id)
        return jsonify({"result": result, **_state_payload(pipeline, run_id)})

    @app.put("/api/cases/<case_id>")
    def edit_case(case_id: str) -> Any:
        run_id = _run_id()
        data = request.get_json(silent=True) or {}
        data.pop("run_id", None)
        pipeline.edit_case(run_id, case_id, data)
        return jsonify(_state_payload(pipeline, run_id))

    @app.post("/api/cases/<case_id>/review")
    def review_case(case_id: str) -> Any:
        run_id = _run_id()
        data = request.get_json(silent=True) or {}
        pipeline.review_case(
            run_id,
            case_id,
            str(data.get("action", "")),
            str(data.get("actor", "local-reviewer")),
            str(data.get("reason", "")),
            str(data["priority"]) if data.get("priority") else None,
        )
        return jsonify(_state_payload(pipeline, run_id))

    @app.post("/api/export/<fmt>")
    def export(fmt: str) -> Any:
        run_id = _run_id()
        run = pipeline.get_run(run_id)
        approved_only = bool((request.get_json(silent=True) or {}).get("approved_only", False))
        output = Path(tempfile.gettempdir()) / f"tcg-{run_id}.{fmt.lower()}"
        result = export_run(run, fmt, output, pipeline.scanner, approved_only)
        pipeline.audit.record(
            "EXPORT_COMPLETED", run_id, metadata={"format": fmt, "cases": str(result["case_count"])}
        )
        return send_file(output, as_attachment=True, download_name=output.name)

    @app.get("/api/report/<report_type>")
    def report(report_type: str) -> Any:
        run_id = _run_id()
        reports = pipeline.reports(run_id)
        if report_type not in reports:
            raise PipelineError("Unknown report type")
        return jsonify(reports[report_type])

    @app.errorhandler(PipelineError)
    def pipeline_error(error: PipelineError) -> Any:
        return jsonify({"error": str(error)}), 400

    @app.errorhandler(ValueError)
    def value_error(error: ValueError) -> Any:
        return jsonify({"error": str(error)}), 400

    def _run_id() -> str:
        run_id = request.args.get("run_id") or request.form.get("run_id")
        data = request.get_json(silent=True) or {}
        run_id = run_id or data.get("run_id")
        if run_id:
            return str(run_id)
        runs = pipeline.list_runs()
        if runs:
            return runs[-1].run_id
        raise PipelineError("Create or load a generation run first")

    return app


def _state_payload(pipeline: GeneratorPipeline, run_id: str | None = None) -> dict[str, Any]:
    runs = pipeline.list_runs()
    if run_id:
        run = pipeline.get_run(run_id)
    elif runs:
        run = runs[-1]
    else:
        return {
            "run": None,
            "runs": [],
            "counts": {
                "sources": 0,
                "requirements": 0,
                "cases": 0,
                "approved_cases": 0,
                "awaiting_review_cases": 0,
                "rejected_cases": 0,
                "coverage": 0,
            },
            "requirements": [],
            "criteria": [],
            "flow_paths": [],
            "scenario_plans": [],
            "cases": [],
            "coverage": [],
            "traceability": [],
            "reports": {},
            "signals": [],
            "scenario_types": SCENARIO_TYPES,
        }
    coverage = pipeline.coverage(run.run_id)
    coverage_average = _average_coverage(coverage)
    approved_cases = sum(case.review_status.value == "APPROVED" for case in run.cases)
    rejected_cases = sum(case.review_status.value == "REJECTED" for case in run.cases)
    awaiting_review_cases = sum(
        case.review_status.value in {"DRAFT", "NEEDS_REVIEW", "NEEDS_CLARIFICATION"}
        for case in run.cases
    )
    return {
        "run": {
            "run_id": run.run_id,
            "project_name": run.project_name,
            "feature_context": run.feature_context,
            "classification": run.classification.value,
            "status": run.status.value,
            "created_at": run.created_at.isoformat(),
        },
        "runs": [
            {"run_id": item.run_id, "project_name": item.project_name, "status": item.status.value}
            for item in runs
        ],
        "counts": {
            "sources": len(run.sources),
            "requirements": len(run.requirements),
            "cases": len(run.cases),
            "approved_cases": approved_cases,
            "awaiting_review_cases": awaiting_review_cases,
            "rejected_cases": rejected_cases,
            "coverage": round(coverage_average, 1),
        },
        "sources": [jsonable(item) for item in run.sources],
        "requirements": [jsonable(item) for item in run.requirements],
        "criteria": [jsonable(item) for item in run.criteria],
        "flow_paths": [jsonable(item) for item in run.flow_paths],
        "scenario_plans": [jsonable(item) for item in run.scenario_plans],
        "cases": [jsonable(item) for item in run.cases],
        "coverage": coverage,
        "traceability": pipeline.traceability(run.run_id),
        "reports": pipeline.reports(run.run_id),
        "warnings": run.warnings[-20:],
        "signals": _active_signals(run),
        "scenario_types": SCENARIO_TYPES,
    }


def _active_signals(run: Any) -> list[str]:
    """Return unresolved signals while suppressing recovered generation failures."""
    resolved_cases = {(case.requirement_id, case.test_type.value) for case in run.cases}
    generation_failures: dict[tuple[str, str], str] = {}
    other_signals: list[str] = []
    seen_other: set[str] = set()
    pattern = re.compile(r"^Generation failed for ([^/]+)/([^:]+):")
    resolved_jira_warnings = {
        "JIRA Story ID was not found",
        "No Given/When/Then acceptance criteria were found",
    }

    for warning in run.warnings:
        match = pattern.match(warning)
        if match:
            key = (match.group(1), match.group(2))
            if key not in resolved_cases:
                generation_failures[key] = warning
            continue
        if run.criteria and warning in resolved_jira_warnings:
            continue
        if warning not in seen_other:
            seen_other.add(warning)
            other_signals.append(warning)

    return [*other_signals, *generation_failures.values()][-20:]


def _average_coverage(records: list[dict[str, object]]) -> float:
    values = [item.get("coverage_percentage", 0.0) for item in records]
    numeric = [float(value) for value in values if isinstance(value, (int, float))]
    return sum(numeric) / len(numeric) if numeric else 0.0


def main() -> None:
    host = os.environ.get("TCG_WEB_HOST", "127.0.0.1")
    port = int(os.environ.get("TCG_WEB_PORT", "5000"))
    create_app().run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
