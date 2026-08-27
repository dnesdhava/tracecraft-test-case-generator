from __future__ import annotations

import json
from pathlib import Path

from tcg.domain.models import RunState, jsonable, run_from_dict


class StorageError(RuntimeError):
    """Raised when a persisted run cannot be loaded or written."""


class FileRunStorage:
    """Persist each run as one atomically replaced JSON document."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_run(self, run: RunState) -> None:
        path = self._run_path(run.run_id)
        if path.exists():
            raise StorageError("A run with this identifier already exists")
        self.save_run(run)

    def load_run(self, run_id: str) -> RunState:
        path = self._run_path(run_id)
        if not path.exists():
            raise StorageError("Generation run was not found")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return run_from_dict(data)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise StorageError("Generation run state is unreadable") from exc

    def save_run(self, run: RunState) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        path = self._run_path(run.run_id)
        temporary = path.with_suffix(".tmp")
        try:
            temporary.write_text(
                json.dumps(jsonable(run), indent=2, ensure_ascii=True), encoding="utf-8"
            )
            temporary.replace(path)
        except OSError as exc:
            raise StorageError("Unable to persist generation run") from exc

    def list_runs(self) -> list[RunState]:
        runs: list[RunState] = []
        for path in sorted(self.base_dir.glob("*.json")):
            try:
                runs.append(run_from_dict(json.loads(path.read_text(encoding="utf-8"))))
            except (OSError, ValueError, KeyError, TypeError):
                continue
        return runs

    def _run_path(self, run_id: str) -> Path:
        safe_id = "".join(
            character for character in run_id if character.isalnum() or character == "-"
        )
        if safe_id != run_id or not safe_id:
            raise StorageError("Invalid run identifier")
        return self.base_dir / f"{safe_id}.json"
