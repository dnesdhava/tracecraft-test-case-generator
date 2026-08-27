from __future__ import annotations

import re
from pathlib import Path

from tcg.domain.models import (
    AcceptanceCriterion,
    SourceExtraction,
    SourceLocation,
    SourceType,
)


class JiraMarkdownParser:
    """Parse a Markdown story export without contacting a live JIRA instance."""

    source_types = (SourceType.JIRA_MARKDOWN,)

    def accepts(self, source_type: SourceType) -> bool:
        return source_type in self.source_types

    def parse(self, path: Path, source_id: str) -> SourceExtraction:
        content = path.read_text(encoding="utf-8")
        return self.parse_text(content, source_id, path.name)

    def parse_text(
        self,
        content: str,
        source_id: str,
        filename: str = "jira-story.md",
        source_url: str | None = None,
    ) -> SourceExtraction:
        del filename
        story_id = self._extract_story_id(content, source_url)
        warnings: list[str] = []
        if story_id == "UNIDENTIFIED-STORY":
            warnings.append("JIRA Story ID was not found")
        criteria: list[AcceptanceCriterion] = []
        headings = list(
            re.finditer(
                r"^(?P<level>#{2,6})\s+(?P<header>[^\n]+?)\s*$",
                content,
                re.MULTILINE,
            )
        )
        acceptance_depth: int | None = None
        for index, heading in enumerate(headings):
            level = len(heading.group("level"))
            header = heading.group("header").strip()
            if re.match(r"(?i)^acceptance criteria\s*:?$", header):
                acceptance_depth = level
                continue
            criterion_match = re.match(
                r"(?i)^(?P<criterion>AC[-_][A-Z0-9-]+)\b(?:\s*[-:]\s*(?P<title>.*))?$",
                header,
            )
            is_criterion_heading = criterion_match is not None or (
                acceptance_depth is not None
                and level > acceptance_depth
                and bool(re.match(r"(?i)^(?:criterion|scenario|case)\b", header))
            )
            if not is_criterion_heading:
                continue
            next_start = headings[index + 1].start() if index + 1 < len(headings) else len(content)
            body = content[heading.end() : next_start].strip()
            trace = self._traceability_text(body)
            text = self._criterion_text(body)
            if not text:
                continue
            criterion_id = (
                criterion_match.group("criterion")
                if criterion_match
                else f"AC-{story_id}-{len(criteria) + 1:02d}"
            )
            requirement_ids = tuple(sorted(set(re.findall(r"BRD-PAY-\d{3}", f"{trace} {text}"))))
            criteria.append(
                self._criterion(
                    source_id,
                    story_id,
                    criterion_id,
                    text,
                    requirement_ids,
                )
            )
        if not criteria:
            criteria.extend(self._parse_bdd_criteria(content, source_id, story_id))
        if not criteria:
            warnings.append("No Given/When/Then acceptance criteria were found")
        return SourceExtraction(
            source_id=source_id,
            source_type=SourceType.JIRA_MARKDOWN,
            criteria=tuple(criteria),
            warnings=tuple(warnings),
        )

    @staticmethod
    def _extract_story_id(content: str, source_url: str | None) -> str:
        patterns = (
            r"(?i)(?:\*\*)?JIRA\s+Story\s+ID(?:\*\*)?\s*[:#-]\s*([A-Z][A-Z0-9]+-\d+)",
            r"(?im)^\s*(?:story\s+)?(?:id|key)\s*[:#-]\s*([A-Z][A-Z0-9]+-\d+)",
            r"(?im)^#\s*([A-Z][A-Z0-9]+-\d+)\b",
        )
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1).upper()
        if source_url:
            match = re.search(r"/browse/([A-Z][A-Z0-9]+-\d+)", source_url, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        return "UNIDENTIFIED-STORY"

    @staticmethod
    def _traceability_text(body: str) -> str:
        match = re.search(
            r"(?im)^\s*(?:\*\*)?traceability(?:\*\*)?\s*:\s*(?P<value>[^\n]+)",
            body,
        )
        return match.group("value") if match else ""

    @staticmethod
    def _criterion_text(body: str) -> str:
        blocks = re.findall(
            r"```(?:text|gherkin|markdown)?\s*\n?(.*?)```", body, re.IGNORECASE | re.DOTALL
        )
        bdd_blocks = [block for block in blocks if re.search(r"(?i)\b(?:given|when|then)\b", block)]
        if bdd_blocks:
            return " ".join(bdd_blocks[0].split())
        without_trace = re.sub(
            r"(?im)^\s*(?:\*\*)?traceability(?:\*\*)?\s*:\s*[^\n]+\n?",
            "",
            body,
        )
        without_fences = re.sub(
            r"```(?:text|gherkin|markdown)?", "", without_trace, flags=re.IGNORECASE
        )
        without_fences = without_fences.replace("```", "")
        return " ".join(without_fences.split()).strip(" -*")

    @classmethod
    def _parse_bdd_criteria(
        cls, content: str, source_id: str, story_id: str
    ) -> list[AcceptanceCriterion]:
        acceptance_match = re.search(r"(?im)^\s*(?:#{1,6}\s*)?acceptance criteria\s*:?.*$", content)
        body = content[acceptance_match.end() :] if acceptance_match else content
        next_section = re.search(r"(?m)^#{1,6}\s+(?!acceptance criteria\b)", body, re.IGNORECASE)
        if next_section:
            body = body[: next_section.start()]
        blocks = re.findall(
            r"```(?:text|gherkin|markdown)?\s*\n?(.*?)```", body, re.IGNORECASE | re.DOTALL
        )
        candidates = blocks or [body]
        criteria: list[AcceptanceCriterion] = []
        for candidate in candidates:
            starts = list(re.finditer(r"(?im)^\s*(?:[-*]\s+|\d+[.)]\s+)?Given\b", candidate))
            segments = [
                candidate[
                    start.start() : starts[pos + 1].start() if pos + 1 < len(starts) else None
                ]
                for pos, start in enumerate(starts)
            ] or [candidate]
            for segment in segments:
                if not re.search(r"(?i)\b(?:given|when|then)\b", segment):
                    continue
                text = " ".join(segment.split())
                explicit_id = re.search(r"\b(AC[-_][A-Z0-9-]+)\b", segment, re.IGNORECASE)
                criterion_id = (
                    explicit_id.group(1).upper()
                    if explicit_id
                    else f"AC-{story_id}-{len(criteria) + 1:02d}"
                )
                requirement_ids = tuple(sorted(set(re.findall(r"BRD-PAY-\d{3}", segment))))
                criteria.append(
                    cls._criterion(source_id, story_id, criterion_id, text, requirement_ids)
                )
        return criteria

    @staticmethod
    def _criterion(
        source_id: str,
        story_id: str,
        criterion_id: str,
        text: str,
        requirement_ids: tuple[str, ...],
    ) -> AcceptanceCriterion:
        return AcceptanceCriterion(
            criterion_id=criterion_id,
            story_id=story_id,
            text=text,
            requirement_ids=requirement_ids,
            location=SourceLocation(
                source_id=source_id,
                label=f"{criterion_id} / {story_id}",
                section_path=("Acceptance Criteria", criterion_id),
            ),
        )
