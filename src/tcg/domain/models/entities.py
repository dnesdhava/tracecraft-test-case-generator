from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass, replace
from datetime import UTC, datetime
from enum import Enum
from typing import Any, TypeVar

from .enums import (
    ApplicabilityStatus,
    DataClassification,
    EntityType,
    FindingSeverity,
    LinkStatus,
    PathType,
    Priority,
    ProcessingStatus,
    ReviewStatus,
    RunStatus,
    SourceType,
    TestType,
    ValidationStatus,
)

T = TypeVar("T")
TEnum = TypeVar("TEnum", bound=Enum)


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class BoundingBox:
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass(frozen=True)
class SourceLocation:
    source_id: str
    label: str
    page_number: int | None = None
    sheet_name: str | None = None
    row_number: int | None = None
    section_path: tuple[str, ...] = ()
    node_id: str | None = None
    path_id: str | None = None
    bounding_box: BoundingBox | None = None

    def display(self) -> str:
        parts = [self.label]
        if self.sheet_name:
            parts.append(f"sheet {self.sheet_name}")
        if self.row_number is not None:
            parts.append(f"row {self.row_number}")
        if self.page_number is not None:
            parts.append(f"page {self.page_number}")
        if self.path_id:
            parts.append(self.path_id)
        return " | ".join(parts)


@dataclass(frozen=True)
class SourceMetadata:
    source_id: str
    source_type: SourceType
    filename: str
    checksum: str
    status: ProcessingStatus
    item_count: int = 0
    warning_count: int = 0
    message: str = ""
    source_url: str | None = None
    uploaded_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class AcceptanceCriterion:
    criterion_id: str
    story_id: str
    text: str
    requirement_ids: tuple[str, ...]
    location: SourceLocation
    confidence: float = 1.0


@dataclass(frozen=True)
class Requirement:
    requirement_id: str
    description: str
    business_process: str
    functional_requirement: str
    business_rule: str
    input_field: str
    validation: str
    expected_behaviour: str
    priority: Priority
    dependencies: tuple[str, ...]
    source_id: str
    location: SourceLocation
    related_story_id: str | None = None
    criterion_ids: tuple[str, ...] = ()
    flow_path_ids: tuple[str, ...] = ()
    confidence: float = 1.0
    original_text: str = ""

    @property
    def normalized_text(self) -> str:
        return " ".join(self.description.lower().split())

    @property
    def behavior_statement(self) -> str:
        return self.expected_behaviour or self.functional_requirement or self.description


@dataclass(frozen=True)
class FlowNode:
    node_id: str
    label: str
    node_type: str
    page_number: int
    requirement_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class FlowEdge:
    edge_id: str
    from_node_id: str
    to_node_id: str
    label: str
    path_id: str | None = None
    ambiguous: bool = False


@dataclass(frozen=True)
class FlowPath:
    path_id: str
    name: str
    path_type: PathType
    node_ids: tuple[str, ...]
    requirement_ids: tuple[str, ...]
    complete: bool
    location: SourceLocation
    confidence: float = 1.0


@dataclass(frozen=True)
class FlowExtraction:
    source_id: str
    page_count: int
    nodes: tuple[FlowNode, ...]
    edges: tuple[FlowEdge, ...]
    paths: tuple[FlowPath, ...]
    warnings: tuple[str, ...] = ()
    confidence: float = 1.0


@dataclass(frozen=True)
class SourceExtraction:
    source_id: str
    source_type: SourceType
    requirements: tuple[Requirement, ...] = ()
    criteria: tuple[AcceptanceCriterion, ...] = ()
    flow: FlowExtraction | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class TraceLink:
    from_id: str
    from_type: EntityType
    to_id: str
    to_type: EntityType
    status: LinkStatus = LinkStatus.CONFIRMED
    confidence: float = 1.0
    evidence: str = ""


@dataclass(frozen=True)
class ScenarioPlan:
    requirement_id: str
    test_type: TestType
    applicability: ApplicabilityStatus
    rationale: str
    source_references: tuple[SourceLocation, ...]
    flow_path_id: str | None = None


@dataclass(frozen=True)
class TestDataItem:
    description: str
    value: str | None = None
    data_type: str | None = None
    masked: bool = True


