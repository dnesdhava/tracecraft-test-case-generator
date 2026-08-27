from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from tcg.domain.models import (
    AcceptanceCriterion,
    ApplicabilityStatus,
    EntityType,
    FlowPath,
    LinkStatus,
    Requirement,
    ScenarioPlan,
    SourceLocation,
    TestCase,
    TestType,
    TraceLink,
)


@dataclass(frozen=True)
class NormalizationResult:
    requirements: tuple[Requirement, ...]
    trace_links: tuple[TraceLink, ...]
    issues: tuple[str, ...]


class RequirementNormalizer:
    """Correlate extracted BRD, JIRA, and flow evidence without inventing links."""

    def normalize(
        self,
        requirements: list[Requirement],
        criteria: list[AcceptanceCriterion],
        flow_paths: list[FlowPath],
    ) -> NormalizationResult:
        criterion_by_requirement: dict[str, list[str]] = {}
        story_ids: set[str] = set()
        links: list[TraceLink] = []
        issues: list[str] = []
        for criterion in criteria:
            story_ids.add(criterion.story_id)
            for requirement_id in criterion.requirement_ids:
                criterion_by_requirement.setdefault(requirement_id, []).append(
                    criterion.criterion_id
                )
                links.append(
                    TraceLink(
                        from_id=criterion.story_id,
                        from_type=EntityType.STORY,
                        to_id=criterion.criterion_id,
                        to_type=EntityType.CRITERION,
                        status=LinkStatus.CONFIRMED,
                        confidence=1.0,
                        evidence="Criterion declares its parent story",
                    )
                )

        paths_by_requirement: dict[str, list[str]] = {}
        for flow_path in flow_paths:
            for requirement_id in flow_path.requirement_ids:
                paths_by_requirement.setdefault(requirement_id, []).append(flow_path.path_id)

        normalized: list[Requirement] = []
        for requirement in requirements:
            requirement_criteria = tuple(
                sorted(criterion_by_requirement.get(requirement.requirement_id, []))
            )
            requirement_paths = tuple(
                sorted(paths_by_requirement.get(requirement.requirement_id, []))
            )
            story_id = next(
                (
                    criterion.story_id
                    for criterion in criteria
                    if requirement.requirement_id in criterion.requirement_ids
                ),
                None,
            )
            if story_id:
                links.append(
                    TraceLink(
                        from_id=requirement.requirement_id,
                        from_type=EntityType.REQUIREMENT,
                        to_id=story_id,
                        to_type=EntityType.STORY,
                        status=LinkStatus.CONFIRMED,
                        confidence=1.0,
                        evidence="Requirement ID is declared in story acceptance criteria",
                    )
                )
            else:
                issues.append(
                    f"GAP: {requirement.requirement_id} has no linked JIRA acceptance criterion"
                )
            if requirement_paths:
                for path_id in requirement_paths:
                    links.append(
                        TraceLink(
                            from_id=requirement.requirement_id,
                            from_type=EntityType.REQUIREMENT,
                            to_id=path_id,
                            to_type=EntityType.FLOW_PATH,
                            status=LinkStatus.CONFIRMED,
                            confidence=0.95,
                            evidence="Flow path declares the requirement ID",
                        )
                    )
            else:
                issues.append(f"GAP: {requirement.requirement_id} has no linked flow path")
            normalized.append(
                Requirement(
                    **{
                        **requirement.__dict__,
                        "related_story_id": story_id,
                        "criterion_ids": requirement_criteria,
                        "flow_path_ids": requirement_paths,
                    }
                )
            )

        for criterion in criteria:
            if not criterion.requirement_ids:
                issues.append(f"GAP: {criterion.criterion_id} has no linked BRD requirement")
        if not story_ids and requirements:
            issues.append("GAP: no JIRA story was available for normalization")
        return NormalizationResult(tuple(normalized), tuple(links), tuple(sorted(set(issues))))


