from __future__ import annotations


class AccessController:
    """Local-workspace authorization boundary used by every application operation."""

    def authorize(self, principal: str, action: str, project_id: str) -> bool:
        if not principal or not project_id:
            return False
        return action.upper() in {
            "READ",
            "CREATE_RUN",
            "UPLOAD",
            "PROCESS",
            "GENERATE",
            "VALIDATE",
            "EDIT",
            "REVIEW",
            "EXPORT",
            "REPORT",
        }
