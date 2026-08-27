from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class FileAuditWriter:
    """Write non-sensitive, append-only audit events to JSONL files."""

    def __init__(self, path: Path, security_path: Path) -> None:
        self.path = path
        self.security_path = security_path
        self.logger = logging.getLogger("tcg.audit")

    def record(
        self,
        event_type: str,
        run_id: str,
        target_id: str = "",
        outcome: str = "SUCCESS",
        metadata: dict[str, str] | None = None,
    ) -> None:
        event: dict[str, Any] = {
            "event_id": f"audit-{datetime.now(UTC).timestamp():.6f}",
            "event_type": event_type,
            "run_id": run_id,
            "target_id": target_id,
            "outcome": outcome,
            "metadata": metadata or {},
            "timestamp": datetime.now(UTC).isoformat(),
        }
        try:
            self._append(self.path, event)
            if event_type in {"SECURITY_EVENT", "SENSITIVE_DATA_DETECTED", "ACCESS_DENIED"}:
                self._append(self.security_path, event)
        except OSError:
            self.logger.critical("Audit write failed for event type %s", event_type)

    @staticmethod
    def _append(path: Path, event: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=True) + "\n")
        path.chmod(0o640)
