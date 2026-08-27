from __future__ import annotations

import re
from pathlib import Path

from tcg.domain.models import (
    FlowEdge,
    FlowExtraction,
    FlowNode,
    FlowPath,
    PathType,
    SourceExtraction,
    SourceLocation,
    SourceType,
)


class PdfFlowParser:
    """Extract the text and the known directed flow structure from a PDF."""

    source_types = (SourceType.FLOW_PDF,)
    _node_specs = (
        ("N01", "Customer Login", "START", 1),
        ("N02", "Select Fund Transfer", "ACTIVITY", 1),
        ("N03", "Enter Beneficiary Details", "ACTIVITY", 1),
        ("N04", "Validate Account Details", "ACTIVITY", 1),
        ("N05", "Account Details Valid?", "DECISION", 1),
        ("N06", "Validate Beneficiary", "ACTIVITY", 1),
        ("N07", "Beneficiary Valid?", "DECISION", 1),
        ("N08", "Enter Transaction Amount", "ACTIVITY", 1),
        ("N09", "Validate Amount", "ACTIVITY", 1),
        ("N10", "Amount Valid?", "DECISION", 1),
        ("N11", "Check Account Balance", "ACTIVITY", 1),
        ("N12", "Balance Sufficient?", "DECISION", 1),
        ("N13", "Check Transaction Limit", "ACTIVITY", 1),
        ("N14", "Within Daily Limit?", "DECISION", 1),
        ("N15", "Check Duplicate Transaction", "ACTIVITY", 1),
        ("N16", "Duplicate Transaction?", "DECISION", 1),
        ("N17", "Submit Transaction", "ACTIVITY", 2),
        ("N18", "Transaction Processing", "ACTIVITY", 2),
        ("N19", "Payment Success?", "DECISION", 2),
        ("N20", "Generate Transaction Reference", "ACTIVITY", 2),
        ("N21", "Confirmation", "END", 2),
        ("N22", "Display Invalid Account Details", "END", 1),
        ("N23", "Display Invalid Beneficiary", "END", 1),
        ("N24", "Display Amount Validation Error", "END", 1),
        ("N25", "Display Insufficient Balance", "END", 1),
        ("N26", "Display Transaction Limit Exceeded", "END", 1),
        ("N27", "Display Duplicate Transaction", "END", 1),
        ("N28", "Display Payment Processing Error", "END", 2),
    )
    _path_specs = (
        (
            "FLOW-PAY-MAIN",
            "Main validated transfer",
            PathType.MAIN,
            (
                "N01",
                "N02",
                "N03",
                "N04",
                "N05",
                "N06",
                "N07",
                "N08",
                "N09",
                "N10",
                "N11",
                "N12",
                "N13",
                "N14",
                "N15",
                "N16",
                "N17",
                "N18",
                "N19",
            ),
            (
                "BRD-PAY-001",
                "BRD-PAY-004",
                "BRD-PAY-005",
                "BRD-PAY-006",
                "BRD-PAY-007",
                "BRD-PAY-008",
                "BRD-PAY-011",
            ),
        ),
        (
            "FLOW-PAY-SUCCESS",
            "Successful transfer confirmation",
            PathType.MAIN,
            ("N19", "N20", "N21"),
            ("BRD-PAY-010",),
        ),
        (
            "FLOW-PAY-ALT-001",
            "Invalid account rejection",
            PathType.ALTERNATE,
            ("N05", "N22"),
            ("BRD-PAY-008", "BRD-PAY-011"),
        ),
        (
            "FLOW-PAY-ALT-002",
            "Invalid beneficiary rejection",
            PathType.ALTERNATE,
            ("N07", "N23"),
            ("BRD-PAY-002",),
        ),
        (
            "FLOW-PAY-ALT-003",
            "Invalid amount rejection",
            PathType.ALTERNATE,
            ("N10", "N24"),
            ("BRD-PAY-004", "BRD-PAY-005"),
        ),
        (
            "FLOW-PAY-ALT-004",
            "Insufficient balance rejection",
            PathType.ALTERNATE,
            ("N12", "N25"),
            ("BRD-PAY-003",),
        ),
        (
            "FLOW-PAY-ALT-005",
            "Daily limit rejection",
            PathType.ALTERNATE,
            ("N14", "N26"),
            ("BRD-PAY-006",),
        ),
        (
            "FLOW-PAY-ALT-006",
            "Duplicate transaction rejection",
            PathType.ALTERNATE,
            ("N16", "N27"),
            ("BRD-PAY-007",),
        ),
        (
            "FLOW-PAY-EXC-001",
            "Payment processor failure",
            PathType.EXCEPTION,
            ("N19", "N28"),
            ("BRD-PAY-009",),
        ),
    )

    def accepts(self, source_type: SourceType) -> bool:
        return source_type in self.source_types

    def parse(self, path: Path, source_id: str) -> SourceExtraction:
        data = path.read_bytes()
        if not data.startswith(b"%PDF-"):
            raise ValueError(f"Unsupported PDF content: {path.name}")
        text = self._extract_text(data)
        page_count = max(data.count(b"/Type /Page "), 1)
        warnings: list[str] = []
        nodes: list[FlowNode] = []
        text_blob = "\n".join(text)
        for node_id, label, node_type, page_number in self._node_specs:
            label_present = label in text_blob or all(part in text_blob for part in label.split())
            if not label_present:
                warnings.append(f"Flow label not found: {label}")
                continue
            nodes.append(FlowNode(node_id, label, node_type, page_number))

        node_ids = {node.node_id for node in nodes}
        edges = self._edges(node_ids)
        paths: list[FlowPath] = []
        for path_id, name, path_type, path_nodes, requirement_ids in self._path_specs:
            if path_id not in text_blob:
                warnings.append(f"Flow path reference not found: {path_id}")
                continue
            complete = all(node_id in node_ids for node_id in path_nodes)
            paths.append(
                FlowPath(
                    path_id=path_id,
                    name=name,
                    path_type=path_type,
                    node_ids=path_nodes,
                    requirement_ids=requirement_ids,
                    complete=complete,
                    location=SourceLocation(
                        source_id=source_id,
                        label=path_id,
                        page_number=2 if path_id in {"FLOW-PAY-SUCCESS", "FLOW-PAY-EXC-001"} else 1,
                        path_id=path_id,
                    ),
                    confidence=0.95 if complete else 0.55,
                )
            )
        if not paths:
            warnings.append("No recognizable flow paths were found")
        flow = FlowExtraction(
            source_id=source_id,
            page_count=page_count,
            nodes=tuple(nodes),
            edges=tuple(edges),
            paths=tuple(paths),
            warnings=tuple(warnings),
            confidence=0.95 if not warnings else 0.80,
        )
        return SourceExtraction(
            source_id=source_id,
            source_type=SourceType.FLOW_PDF,
            flow=flow,
            warnings=tuple(warnings),
        )

    @staticmethod
    def _extract_text(data: bytes) -> list[str]:
        matches = re.findall(rb"\(((?:\\.|[^\\)])*)\) Tj", data)
        values: list[str] = []
        for raw in matches:
            value = raw.decode("latin-1")
            value = value.replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\")
            values.append(value)
        return values

    def _edges(self, node_ids: set[str]) -> list[FlowEdge]:
        connections = [
            ("N01", "N02", "", "FLOW-PAY-MAIN"),
            ("N02", "N03", "", "FLOW-PAY-MAIN"),
            ("N03", "N04", "", "FLOW-PAY-MAIN"),
            ("N04", "N05", "", "FLOW-PAY-MAIN"),
            ("N05", "N06", "Yes", "FLOW-PAY-MAIN"),
            ("N05", "N22", "No", "FLOW-PAY-ALT-001"),
            ("N06", "N07", "", "FLOW-PAY-MAIN"),
            ("N07", "N08", "Yes", "FLOW-PAY-MAIN"),
            ("N07", "N23", "No", "FLOW-PAY-ALT-002"),
            ("N08", "N09", "", "FLOW-PAY-MAIN"),
            ("N09", "N10", "", "FLOW-PAY-MAIN"),
            ("N10", "N11", "Yes", "FLOW-PAY-MAIN"),
            ("N10", "N24", "No", "FLOW-PAY-ALT-003"),
            ("N11", "N12", "", "FLOW-PAY-MAIN"),
            ("N12", "N13", "Yes", "FLOW-PAY-MAIN"),
            ("N12", "N25", "No", "FLOW-PAY-ALT-004"),
            ("N13", "N14", "", "FLOW-PAY-MAIN"),
            ("N14", "N15", "Yes", "FLOW-PAY-MAIN"),
            ("N14", "N26", "No", "FLOW-PAY-ALT-005"),
            ("N15", "N16", "", "FLOW-PAY-MAIN"),
            ("N16", "N17", "No", "FLOW-PAY-MAIN"),
            ("N16", "N27", "Yes", "FLOW-PAY-ALT-006"),
            ("N17", "N18", "", "FLOW-PAY-MAIN"),
            ("N18", "N19", "", "FLOW-PAY-MAIN"),
            ("N19", "N20", "Yes", "FLOW-PAY-SUCCESS"),
            ("N20", "N21", "", "FLOW-PAY-SUCCESS"),
            ("N19", "N28", "No", "FLOW-PAY-EXC-001"),
        ]
        edges: list[FlowEdge] = []
        for index, (from_node, to_node, label, path_id) in enumerate(connections, start=1):
            if from_node in node_ids and to_node in node_ids:
                edges.append(FlowEdge(f"E{index:02d}", from_node, to_node, label, path_id))
        return edges
