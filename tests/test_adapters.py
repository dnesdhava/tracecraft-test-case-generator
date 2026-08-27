from __future__ import annotations

from pathlib import Path

from tcg.domain.models import SourceType
from tcg.infrastructure.parsers import ExcelBRDParser, JiraMarkdownParser, PdfFlowParser


def test_excel_brd_parser_reads_required_sheets_and_requirements(project_root: Path) -> None:
    result = ExcelBRDParser().parse(project_root / "samples/brd/sample_brd.xlsx", "brd-test")

    assert result.source_type == SourceType.BRD_EXCEL
    assert len(result.requirements) == 11
    assert result.requirements[0].requirement_id == "BRD-PAY-001"
    assert result.requirements[3].location.sheet_name == "Business_Requirements"
    assert result.requirements[3].location.row_number == 5


def test_jira_parser_preserves_criteria_and_brd_links(project_root: Path) -> None:
    result = JiraMarkdownParser().parse(
        project_root / "samples/jira/sample_jira_user_story.md", "jira-test"
    )

    assert len(result.criteria) == 9
    assert result.criteria[0].story_id == "PAY-101"
    assert "BRD-PAY-001" in result.criteria[0].requirement_ids
    assert result.criteria[-1].criterion_id == "AC-PAY-101-09"


def test_jira_parser_supports_pasted_bdd_criteria_and_url_story_id() -> None:
    content = """## Acceptance Criteria

### Criterion 1
Given the customer is authenticated
When the customer submits a valid transfer
Then the system displays confirmation

### Criterion 2
Given the beneficiary is inactive
When the transfer is submitted
Then the system rejects the request
"""

    result = JiraMarkdownParser().parse_text(
        content,
        "jira-pasted",
        source_url="https://jira.example.com/browse/PAY-101",
    )

    assert len(result.criteria) == 2
    assert all(item.story_id == "PAY-101" for item in result.criteria)
    assert result.criteria[0].criterion_id == "AC-PAY-101-01"
    assert not result.warnings


def test_flow_parser_builds_decisions_and_paths(project_root: Path) -> None:
    result = PdfFlowParser().parse(
        project_root / "samples/flow_diagrams/sample_payment_flow.pdf", "flow-test"
    )

    assert result.flow is not None
    assert result.flow.page_count == 2
    assert len(result.flow.nodes) == 28
    assert len(result.flow.edges) == 27
    assert len(result.flow.paths) == 9
    assert any(node.node_type == "DECISION" for node in result.flow.nodes)
    assert {path.path_id for path in result.flow.paths} >= {"FLOW-PAY-MAIN", "FLOW-PAY-EXC-001"}
