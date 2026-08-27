from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from tcg.domain.models import DataClassification


@dataclass(frozen=True)
class Settings:
    project_root: Path
    storage_dir: Path
    audit_log_path: Path
    security_audit_log_path: Path
    max_upload_bytes: int
    ai_provider: str
    ai_model_name: str
    ai_model_id: str
    ai_api_key_env_var: str
    ai_endpoint: str
    ai_timeout_seconds: int
    ai_max_output_tokens: int
    ai_fallback_enabled: bool
    context_budget: int
    duplicate_similarity_threshold: float
    duplicate_policy: str
    validation_rule_version: str
    schema_version: str
    require_approved_export: bool
    redact_source_excerpts: bool
    prompt_injection_blocklist: tuple[str, ...]
    sensitive_patterns: tuple[str, ...]
    language_enforce_english: bool
    log_level: str
    log_format: str
    ai_data_classification: DataClassification = DataClassification.INTERNAL

    @property
    def prompt_template_path(self) -> Path:
        return self.project_root / "config" / "prompt_templates" / "generate_v1.0.txt"


def _root_dir() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_defaults(root: Path) -> dict[str, Any]:
    path = root / "config" / "defaults.yaml"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    return loaded if isinstance(loaded, dict) else {}


def _env(name: str, default: Any) -> Any:
    value = os.environ.get(name)
    return default if value is None or value == "" else value


def _as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def load_settings(project_root: Path | None = None) -> Settings:
    root = (project_root or _root_dir()).resolve()
    load_dotenv(root / ".env", override=False)
    defaults = _load_defaults(root)
    storage = defaults.get("storage", {})
    intake = defaults.get("intake", {})
    ai = defaults.get("ai", {})
    validation = defaults.get("validation", {})
    export = defaults.get("export", {})
    security = defaults.get("security", {})
    language = defaults.get("language", {})
    logging = defaults.get("logging", {})

    storage_dir = Path(str(_env("TCG_STORAGE_BASE_DIR", storage.get("base_dir", "./storage"))))
    if not storage_dir.is_absolute():
        storage_dir = root / storage_dir
    audit_path = Path(
        str(_env("TCG_AUDIT_LOG_PATH", storage.get("audit_log_path", "./storage/audit.jsonl")))
    )
    security_audit_path = Path(
        str(
            _env(
                "TCG_SECURITY_AUDIT_LOG_PATH",
                storage.get("security_audit_log_path", "./storage/security-audit.jsonl"),
            )
        )
    )
    if not audit_path.is_absolute():
        audit_path = root / audit_path
    if not security_audit_path.is_absolute():
        security_audit_path = root / security_audit_path

    return Settings(
        project_root=root,
        storage_dir=storage_dir,
        audit_log_path=audit_path,
        security_audit_log_path=security_audit_path,
        max_upload_bytes=int(
            _env("TCG_MAX_UPLOAD_BYTES", intake.get("max_upload_bytes", 52428800))
        ),
        ai_provider=str(_env("TCG_AI_PROVIDER", ai.get("provider", "google"))),
        ai_model_name=str(_env("TCG_AI_MODEL_NAME", ai.get("model_name", "Gemma 4:31B"))),
        ai_model_id=str(_env("TCG_AI_MODEL_ID", ai.get("model_id", "gemma-4-31b-it"))),
        ai_api_key_env_var=str(
            _env("TCG_AI_API_KEY_ENV_VAR", ai.get("api_key_env_var", "TCG_AI_API_KEY"))
        ),
        ai_endpoint=str(
            _env(
                "TCG_AI_ENDPOINT",
                ai.get("endpoint", "https://generativelanguage.googleapis.com/v1beta"),
            )
        ),
        ai_timeout_seconds=int(_env("TCG_AI_TIMEOUT_SECONDS", ai.get("timeout_seconds", 30))),
        ai_max_output_tokens=int(
            _env("TCG_AI_MAX_OUTPUT_TOKENS", ai.get("max_output_tokens", 1024))
        ),
        ai_fallback_enabled=_as_bool(
            _env("TCG_AI_FALLBACK_ENABLED", ai.get("fallback_enabled", True))
        ),
        context_budget=int(_env("TCG_AI_CONTEXT_BUDGET", ai.get("context_budget", 2000))),
        duplicate_similarity_threshold=float(
            _env(
                "TCG_DUPLICATE_SIMILARITY_THRESHOLD",
                validation.get("duplicate_similarity_threshold", 0.85),
            )
        ),
        duplicate_policy=str(
            _env("TCG_DUPLICATE_POLICY", validation.get("duplicate_policy", "warn"))
        ),
        validation_rule_version=str(
            _env("TCG_VALIDATION_RULE_VERSION", validation.get("rule_version", "1.0"))
        ),
        schema_version=str(_env("TCG_SCHEMA_VERSION", export.get("schema_version", "1.0"))),
        require_approved_export=_as_bool(
            _env("TCG_REQUIRE_APPROVED_EXPORT", export.get("require_approved", False))
        ),
        redact_source_excerpts=_as_bool(
            _env("TCG_REDACT_SOURCE_EXCERPTS", export.get("redact_source_excerpts", True))
        ),
        prompt_injection_blocklist=tuple(
            str(item) for item in security.get("prompt_injection_blocklist", [])
        ),
        sensitive_patterns=tuple(str(item) for item in security.get("sensitive_patterns", [])),
        language_enforce_english=_as_bool(
            _env("TCG_ENFORCE_ENGLISH", language.get("enforce_english", False))
        ),
        log_level=str(_env("TCG_LOG_LEVEL", logging.get("level", "INFO"))),
        log_format=str(_env("TCG_LOG_FORMAT", logging.get("format", "json"))),
        ai_data_classification=DataClassification(
            str(_env("TCG_AI_DATA_CLASSIFICATION", DataClassification.INTERNAL.value))
        ),
    )