@dataclass(frozen=True)
class TestStep:
    step_number: int
    action: str
    expected_result: str


@dataclass(frozen=True)
class GenerationMetadata:
    run_id: str
    provider_name: str
    model_name: str
    prompt_version: str
    schema_version: str
    source_versions: dict[str, str]
    generated_at: datetime = field(default_factory=utc_now)
    input_tokens: int | None = None
    output_tokens: int | None = None


@dataclass(frozen=True)
class ValidationFinding:
    finding_id: str
    gate: str
    severity: FindingSeverity
    message: str
    field: str | None = None


@dataclass(frozen=True)
class ReviewEvent:
    action: str
    actor: str
    timestamp: datetime = field(default_factory=utc_now)
    reason: str = ""


@dataclass(frozen=True)
class TestCase:
    test_case_id: str
    test_case_number: str
    schema_version: str
    requirement_id: str
    scenario: str
    preconditions: tuple[str, ...]
    test_data: tuple[TestDataItem, ...]
    test_steps: tuple[TestStep, ...]
    expected_results: tuple[str, ...]
    priority: Priority
    test_type: TestType
    source_references: tuple[SourceLocation, ...]
    review_status: ReviewStatus
    validation_status: ValidationStatus
    generation_metadata: GenerationMetadata
    jira_story_id: str | None = None
    assumptions: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()
    validation_findings: tuple[ValidationFinding, ...] = ()
    review_history: tuple[ReviewEvent, ...] = ()
    flow_path_id: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def with_validation(
        self,
        status: ValidationStatus,
        findings: tuple[ValidationFinding, ...],
        review_status: ReviewStatus | None = None,
    ) -> TestCase:
        return TestCase(
            **{
                **self.__dict__,
                "validation_status": status,
                "validation_findings": findings,
                "review_status": review_status or self.review_status,
                "updated_at": utc_now(),
            }
        )

    def with_review(self, status: ReviewStatus, actor: str, reason: str = "") -> TestCase:
        event = ReviewEvent(action=status.value, actor=actor, reason=reason)
        return TestCase(
            **{
                **self.__dict__,
                "review_status": status,
                "review_history": (*self.review_history, event),
                "updated_at": utc_now(),
            }
        )


@dataclass
class RunState:
    run_id: str
    project_name: str
    feature_context: str
    classification: DataClassification
    status: RunStatus = RunStatus.CREATED
    sources: list[SourceMetadata] = field(default_factory=list)
    extractions: dict[str, SourceExtraction] = field(default_factory=dict)
    requirements: list[Requirement] = field(default_factory=list)
    criteria: list[AcceptanceCriterion] = field(default_factory=list)
    flow_paths: list[FlowPath] = field(default_factory=list)
    trace_links: list[TraceLink] = field(default_factory=list)
    scenario_plans: list[ScenarioPlan] = field(default_factory=list)
    cases: list[TestCase] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


def jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return {item.name: jsonable(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [jsonable(item) for item in value]
    return value


def parse_datetime(value: str | None) -> datetime:
    if not value:
        return utc_now()
    return datetime.fromisoformat(value)


def enum_value(enum_cls: type[TEnum], value: str | None, default: TEnum) -> TEnum:
    if value is None:
        return default
    return enum_cls(value)


def location_from_dict(data: dict[str, Any]) -> SourceLocation:
    box = data.get("bounding_box")
    return SourceLocation(
        source_id=str(data.get("source_id", "")),
        label=str(data.get("label", "")),
        page_number=data.get("page_number"),
        sheet_name=data.get("sheet_name"),
        row_number=data.get("row_number"),
        section_path=tuple(data.get("section_path", [])),
        node_id=data.get("node_id"),
        path_id=data.get("path_id"),
        bounding_box=BoundingBox(**box) if box else None,
    )


def requirement_from_dict(data: dict[str, Any]) -> Requirement:
    return Requirement(
        requirement_id=str(data["requirement_id"]),
        description=str(data.get("description", "")),
        business_process=str(data.get("business_process", "")),
        functional_requirement=str(data.get("functional_requirement", "")),
        business_rule=str(data.get("business_rule", "")),
        input_field=str(data.get("input_field", "")),
        validation=str(data.get("validation", "")),
        expected_behaviour=str(data.get("expected_behaviour", "")),
        priority=enum_value(Priority, data.get("priority"), Priority.UNKNOWN),
        dependencies=tuple(data.get("dependencies", [])),
        source_id=str(data.get("source_id", "")),
        location=location_from_dict(data.get("location", {})),
        related_story_id=data.get("related_story_id"),
        criterion_ids=tuple(data.get("criterion_ids", [])),
        flow_path_ids=tuple(data.get("flow_path_ids", [])),
        confidence=float(data.get("confidence", 1.0)),
        original_text=str(data.get("original_text", "")),
    )


def criterion_from_dict(data: dict[str, Any]) -> AcceptanceCriterion:
    return AcceptanceCriterion(
        criterion_id=str(data["criterion_id"]),
        story_id=str(data.get("story_id", "")),
        text=str(data.get("text", "")),
        requirement_ids=tuple(data.get("requirement_ids", [])),
        location=location_from_dict(data.get("location", {})),
        confidence=float(data.get("confidence", 1.0)),
    )


def flow_path_from_dict(data: dict[str, Any]) -> FlowPath:
    return FlowPath(
        path_id=str(data["path_id"]),
        name=str(data.get("name", "")),
        path_type=enum_value(PathType, data.get("path_type"), PathType.ALTERNATE),
        node_ids=tuple(data.get("node_ids", [])),
        requirement_ids=tuple(data.get("requirement_ids", [])),
        complete=bool(data.get("complete", True)),
        location=location_from_dict(data.get("location", {})),
        confidence=float(data.get("confidence", 1.0)),
    )


def source_metadata_from_dict(data: dict[str, Any]) -> SourceMetadata:
    return SourceMetadata(
        source_id=str(data["source_id"]),
        source_type=enum_value(SourceType, data.get("source_type"), SourceType.BRD_EXCEL),
        filename=str(data.get("filename", "")),
        checksum=str(data.get("checksum", "")),
        status=enum_value(ProcessingStatus, data.get("status"), ProcessingStatus.COMPLETED),
        item_count=int(data.get("item_count", 0)),
        warning_count=int(data.get("warning_count", 0)),
        message=str(data.get("message", "")),
        source_url=data.get("source_url"),
        uploaded_at=parse_datetime(data.get("uploaded_at")),
    )


def test_case_from_dict(data: dict[str, Any]) -> TestCase:
    metadata_data = data.get("generation_metadata", {})
    metadata = GenerationMetadata(
        run_id=str(metadata_data.get("run_id", "")),
        provider_name=str(metadata_data.get("provider_name", "deterministic-evidence")),
        model_name=str(metadata_data.get("model_name", "local-rules")),
        prompt_version=str(metadata_data.get("prompt_version", "local-v1")),
        schema_version=str(metadata_data.get("schema_version", data.get("schema_version", "1.0"))),
        source_versions=dict(metadata_data.get("source_versions", {})),
        generated_at=parse_datetime(metadata_data.get("generated_at")),
        input_tokens=metadata_data.get("input_tokens"),
        output_tokens=metadata_data.get("output_tokens"),
    )
    test_data = tuple(TestDataItem(**item) for item in data.get("test_data", []))
    steps = tuple(TestStep(**item) for item in data.get("test_steps", []))
    findings = tuple(
        ValidationFinding(
            finding_id=str(item.get("finding_id", "")),
            gate=str(item.get("gate", "")),
            severity=enum_value(FindingSeverity, item.get("severity"), FindingSeverity.WARNING),
            message=str(item.get("message", "")),
            field=item.get("field"),
        )
        for item in data.get("validation_findings", [])
    )
    history = tuple(
        ReviewEvent(
            action=str(item.get("action", "")),
            actor=str(item.get("actor", "")),
            timestamp=parse_datetime(item.get("timestamp")),
            reason=str(item.get("reason", "")),
        )
        for item in data.get("review_history", [])
    )
    return TestCase(
        test_case_id=str(data["test_case_id"]),
        test_case_number=str(data.get("test_case_number", "")),
        schema_version=str(data.get("schema_version", "1.0")),
        requirement_id=str(data.get("requirement_id", "")),
        scenario=str(data.get("scenario", "")),
        preconditions=tuple(data.get("preconditions", [])),
        test_data=test_data,
        test_steps=steps,
        expected_results=tuple(data.get("expected_results", [])),
        priority=enum_value(Priority, data.get("priority"), Priority.UNKNOWN),
        test_type=enum_value(TestType, data.get("test_type"), TestType.POSITIVE),
        source_references=tuple(
            location_from_dict(item) for item in data.get("source_references", [])
        ),
        review_status=enum_value(ReviewStatus, data.get("review_status"), ReviewStatus.DRAFT),
        validation_status=enum_value(
            ValidationStatus, data.get("validation_status"), ValidationStatus.FAILED
        ),
        generation_metadata=metadata,
        jira_story_id=data.get("jira_story_id"),
        assumptions=tuple(data.get("assumptions", [])),
        open_questions=tuple(data.get("open_questions", [])),
        validation_findings=findings,
        review_history=history,
        flow_path_id=data.get("flow_path_id"),
        created_at=parse_datetime(data.get("created_at")),
        updated_at=parse_datetime(data.get("updated_at")),
    )


def source_extraction_from_dict(data: dict[str, Any]) -> SourceExtraction:
    flow_data = data.get("flow")
    flow = None
    if flow_data:
        nodes = tuple(FlowNode(**node) for node in flow_data.get("nodes", []))
        edges = tuple(FlowEdge(**edge) for edge in flow_data.get("edges", []))
        paths = tuple(flow_path_from_dict(item) for item in flow_data.get("paths", []))
        flow = FlowExtraction(
            source_id=str(flow_data.get("source_id", data.get("source_id", ""))),
            page_count=int(flow_data.get("page_count", 1)),
            nodes=nodes,
            edges=edges,
            paths=paths,
            warnings=tuple(flow_data.get("warnings", [])),
            confidence=float(flow_data.get("confidence", 1.0)),
        )
    return SourceExtraction(
        source_id=str(data["source_id"]),
        source_type=enum_value(SourceType, data.get("source_type"), SourceType.BRD_EXCEL),
        requirements=tuple(requirement_from_dict(item) for item in data.get("requirements", [])),
        criteria=tuple(criterion_from_dict(item) for item in data.get("criteria", [])),
        flow=flow,
        warnings=tuple(data.get("warnings", [])),
    )


def run_from_dict(data: dict[str, Any]) -> RunState:
    extractions = {
        key: source_extraction_from_dict(value)
        for key, value in data.get("extractions", {}).items()
    }
    cases = [test_case_from_dict(item) for item in data.get("cases", [])]
    cases = [
        replace(case, test_case_number=case.test_case_number or f"TC-{index:03d}")
        for index, case in enumerate(cases, start=1)
    ]
    return RunState(
        run_id=str(data["run_id"]),
        project_name=str(data.get("project_name", "Demo Project")),
        feature_context=str(data.get("feature_context", "")),
        classification=enum_value(
            DataClassification, data.get("classification"), DataClassification.INTERNAL
        ),
        status=enum_value(RunStatus, data.get("status"), RunStatus.CREATED),
        sources=[source_metadata_from_dict(item) for item in data.get("sources", [])],
        extractions=extractions,
        requirements=[requirement_from_dict(item) for item in data.get("requirements", [])],
        criteria=[criterion_from_dict(item) for item in data.get("criteria", [])],
        flow_paths=[flow_path_from_dict(item) for item in data.get("flow_paths", [])],
        trace_links=[TraceLink(**item) for item in data.get("trace_links", [])],
        scenario_plans=[
            ScenarioPlan(
                requirement_id=str(item.get("requirement_id", "")),
                test_type=enum_value(TestType, item.get("test_type"), TestType.POSITIVE),
                applicability=enum_value(
                    ApplicabilityStatus, item.get("applicability"), ApplicabilityStatus.APPLICABLE
                ),
                rationale=str(item.get("rationale", "")),
                source_references=tuple(
                    location_from_dict(ref) for ref in item.get("source_references", [])
                ),
                flow_path_id=item.get("flow_path_id"),
            )
            for item in data.get("scenario_plans", [])
        ],
        cases=cases,
        warnings=list(data.get("warnings", [])),
        created_at=parse_datetime(data.get("created_at")),
        updated_at=parse_datetime(data.get("updated_at")),
    )