class ScenarioService:
    """Apply evidence-first applicability rules for the seven scenario classes."""

    scenario_types = tuple(TestType)

    def plan(
        self,
        requirement: Requirement,
        flow_paths: list[FlowPath],
        selected_types: set[TestType] | None = None,
    ) -> list[ScenarioPlan]:
        selected = selected_types or set(self.scenario_types)
        related_paths = [path for path in flow_paths if path.path_id in requirement.flow_path_ids]
        plans: list[ScenarioPlan] = []
        for test_type in self.scenario_types:
            if test_type not in selected:
                continue
            status, rationale = self._applicability(requirement, test_type, related_paths)
            refs: tuple[SourceLocation, ...] = (requirement.location,)
            path_id = (
                related_paths[0].path_id
                if related_paths and test_type == TestType.END_TO_END
                else None
            )
            if path_id:
                refs = (*refs, related_paths[0].location)
            plans.append(
                ScenarioPlan(
                    requirement.requirement_id, test_type, status, rationale, refs, path_id
                )
            )
        return plans

    @staticmethod
    def _applicability(
        requirement: Requirement,
        test_type: TestType,
        flow_paths: list[FlowPath],
    ) -> tuple[ApplicabilityStatus, str]:
        evidence = " ".join(
            [
                requirement.description,
                requirement.business_rule,
                requirement.validation,
                requirement.expected_behaviour,
                requirement.functional_requirement,
                " ".join(requirement.dependencies),
            ]
        ).lower()
        if test_type == TestType.POSITIVE:
            return ApplicabilityStatus.APPLICABLE, "The requirement defines testable behavior"
        if test_type == TestType.END_TO_END:
            if any(path.complete for path in flow_paths):
                return ApplicabilityStatus.APPLICABLE, "A complete linked flow path is available"
            return ApplicabilityStatus.EXCLUDED, "No complete linked flow path is available"
        if test_type == TestType.BOUNDARY:
            has_boundary = bool(
                re.search(r"(?:usd|\$|minimum|maximum|limit|inclusive|\d[\d,.]*)", evidence)
            ) and bool(
                re.search(r"(?:amount|balance|total|limit|range|two decimal|five minute)", evidence)
            )
            return (
                (
                    ApplicabilityStatus.APPLICABLE,
                    "Explicit numeric, precision, or time boundary is present",
                )
                if has_boundary
                else (ApplicabilityStatus.EXCLUDED, "No explicit boundary value is present")
            )
        if test_type == TestType.VALIDATION:
            has_validation = bool(
                re.search(
                    r"required|mandatory|format|validat|precision|owned|active|eligible", evidence
                )
            )
            return (
                (
                    ApplicabilityStatus.APPLICABLE,
                    "The source states a field or business-rule validation",
                )
                if has_validation
                else (ApplicabilityStatus.EXCLUDED, "No explicit validation rule is present")
            )
        if test_type == TestType.NEGATIVE:
            has_negative = bool(
                re.search(
                    r"reject|invalid|insufficient|duplicate|exceed|unauthor|failure|error", evidence
                )
            )
            return (
                (
                    ApplicabilityStatus.APPLICABLE,
                    "The source explicitly describes a rejection or invalid outcome",
                )
                if has_negative
                else (
                    ApplicabilityStatus.EXCLUDED,
                    "No explicit rejection or invalid outcome is present",
                )
            )
        if test_type == TestType.EXCEPTION:
            has_exception = bool(
                re.search(r"fail|failure|unavailable|timeout|error|recover", evidence)
            )
            return (
                (
                    ApplicabilityStatus.APPLICABLE,
                    "The source explicitly describes a failure or exception outcome",
                )
                if has_exception
                else (
                    ApplicabilityStatus.EXCLUDED,
                    "No explicit exception or recovery behavior is present",
                )
            )
        if test_type == TestType.INTEGRATION:
            if requirement.dependencies:
                return (
                    ApplicabilityStatus.APPLICABLE,
                    "The requirement names dependent services or systems",
                )
            return ApplicabilityStatus.EXCLUDED, "No external dependency is named"
        return ApplicabilityStatus.UNRESOLVED, "Applicability requires human clarification"


class DeduplicationService:
    """Create deterministic fingerprints and identify exact or close case duplicates."""

    @staticmethod
    def fingerprint(case: TestCase) -> str:
        normalized = " ".join(case.scenario.lower().split())
        payload = f"{normalized}|{case.test_type.value}|{case.requirement_id}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def similarity(left: TestCase, right: TestCase) -> float:
        return SequenceMatcher(None, left.scenario.lower(), right.scenario.lower()).ratio()

    def find_duplicates(
        self, cases: list[TestCase], threshold: float = 0.85
    ) -> dict[str, list[str]]:
        fingerprints: dict[str, list[str]] = {}
        for case in cases:
            fingerprints.setdefault(self.fingerprint(case), []).append(case.test_case_id)
        duplicates = {key: ids for key, ids in fingerprints.items() if len(ids) > 1}
        for index, left in enumerate(cases):
            for right in cases[index + 1 :]:
                if left.test_case_id == right.test_case_id:
                    continue
                if self.similarity(left, right) >= threshold and self.fingerprint(
                    left
                ) != self.fingerprint(right):
                    duplicates.setdefault("near", []).extend(
                        [left.test_case_id, right.test_case_id]
                    )
        return {key: sorted(set(ids)) for key, ids in duplicates.items()}


class CoverageService:
    """Compute explainable requirement and scenario-class coverage records."""

    def calculate(
        self, requirements: list[Requirement], plans: list[ScenarioPlan], cases: list[TestCase]
    ) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []
        for requirement in requirements:
            requirement_plans = [
                plan for plan in plans if plan.requirement_id == requirement.requirement_id
            ]
            linked = [case for case in cases if case.requirement_id == requirement.requirement_id]
            applicable = [
                plan.test_type.value
                for plan in requirement_plans
                if plan.applicability == ApplicabilityStatus.APPLICABLE
            ]
            covered = sorted({case.test_type.value for case in linked})
            excluded = [
                {"test_type": plan.test_type.value, "reason": plan.rationale}
                for plan in requirement_plans
                if plan.applicability == ApplicabilityStatus.EXCLUDED
            ]
            unresolved = [
                plan.test_type.value
                for plan in requirement_plans
                if plan.applicability == ApplicabilityStatus.UNRESOLVED
            ]
            denominator = len(set(applicable))
            percentage = (
                round(len(set(covered) & set(applicable)) / denominator * 100, 1)
                if denominator
                else 0.0
            )
            records.append(
                {
                    "entity_id": requirement.requirement_id,
                    "entity_type": "REQUIREMENT",
                    "description": requirement.description,
                    "applicable": applicable,
                    "covered": covered,
                    "excluded": excluded,
                    "unresolved": unresolved,
                    "linked_case_ids": [case.test_case_id for case in linked],
                    "coverage_percentage": percentage,
                    "has_approved_case": any(
                        case.review_status.value == "APPROVED" for case in linked
                    ),
                    "orphan": not linked,
                }
            )
        return records
