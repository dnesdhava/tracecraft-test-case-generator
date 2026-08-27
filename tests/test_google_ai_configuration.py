from __future__ import annotations

import json
import urllib.error
from pathlib import Path

import pytest

from tcg.config.settings import load_settings
from tcg.domain.models import Priority, Requirement, SourceLocation
from tcg.domain.models import TestType as ScenarioType
from tcg.infrastructure.ai import GoogleAIStudioProvider


def _requirement() -> Requirement:
    return Requirement(
        requirement_id="BRD-PAY-001",
        description="Submit a valid transfer",
        business_process="Fund transfer",
        functional_requirement="Validate and submit the request",
        business_rule="The transfer must be valid",
        input_field="Transfer amount",
        validation="Amount is required",
        expected_behaviour="Show confirmation",
        priority=Priority.HIGH,
        dependencies=("Payment processor",),
        source_id="brd-test",
        location=SourceLocation("brd-test", "Business_Requirements/BRD-PAY-001"),
    )


def test_google_defaults_and_backend_key_reference(monkeypatch, project_root: Path) -> None:
    monkeypatch.delenv("TCG_AI_PROVIDER", raising=False)
    monkeypatch.delenv("TCG_AI_MODEL_NAME", raising=False)
    settings = load_settings(project_root)

    assert settings.ai_provider == "google"
    assert settings.ai_model_name == "Gemma 4:31B"
    assert settings.ai_model_id == "gemma-4-31b-it"
    assert settings.ai_endpoint == "https://generativelanguage.googleapis.com/v1beta"
    assert settings.ai_api_key_env_var == "TCG_AI_API_KEY"
    assert "AIza" not in repr(settings)


def test_google_provider_reads_key_at_call_time_and_uses_header(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def read(self) -> bytes:
            return json.dumps({"candidates": [{"content": {"parts": [{"text": "{}"}]}}]}).encode()

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setenv("TCG_TEST_GOOGLE_KEY", "AIza-fictional-backend-only-key")
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    provider = GoogleAIStudioProvider(
        "Gemma 4:31B",
        "TCG_TEST_GOOGLE_KEY",
        "https://generativelanguage.googleapis.com/v1beta",
    )

    result = provider.generate(_requirement(), ScenarioType.POSITIVE, "sanitized evidence")
    request = captured["request"]
    assert result == {}
    assert request.get_header("X-goog-api-key") == "AIza-fictional-backend-only-key"
    assert request.full_url.endswith("/models/gemma-4-31b-it:generateContent")
    assert "AIza-fictional-backend-only-key" not in repr(provider.__dict__)


def test_google_provider_reports_missing_backend_key_without_secret(monkeypatch) -> None:
    for name in ("TCG_MISSING_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    provider = GoogleAIStudioProvider(
        "Gemma 4:31B",
        "TCG_MISSING_KEY",
        "https://generativelanguage.googleapis.com/v1beta",
    )

    with pytest.raises(RuntimeError, match="TCG_MISSING_KEY") as error:
        provider.generate(_requirement(), ScenarioType.POSITIVE, "sanitized evidence")

    assert "GOOGLE_API_KEY" in str(error.value)
    assert "GEMINI_API_KEY" in str(error.value)


def test_google_provider_payload_requests_structured_draft_schema() -> None:
    schema = GoogleAIStudioProvider._response_schema()

    assert schema["type"] == "OBJECT"
    assert "scenario" in schema["properties"]
    assert "test_steps" in schema["required"]


def test_google_provider_bounds_output_tokens() -> None:
    provider = GoogleAIStudioProvider(
        "Gemma 4:31B",
        "TCG_TEST_GOOGLE_KEY",
        "https://generativelanguage.googleapis.com/v1beta",
        max_output_tokens=64,
    )

    assert provider.max_output_tokens == 128


def test_google_provider_retries_transient_http_failure(monkeypatch) -> None:
    calls = {"count": 0}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def read(self) -> bytes:
            return json.dumps({"candidates": [{"content": {"parts": [{"text": "{}"}]}}]}).encode()

    def fake_urlopen(request, timeout):
        calls["count"] += 1
        if calls["count"] == 1:
            raise urllib.error.HTTPError(request.full_url, 503, "temporary", {}, None)
        return FakeResponse()

    monkeypatch.setenv("TCG_TEST_GOOGLE_KEY", "AIza-fictional-backend-only-key")
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("time.sleep", lambda _: None)
    provider = GoogleAIStudioProvider(
        "Gemma 4:31B",
        "TCG_TEST_GOOGLE_KEY",
        "https://generativelanguage.googleapis.com/v1beta",
        max_attempts=2,
    )

    assert provider.generate(_requirement(), ScenarioType.POSITIVE, "sanitized evidence") == {}
    assert calls["count"] == 2


def test_google_provider_accepts_json_only_markdown_wrapper() -> None:
    content = '```json\n{"scenario": "Valid transfer"}\n```'

    assert GoogleAIStudioProvider._parse_json_content(content) == {"scenario": "Valid transfer"}


def test_google_provider_rejects_prose_around_json() -> None:
    content = 'Here is the result:\n{"scenario": "Valid transfer"}'

    with pytest.raises(json.JSONDecodeError):
        GoogleAIStudioProvider._parse_json_content(content)
