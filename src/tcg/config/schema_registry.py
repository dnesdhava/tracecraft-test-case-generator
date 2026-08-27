from __future__ import annotations

from typing import Any


class ConfigurationError(ValueError):
    """Raised when a requested project configuration or schema is unavailable."""


class SchemaRegistry:
    """Own the versioned machine-readable contract for generated test cases."""

    _schema_version = "1.0"
    _csv_columns = [
        "test_case_id",
        "test_case_number",
        "schema_version",
        "requirement_id",
        "jira_story_id",
        "scenario",
        "preconditions",
        "test_data",
        "test_steps",
        "expected_results",
        "priority",
        "test_type",
        "source_references",
        "review_status",
        "validation_status",
        "assumptions",
        "open_questions",
        "generation_run_id",
        "generated_at",
    ]

    @classmethod
    def current_version(cls) -> str:
        return cls._schema_version

    @classmethod
    def is_known_version(cls, version: str) -> bool:
        return version == cls._schema_version

    @classmethod
    def get_csv_columns(cls, version: str) -> list[str]:
        cls._require(version)
        return list(cls._csv_columns)

    @classmethod
    def get_schema(cls, version: str) -> dict[str, Any]:
        cls._require(version)
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "tcg-test-case-schema-v1.0",
            "type": "object",
            "required": [
                "test_case_id",
                "test_case_number",
                "schema_version",
                "requirement_id",
                "scenario",
                "preconditions",
                "test_data",
                "test_steps",
                "expected_results",
                "priority",
                "test_type",
                "source_references",
                "review_status",
                "validation_status",
                "generation_metadata",
            ],
            "properties": {
                "test_case_id": {"type": "string", "minLength": 1},
                "test_case_number": {
                    "type": "string",
                    "pattern": "^TC-\\d{3,}$",
                },
                "schema_version": {"const": "1.0"},
                "requirement_id": {"type": "string", "minLength": 1},
                "jira_story_id": {"type": ["string", "null"]},
                "scenario": {"type": "string", "minLength": 10},
                "preconditions": {"type": "array", "items": {"type": "string"}},
                "test_data": {"type": "array", "items": {"type": "object"}},
                "test_steps": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": ["step_number", "action", "expected_result"],
                        "properties": {
                            "step_number": {"type": "integer", "minimum": 1},
                            "action": {"type": "string", "minLength": 5},
                            "expected_result": {"type": "string"},
                        },
                    },
                },
                "expected_results": {"type": "array", "minItems": 1, "items": {"type": "string"}},
                "priority": {"enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]},
                "test_type": {
                    "enum": [
                        "POSITIVE",
                        "NEGATIVE",
                        "BOUNDARY",
                        "VALIDATION",
                        "EXCEPTION",
                        "INTEGRATION",
                        "END_TO_END",
                    ]
                },
                "source_references": {"type": "array", "minItems": 1, "items": {"type": "object"}},
                "review_status": {
                    "enum": ["DRAFT", "NEEDS_REVIEW", "NEEDS_CLARIFICATION", "REJECTED", "APPROVED"]
                },
                "validation_status": {"enum": ["PASSED", "WARNING", "FAILED", "BLOCKED"]},
                "generation_metadata": {"type": "object"},
            },
        }

    @classmethod
    def _require(cls, version: str) -> None:
        if not cls.is_known_version(version):
            raise ConfigurationError(f"Unknown schema version: {version}")
