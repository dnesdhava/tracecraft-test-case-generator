from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

from tcg.config.schema_registry import SchemaRegistry
from tcg.config.settings import Settings
from tcg.domain.models import (
    AcceptanceCriterion,
    DataClassification,
    FindingSeverity,
    FlowPath,
    GenerationMetadata,
    Priority,
    ProcessingStatus,
    Requirement,
    ReviewEvent,
    ReviewStatus,
    RunState,
    RunStatus,
    ScenarioPlan,
    SourceExtraction,
    SourceMetadata,
    SourceType,
    TestCase,
    TestDataItem,
    TestStep,
    TestType,
    ValidationFinding,
    ValidationStatus,
    utc_now,
)
from tcg.domain.ports import AIProvider
from tcg.domain.services import (
    CoverageService,
    DeduplicationService,
    RequirementNormalizer,
    ScenarioService,
)
from tcg.infrastructure.ai import (
    ContextAssembler,
    DeterministicAIProvider,
    GoogleAIStudioProvider,
    OpenAICompatibleProvider,
    PromptBuilder,
)
from tcg.infrastructure.audit import FileAuditWriter
from tcg.infrastructure.parsers import ExcelBRDParser, JiraMarkdownParser, PdfFlowParser
from tcg.infrastructure.security import AccessController, FileValidator, SensitiveDataScanner
from tcg.infrastructure.storage import FileRunStorage

Parser = ExcelBRDParser | JiraMarkdownParser | PdfFlowParser


class PipelineError(RuntimeError):
    """A user-actionable pipeline failure with no confidential payload."""


class GeneratorPipeline:
    """Coordinate adapters and domain services for both the web UI and CLI."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.storage = FileRunStorage(settings.storage_dir)
        self.audit = FileAuditWriter(settings.audit_log_path, settings.security_audit_log_path)
        self.access = AccessController()
        self.file_validator = FileValidator(settings.max_upload_bytes)
        self.scanner = SensitiveDataScanner(settings.sensitive_patterns)
        self.jira_parser = JiraMarkdownParser()
        self.parsers: dict[str, Parser] = {
            "brd": ExcelBRDParser(),
            "jira": self.jira_parser,
            "flow": PdfFlowParser(),
        }
        self.normalizer = RequirementNormalizer()
        self.scenario_service = ScenarioService()
        self.coverage_service = CoverageService()
        self.deduplication = DeduplicationService()
        self.context_assembler = ContextAssembler(
            settings.context_budget,
            settings.prompt_injection_blocklist,
            self.scanner,
        )
        self.prompt_builder = PromptBuilder(settings.prompt_template_path)
        self.provider_name = settings.ai_provider
        self.ai_provider = self._provider()
        self.fallback_provider = DeterministicAIProvider("local-evidence-fallback")

    def create_run(self, project_name: str, feature_context: str, classification: str) -> RunState:
        run_id = f"run-{uuid.uuid4().hex[:10]}"
        try:
            data_classification = DataClassification(classification.upper())
        except ValueError as exc:
            raise PipelineError("Unsupported data classification") from exc
        run = RunState(
            run_id,
            project_name.strip() or "Untitled project",
            feature_context.strip(),
            data_classification,
        )
        self.storage.create_run(run)
        self.audit.record("RUN_CREATED", run_id, metadata={"project": run.project_name})
        return run

    def get_run(self, run_id: str) -> RunState:
        try:
            return self.storage.load_run(run_id)
        except Exception as exc:
            raise PipelineError("Generation run was not found") from exc

    def list_runs(self) -> list[RunState]:
        return self.storage.list_runs()

    def ingest_file(
        self, run_id: str, path: Path, kind: str, source_url: str | None = None
    ) -> SourceMetadata:
        run = self.get_run(run_id)
        if not self.access.authorize("local-user", "UPLOAD", run.project_name):
            self.audit.record("ACCESS_DENIED", run_id, outcome="FAILURE")
            raise PipelineError("Upload is not authorized for this project")
        if kind not in self.parsers:
            raise PipelineError("Unsupported source kind")
        try:
            checksum = self.file_validator.validate(path, kind)
            source_id = f"{kind}-{uuid.uuid4().hex[:10]}"
            extraction = self.parsers[kind].parse(path, source_id)
        except (OSError, ValueError) as exc:
            self.audit.record(
                "EXTRACTION_WARNING", run_id, outcome="FAILURE", metadata={"kind": kind}
            )
            raise PipelineError(str(exc)) from exc
        source = self._metadata(source_id, kind, path.name, checksum, extraction, source_url)
        run.sources.append(source)
        run.extractions[source_id] = extraction
        run.warnings.extend(extraction.warnings)
        run.updated_at = utc_now()
        self.storage.save_run(run)
        self.audit.record(
            "SOURCE_REGISTERED",
            run_id,
            source_id,
            metadata={"kind": kind, "status": source.status.value},
        )
        self.audit.record(
            "SOURCE_PARSED", run_id, source_id, metadata={"items": str(source.item_count)}
        )
        return source

    def ingest_jira_text(
        self, run_id: str, content: str, source_url: str | None = None
    ) -> SourceMetadata:
        run = self.get_run(run_id)
        if not content.strip():
            if source_url:
                raise PipelineError(
                    "The JIRA link was registered as a reference; provide story content "
                    "or an approved export"
                )
            raise PipelineError("JIRA story content is required")
        source_id = f"jira-{uuid.uuid4().hex[:10]}"
        checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
        extraction = self.jira_parser.parse_text(content, source_id, source_url=source_url)
        source = self._metadata(
            source_id, "jira", "jira-story.md", checksum, extraction, source_url
        )
        run.sources.append(source)
        run.extractions[source_id] = extraction
        run.warnings.extend(extraction.warnings)
        run.updated_at = utc_now()
        self.storage.save_run(run)
        self.audit.record(
            "SOURCE_REGISTERED",
            run_id,
            source_id,
            metadata={"kind": "jira", "status": source.status.value},
        )
        return source

    def process(self, run_id: str) -> RunState:
        run = self.get_run(run_id)
        run.status = RunStatus.PROCESSING
        brd_requirements: list[Requirement] = []
        criteria: list[AcceptanceCriterion] = []
        flow_paths: list[FlowPath] = []
        for extraction in run.extractions.values():
            brd_requirements.extend(extraction.requirements)
            criteria.extend(extraction.criteria)
            if extraction.flow:
                flow_paths.extend(extraction.flow.paths)
        result = self.normalizer.normalize(brd_requirements, criteria, flow_paths)
        run.requirements = list(result.requirements)
        run.criteria = criteria
        run.flow_paths = flow_paths
        run.trace_links = list(result.trace_links)
        run.warnings.extend(result.issues)
        run.status = RunStatus.AWAITING_REVIEW
        run.updated_at = utc_now()
        self.storage.save_run(run)
        self.audit.record(
            "NORMALIZATION_COMPLETED", run_id, metadata={"requirements": str(len(run.requirements))}
        )
        for issue in result.issues:
            self.audit.record("GAP_IDENTIFIED", run_id, metadata={"issue": issue[:120]})
        return run

    def plan(self, run_id: str, selected_types: set[TestType] | None = None) -> list[ScenarioPlan]:
        run = self.get_run(run_id)
        if not run.requirements:
            self.process(run_id)
            run = self.get_run(run_id)
        plans: list[ScenarioPlan] = []
        for requirement in run.requirements:
            plans.extend(self.scenario_service.plan(requirement, run.flow_paths, selected_types))
        run.scenario_plans = plans
        self.storage.save_run(run)
        return plans

    def generate(self, run_id: str, selected_types: set[TestType] | None = None) -> RunState:
        run = self.get_run(run_id)
        if not run.requirements:
            run = self.process(run_id)
        plans = self.plan(run_id, selected_types)
        run = self.get_run(run_id)
        existing = {(case.requirement_id, case.test_type) for case in run.cases}
        source_versions = {source.source_id: source.checksum for source in run.sources}
        for plan in plans:
            if (
                plan.applicability.value != "APPLICABLE"
                or (plan.requirement_id, plan.test_type) in existing
            ):
                continue
            requirement = next(
                item for item in run.requirements if item.requirement_id == plan.requirement_id
            )
            package = self.context_assembler.assemble(requirement, plan)
            try:
                prompt = self.prompt_builder.build(package)
                draft = self.ai_provider.generate(requirement, plan.test_type, prompt)
                case = self._draft_to_case(run, requirement, plan, draft, source_versions)
            except (RuntimeError, ValueError, FileNotFoundError) as exc:
                run.warnings.append(
                    f"Generation failed for {requirement.requirement_id}/"
                    f"{plan.test_type.value}: {exc}"
                )
                self.audit.record(
                    "GENERATION_FAILED",
                    run_id,
                    metadata={"requirement": requirement.requirement_id},
                )
                if not self._can_use_fallback(exc):
                    continue
                try:
                    fallback_draft = self.fallback_provider.generate(
                        requirement, plan.test_type, package.context
                    )
                    case = self._draft_to_case(
                        run,
                        requirement,
                        plan,
                        fallback_draft,
                        source_versions,
                        provider_name="deterministic-fallback",
                        model_name="local-evidence-fallback",
                    )
                except (RuntimeError, ValueError) as fallback_error:
                    run.warnings.append(
                        f"Deterministic fallback failed for {requirement.requirement_id}/"
                        f"{plan.test_type.value}: {fallback_error}"
                    )
                    continue
                run.cases.append(case)
                existing.add((case.requirement_id, case.test_type))
                run.warnings.append(
                    f"Deterministic evidence fallback used for {requirement.requirement_id}/"
                    f"{plan.test_type.value}; human review is required"
                )
                self.audit.record(
                    "GENERATION_FALLBACK",
                    run_id,
                    case.test_case_id,
                    metadata={"test_type": case.test_type.value},
                )
                continue
            run.cases.append(case)
            existing.add((case.requirement_id, case.test_type))
            self.audit.record(
                "GENERATION_COMPLETED",
                run_id,
                case.test_case_id,
                metadata={"test_type": case.test_type.value},
            )
        run.status = RunStatus.AWAITING_REVIEW
        run.updated_at = utc_now()
        self.storage.save_run(run)
        self.audit.record("GENERATION_REQUESTED", run_id, metadata={"cases": str(len(run.cases))})
        return run

    def validate_cases(self, run_id: str) -> dict[str, object]:
        run = self.get_run(run_id)
        if not run.requirements:
            run = self.process(run_id)
        requirement_ids = {item.requirement_id for item in run.requirements}
        source_ids = {item.source_id for item in run.sources}
        seen: dict[str, str] = {}
        updated: list[TestCase] = []
        passed = warnings = blocked = 0
        for case in run.cases:
            findings: list[ValidationFinding] = []
            if case.requirement_id not in requirement_ids:
                findings.append(
                    self._finding(
                        "IDENTITY",
                        FindingSeverity.BLOCKING,
                        "Requirement reference is not present in this run",
                        "requirement_id",
                    )
                )
            if not case.source_references:
                findings.append(
                    self._finding(
                        "TRACEABILITY",
                        FindingSeverity.BLOCKING,
                        "At least one source reference is required",
                        "source_references",
                    )
                )
            for reference in case.source_references:
                if reference.source_id not in source_ids:
                    findings.append(
                        self._finding(
                            "TRACEABILITY",
                            FindingSeverity.BLOCKING,
                            "Source reference cannot be resolved",
                            "source_references",
                        )
                    )
            sensitive_paths = self.scanner.scan(case)
            if sensitive_paths:
                findings.append(
                    self._finding(
                        "SECURITY",
                        FindingSeverity.BLOCKING,
                        "Sensitive data pattern detected; case quarantined",
                        sensitive_paths[0].split(":", 1)[0],
                    )
                )
                self.audit.record(
                    "SECURITY_EVENT",
                    run_id,
                    case.test_case_id,
                    outcome="FAILURE",
                    metadata={"field": sensitive_paths[0].split(":", 1)[0]},
                )
            if (
                not case.scenario
                or len(case.scenario) < 10
                or not case.test_steps
                or not case.expected_results
            ):
                findings.append(
                    self._finding(
                        "SCHEMA",
                        FindingSeverity.BLOCKING,
                        "Required test case content is incomplete",
                    )
                )
            fingerprint = self.deduplication.fingerprint(case)
            if fingerprint in seen:
                severity = (
                    FindingSeverity.BLOCKING
                    if self.settings.duplicate_policy == "block"
                    else FindingSeverity.WARNING
                )
                findings.append(
                    self._finding(
                        "DUPLICATION", severity, "Case duplicates an existing scenario", "scenario"
                    )
                )
            seen[fingerprint] = case.test_case_id
            if case.open_questions:
                findings.append(
                    self._finding(
                        "EVIDENCE",
                        FindingSeverity.WARNING,
                        "Open questions require reviewer attention",
                        "open_questions",
                    )
                )
            has_blocking = any(item.severity == FindingSeverity.BLOCKING for item in findings)
            status = (
                ValidationStatus.BLOCKED
                if has_blocking
                else ValidationStatus.WARNING
                if findings
                else ValidationStatus.PASSED
            )
            review_status = (
                case.review_status
                if has_blocking or case.review_status != ReviewStatus.DRAFT
                else ReviewStatus.NEEDS_REVIEW
            )
            updated_case = case.with_validation(status, tuple(findings), review_status)
            updated.append(updated_case)
            if status == ValidationStatus.PASSED:
                passed += 1
            elif status == ValidationStatus.WARNING:
                warnings += 1
            else:
                blocked += 1
            self.audit.record(
                "VALIDATION_COMPLETED",
                run_id,
                case.test_case_id,
                outcome="FAILURE" if has_blocking else "SUCCESS",
                metadata={"status": status.value},
            )
        run.cases = updated
        run.status = RunStatus.AWAITING_REVIEW
        run.updated_at = utc_now()
        self.storage.save_run(run)
        return {
            "run_id": run_id,
            "cases_validated": len(updated),
            "passed": passed,
            "warnings": warnings,
            "blocked": blocked,
        }

    def review_case(
        self,
        run_id: str,
        case_id: str,
        action: str,
        actor: str = "local-reviewer",
        reason: str = "",
        priority: str | None = None,
    ) -> TestCase:
        run = self.get_run(run_id)
        case = self._case(run, case_id)
        action = action.upper()
        transitions = {
            "APPROVE": ReviewStatus.APPROVED,
            "REJECT": ReviewStatus.REJECTED,
            "CLARIFY": ReviewStatus.NEEDS_CLARIFICATION,
            "REVIEW": ReviewStatus.NEEDS_REVIEW,
        }
        if action == "APPROVE" and case.validation_status in {
            ValidationStatus.BLOCKED,
            ValidationStatus.FAILED,
        }:
            raise PipelineError("A case with blocking validation findings cannot be approved")
        if action not in transitions:
            raise PipelineError("Unsupported review action")
        review_case = case
        if priority is not None:
            try:
                reviewer_priority = Priority(priority.upper())
            except ValueError as exc:
                raise PipelineError(
                    "Priority must be CRITICAL, HIGH, MEDIUM, LOW, or UNKNOWN"
                ) from exc
            review_case = replace(
                case,
                priority=reviewer_priority,
                review_history=(
                    *case.review_history,
                    ReviewEvent(
                        "EDITED",
                        actor,
                        reason=f"Reviewer priority set to {reviewer_priority.value}",
                    ),
                ),
            )
        updated = review_case.with_review(transitions[action], actor, reason)
        run.cases = [updated if item.test_case_id == case_id else item for item in run.cases]
        run.updated_at = utc_now()
        self.storage.save_run(run)
        event_name = (
            "CASE_APPROVED"
            if action == "APPROVE"
            else "CASE_REJECTED"
            if action == "REJECT"
            else "CASE_EDITED"
        )
        self.audit.record(event_name, run_id, case_id, metadata={"action": action})
        return updated

    def edit_case(self, run_id: str, case_id: str, changes: dict[str, Any]) -> TestCase:
        run = self.get_run(run_id)
        case = self._case(run, case_id)
        allowed = {"scenario", "expected_results", "preconditions", "priority"}
        unknown = set(changes) - allowed
        if unknown:
            raise PipelineError(
                "Only scenario, preconditions, expected results, and priority can be edited"
            )
        values: dict[str, Any] = {}
        if "scenario" in changes:
            values["scenario"] = str(changes["scenario"]).strip()
        if "expected_results" in changes:
            values["expected_results"] = tuple(
                str(item) for item in changes["expected_results"] if str(item).strip()
            )
        if "preconditions" in changes:
            values["preconditions"] = tuple(
                str(item) for item in changes["preconditions"] if str(item).strip()
            )
        if "priority" in changes:
            try:
                values["priority"] = Priority(str(changes["priority"]).upper())
            except ValueError as exc:
                raise PipelineError(
                    "Priority must be CRITICAL, HIGH, MEDIUM, LOW, or UNKNOWN"
                ) from exc
        history = (
            *case.review_history,
            ReviewEvent(
                "EDITED",
                "local-reviewer",
                reason=f"Manual case edit: {', '.join(sorted(values))}",
            ),
        )
        updated = replace(case, **values, review_history=history, updated_at=utc_now())
        run.cases = [updated if item.test_case_id == case_id else item for item in run.cases]
        self.storage.save_run(run)
        self.audit.record("CASE_EDITED", run_id, case_id)
        return updated

    def coverage(self, run_id: str) -> list[dict[str, object]]:
        run = self.get_run(run_id)
        if not run.requirements:
            run = self.process(run_id)
        if not run.scenario_plans:
            self.plan(run_id)
            run = self.get_run(run_id)
        return self.coverage_service.calculate(run.requirements, run.scenario_plans, run.cases)

    def traceability(self, run_id: str) -> list[dict[str, object]]:
        run = self.get_run(run_id)
        rows: list[dict[str, object]] = []
        for requirement in run.requirements:
            linked_criteria = [
                criterion
                for criterion in run.criteria
                if requirement.requirement_id in criterion.requirement_ids
            ]
            linked_paths = [
                path
                for path in run.flow_paths
                if requirement.requirement_id in path.requirement_ids
            ]
            linked_cases = [
                case for case in run.cases if case.requirement_id == requirement.requirement_id
            ]
            rows.append(
                {
                    "requirement_id": requirement.requirement_id,
                    "description": requirement.description,
                    "jira_story_id": requirement.related_story_id,
                    "criteria": [
                        {"id": item.criterion_id, "text": item.text} for item in linked_criteria
                    ],
                    "flow_paths": [
                        {"id": item.path_id, "name": item.name} for item in linked_paths
                    ],
                    "test_cases": [
                        {
                            "id": item.test_case_number,
                            "internal_id": item.test_case_id,
                            "status": item.review_status.value,
                        }
                        for item in linked_cases
                    ],
                }
            )
        return rows

    def reports(self, run_id: str) -> dict[str, object]:
        run = self.get_run(run_id)
        coverage = self.coverage(run_id)
        traceability = self.traceability(run_id)
        return {
            "summary": {
                "run_id": run.run_id,
                "project_name": run.project_name,
                "source_count": len(run.sources),
                "requirements": len(run.requirements),
                "criteria": len(run.criteria),
                "flow_paths": len(run.flow_paths),
                "test_cases": len(run.cases),
                "coverage": round(self._coverage_average(coverage), 1) if coverage else 0.0,
                "warnings": len(run.warnings),
                "priority_distribution": {
                    priority.value: sum(case.priority == priority for case in run.cases)
                    for priority in Priority
                },
            },
            "traceability": traceability,
            "coverage": coverage,
            "quality": {
                "passed": sum(
                    case.validation_status == ValidationStatus.PASSED for case in run.cases
                ),
                "warnings": sum(
                    case.validation_status == ValidationStatus.WARNING for case in run.cases
                ),
                "blocked": sum(
                    case.validation_status == ValidationStatus.BLOCKED for case in run.cases
                ),
            },
            "review": {
                status.value: sum(case.review_status == status for case in run.cases)
                for status in ReviewStatus
            },
            "change_impact": [],
        }

    def _provider(self) -> AIProvider:
        if self.settings.ai_provider.lower() == "google":
            return GoogleAIStudioProvider(
                self.settings.ai_model_name,
                self.settings.ai_api_key_env_var,
                self.settings.ai_endpoint,
                self.settings.ai_model_id,
                self.settings.ai_timeout_seconds,
                max_output_tokens=self.settings.ai_max_output_tokens,
            )
        if self.settings.ai_provider.lower() == "openai":
            return OpenAICompatibleProvider(
                self.settings.ai_model_name,
                self.settings.ai_api_key_env_var,
                self.settings.ai_endpoint,
            )
        return DeterministicAIProvider(self.settings.ai_model_name)

    @staticmethod
    def _metadata(
        source_id: str,
        kind: str,
        filename: str,
        checksum: str,
        extraction: SourceExtraction,
        source_url: str | None,
    ) -> SourceMetadata:
        item_count = len(extraction.requirements) + len(extraction.criteria)
        if extraction.flow:
            item_count += len(extraction.flow.nodes) + len(extraction.flow.paths)
        warning_count = len(extraction.warnings)
        source_type = {
            "brd": SourceType.BRD_EXCEL,
            "jira": SourceType.JIRA_MARKDOWN,
            "flow": SourceType.FLOW_PDF,
        }[kind]
        status = "COMPLETED_WITH_WARNINGS" if warning_count else "COMPLETED"
        return SourceMetadata(
            source_id,
            source_type,
            filename,
            checksum,
            ProcessingStatus(status),
            item_count,
            warning_count,
            "",
            source_url,
        )

    def _draft_to_case(
        self,
        run: RunState,
        requirement: Requirement,
        plan: ScenarioPlan,
        draft: dict[str, object],
        source_versions: dict[str, str],
        provider_name: str | None = None,
        model_name: str | None = None,
    ) -> TestCase:
        raw_steps = self._mapping_list(draft.get("test_steps", []))
        steps = tuple(
            TestStep(
                int(str(item.get("step_number", index))),
                str(item.get("action", "")),
                str(item.get("expected_result", "")),
            )
            for index, item in enumerate(raw_steps, start=1)
            if isinstance(item, dict)
        )
        raw_data = self._mapping_list(draft.get("test_data", []))
        test_data = tuple(
            TestDataItem(
                str(item.get("description", "")),
                str(item.get("value")) if item.get("value") is not None else None,
                str(item.get("data_type")) if item.get("data_type") is not None else None,
                bool(item.get("masked", True)),
            )
            for item in raw_data
        )
        return TestCase(
            test_case_id=str(uuid.uuid4()),
            test_case_number=self._next_case_number(run),
            schema_version=SchemaRegistry.current_version(),
            requirement_id=requirement.requirement_id,
            scenario=str(draft.get("scenario", "")),
            preconditions=tuple(
                item for item in self._string_list(draft.get("preconditions", [])) if item.strip()
            ),
            test_data=test_data,
            test_steps=steps,
            expected_results=tuple(
                item
                for item in self._string_list(draft.get("expected_results", []))
                if item.strip()
            ),
            priority=requirement.priority,
            test_type=plan.test_type,
            source_references=plan.source_references,
            review_status=ReviewStatus.DRAFT,
            validation_status=ValidationStatus.FAILED,
            generation_metadata=GenerationMetadata(
                run_id=run.run_id,
                provider_name=provider_name or self.provider_name,
                model_name=model_name or self.settings.ai_model_name,
                prompt_version="generate_v1.0",
                schema_version=SchemaRegistry.current_version(),
                source_versions=source_versions,
            ),
            jira_story_id=requirement.related_story_id,
            assumptions=self._string_list(draft.get("assumptions", [])),
            open_questions=self._string_list(draft.get("open_questions", [])),
            flow_path_id=plan.flow_path_id,
        )

    @staticmethod
    def _finding(
        gate: str, severity: FindingSeverity, message: str, field: str | None = None
    ) -> ValidationFinding:
        return ValidationFinding(str(uuid.uuid4()), gate, severity, message, field)

    @staticmethod
    def _case(run: RunState, case_id: str) -> TestCase:
        for case in run.cases:
            if case.test_case_id == case_id:
                return case
        raise PipelineError("Test case was not found")

    @staticmethod
    def _string_list(value: object) -> tuple[str, ...]:
        if not isinstance(value, list):
            return ()
        return tuple(str(item) for item in value if str(item).strip())

    @staticmethod
    def _mapping_list(value: object) -> list[dict[str, object]]:
        if not isinstance(value, list):
            return []
        return [cast(dict[str, object], item) for item in value if isinstance(item, dict)]

    @staticmethod
    def _coverage_average(records: list[dict[str, object]]) -> float:
        values = [item.get("coverage_percentage", 0.0) for item in records]
        numeric = [float(value) for value in values if isinstance(value, (int, float))]
        return sum(numeric) / len(numeric) if numeric else 0.0

    @staticmethod
    def _next_case_number(run: RunState) -> str:
        numbers = [
            int(match.group(1))
            for case in run.cases
            if (match := re.fullmatch(r"TC-(\d+)", case.test_case_number))
        ]
        return f"TC-{max(numbers, default=0) + 1:03d}"

    def _can_use_fallback(self, error: Exception) -> bool:
        if not self.settings.ai_fallback_enabled or self.provider_name.lower() != "google":
            return False
        message = str(error).lower()
        return "credentials unavailable" not in message and all(
            marker not in message for marker in ("http 401", "http 403", "http 404")
        )
