from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from tcg.domain.models import Requirement, ScenarioPlan, TestType
from tcg.domain.ports import SensitiveScanner


@dataclass(frozen=True)
class EvidencePackage:
    context: str
    omitted_items: tuple[str, ...]
    redacted_count: int
    injection_mitigations: int
    token_estimate: int


class ContextAssembler:
    """Assemble minimal, redacted evidence for one scenario plan."""

    def __init__(self, budget: int, blocklist: tuple[str, ...], scanner: SensitiveScanner) -> None:
        self.budget = max(budget, 120)
        self.blocklist = tuple(item.lower() for item in blocklist)
        self.scanner = scanner

    def assemble(self, requirement: Requirement, plan: ScenarioPlan) -> EvidencePackage:
        sections = [
            f"Requirement: {requirement.requirement_id}",
            f"Behavior: {requirement.behavior_statement}",
            f"Business rule: {requirement.business_rule}",
            f"Validation: {requirement.validation}",
            f"Input: {requirement.input_field}",
            f"Dependencies: {', '.join(requirement.dependencies) or 'None stated'}",
            f"Scenario type: {plan.test_type.value}",
            f"Evidence: {', '.join(location.display() for location in plan.source_references)}",
        ]
        omitted: list[str] = []
        mitigations = 0
        redacted_count = 0
        sanitized_sections: list[str] = []
        for section in sections:
            sanitized = section
            for phrase in self.blocklist:
                if phrase in sanitized.lower():
                    sanitized = sanitized.lower().replace(
                        phrase, "[CONTENT_REDACTED_INJECTION_RISK]"
                    )
                    mitigations += 1
            sanitized, count = self.scanner.redact(sanitized)
            redacted_count += count
            sanitized_sections.append(sanitized)
        context = "\n".join(sanitized_sections)
        max_chars = self.budget * 4
        if len(context) > max_chars:
            context = context[:max_chars]
            omitted.append("surrounding evidence beyond configured context budget")
        return EvidencePackage(
            context, tuple(omitted), redacted_count, mitigations, len(context) // 4
        )


class PromptBuilder:
    """Load a versioned prompt and substitute only sanitized evidence."""

    def __init__(self, template_path: Path) -> None:
        self.template_path = template_path

    def build(self, package: EvidencePackage) -> str:
        if not self.template_path.exists():
            raise FileNotFoundError("Prompt template generate_v1.0 is unavailable")
        return self.template_path.read_text(encoding="utf-8").replace("{context}", package.context)


class DeterministicAIProvider:
    """Evidence-grounded local provider used for demos and deterministic tests."""

    def __init__(self, model_name: str = "local-evidence-rules") -> None:
        self.model_name = model_name
        self.logger = logging.getLogger("tcg.ai")

    def generate(
        self, requirement: Requirement, test_type: TestType, context: str
    ) -> dict[str, object]:
        outcome = (
            requirement.expected_behaviour or requirement.validation or requirement.description
        )
        scenario_prefix = {
            TestType.POSITIVE: "Complete a valid",
            TestType.NEGATIVE: "Reject an invalid",
            TestType.BOUNDARY: "Verify the explicit boundary for",
            TestType.VALIDATION: "Validate the rules for",
            TestType.EXCEPTION: "Handle the exception for",
            TestType.INTEGRATION: "Verify dependent-service handling for",
            TestType.END_TO_END: "Execute the end-to-end path for",
        }[test_type]
        expected = self._expected_outcome(requirement, test_type, outcome)
        steps = [
            {
                "step_number": 1,
                "action": f"Prepare the stated inputs for {requirement.requirement_id}.",
                "expected_result": "Inputs are ready for the selected scenario.",
            },
            {
                "step_number": 2,
                "action": (
                    f"Execute the {test_type.value.lower()} transfer behavior described by "
                    f"{requirement.requirement_id}."
                ),
                "expected_result": expected,
            },
            {
                "step_number": 3,
                "action": "Observe the resulting transfer state and customer-facing outcome.",
                "expected_result": expected,
            },
        ]
        return {
            "scenario": f"{scenario_prefix} fund transfer behavior ({requirement.requirement_id})",
            "preconditions": [
                "The test run uses authorized fictional data.",
                "The source evidence for the requirement is available.",
            ],
            "test_data": [
                {
                    "description": requirement.input_field
                    or "Requirement-specific transfer inputs",
                    "value": "Use a sanitized value from the sample Test_Data sheet",
                    "data_type": "symbolic",
                    "masked": True,
                }
            ],
            "test_steps": steps,
            "expected_results": [expected],
            "assumptions": [],
            "open_questions": [],
            "context_length": len(context),
        }

    @staticmethod
    def _expected_outcome(requirement: Requirement, test_type: TestType, outcome: str) -> str:
        if test_type == TestType.POSITIVE:
            return outcome
        if test_type in {TestType.NEGATIVE, TestType.VALIDATION, TestType.BOUNDARY}:
            return (
                "The request is evaluated against the stated rule and is not processed "
                f"when it violates it: {outcome}"
            )
        if test_type == TestType.EXCEPTION:
            return (
                f"The documented exception outcome is surfaced without claiming success: {outcome}"
            )
        if test_type == TestType.INTEGRATION:
            return (
                "The named dependency outcome is handled according to the source behavior: "
                f"{outcome}"
            )
        return outcome


class OpenAICompatibleProvider:
    """Optional provider adapter; disabled unless explicitly selected by configuration."""

    def __init__(self, model_name: str, api_key_env_var: str, endpoint: str) -> None:
        self.model_name = model_name
        self.api_key_env_var = api_key_env_var
        self.endpoint = endpoint.rstrip("/")

    def generate(
        self, requirement: Requirement, test_type: TestType, context: str
    ) -> dict[str, object]:
        api_key = os.environ.get(self.api_key_env_var)
        if not api_key:
            raise RuntimeError("Configured AI provider credentials are unavailable")
        payload = {
            "model": self.model_name,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": context}],
        }
        request = urllib.request.Request(
            f"{self.endpoint}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError("AI provider request failed") from exc
        content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not isinstance(content, str):
            raise RuntimeError("AI provider returned an invalid response")
        result = json.loads(content)
        if not isinstance(result, dict):
            raise RuntimeError("AI provider returned an invalid object")
        return result


class GoogleAIStudioProvider:
    """Call Google AI Studio without exposing or retaining the API key."""

    _standard_key_names = ("GOOGLE_API_KEY", "GEMINI_API_KEY")
    _model_aliases = {"gemma 4:31b": "gemma-4-31b-it"}

    def __init__(
        self,
        model_name: str,
        api_key_env_var: str,
        endpoint: str,
        model_id: str | None = None,
        timeout_seconds: int = 30,
        max_attempts: int = 2,
        max_output_tokens: int = 1024,
    ) -> None:
        self.model_name = model_name
        self.model_id = model_id or self._model_aliases.get(
            model_name.lower(), model_name.lower().replace(":", "-").replace(" ", "-")
        )
        self.api_key_env_var = api_key_env_var
        self.endpoint = endpoint.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max(1, max_attempts)
        self.max_output_tokens = max(128, max_output_tokens)

    def generate(
        self, requirement: Requirement, test_type: TestType, context: str
    ) -> dict[str, object]:
        del requirement, test_type
        api_key = self._api_key()
        url = f"{self.endpoint}/models/{quote(self.model_id, safe='-')}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": context}]}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": self.max_output_tokens,
                "responseMimeType": "application/json",
                "responseSchema": self._response_schema(),
            },
        }
        last_error: RuntimeError | None = None
        for attempt in range(1, self.max_attempts + 1):
            request = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    body = json.loads(response.read().decode("utf-8"))
                content = self._response_text(body)
                result = self._parse_json_content(content)
                if not isinstance(result, dict):
                    raise RuntimeError("Google AI Studio returned an invalid object")
                return result
            except urllib.error.HTTPError as exc:
                last_error = RuntimeError(f"Google AI Studio request failed (HTTP {exc.code})")
                if exc.code not in {408, 429, 500, 502, 503, 504}:
                    raise last_error from exc
            except TimeoutError as exc:
                last_error = RuntimeError(
                    f"Google AI Studio request timed out after {self.timeout_seconds} seconds"
                )
                if attempt == self.max_attempts:
                    raise last_error from exc
            except urllib.error.URLError as exc:
                last_error = RuntimeError("Google AI Studio request failed")
                if attempt == self.max_attempts:
                    raise last_error from exc
            except json.JSONDecodeError as exc:
                last_error = RuntimeError("Google AI Studio returned non-JSON output")
                if attempt == self.max_attempts:
                    raise last_error from exc
            except RuntimeError as exc:
                last_error = exc
                if attempt == self.max_attempts:
                    raise
            if attempt < self.max_attempts:
                time.sleep(min(2 ** (attempt - 1), 2))
        raise last_error or RuntimeError("Google AI Studio request failed")

    @staticmethod
    def _parse_json_content(content: str) -> object:
        candidate = content.strip()
        if candidate.startswith("```"):
            lines = candidate.splitlines()
            opening = lines[0].strip().lower()
            closing = lines[-1].strip() if lines else ""
            if opening in {"```", "```json"} and closing == "```":
                candidate = "\n".join(lines[1:-1]).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            decoder = json.JSONDecoder()
            starts = [
                position for position in (candidate.find("{"), candidate.find("[")) if position >= 0
            ]
            if starts:
                start = min(starts)
                prefix = candidate[:start].strip().lower()
                allowed_prefixes = {
                    "",
                    "json",
                    "json:",
                    "response:",
                    "here is the json:",
                    "here is the response:",
                }
                if prefix in allowed_prefixes:
                    try:
                        value, end = decoder.raw_decode(candidate[start:])
                    except json.JSONDecodeError:
                        pass
                    else:
                        suffix = candidate[start + end :].strip().lower()
                        if suffix in {"", "```", "```json"}:
                            return value
            raise json.JSONDecodeError(
                "Google AI Studio returned non-JSON output", content, 0
            ) from None

    @staticmethod
    def _response_text(body: object) -> str:
        if not isinstance(body, dict):
            raise RuntimeError("Google AI Studio returned an invalid response")
        try:
            content = body["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Google AI Studio returned no usable candidate") from exc
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Google AI Studio returned no usable candidate")
        return content

    @staticmethod
    def _response_schema() -> dict[str, object]:
        return {
            "type": "OBJECT",
            "properties": {
                "scenario": {"type": "STRING"},
                "preconditions": {"type": "ARRAY", "items": {"type": "STRING"}},
                "test_data": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "description": {"type": "STRING"},
                            "value": {"type": "STRING"},
                            "data_type": {"type": "STRING"},
                            "masked": {"type": "BOOLEAN"},
                        },
                        "required": ["description"],
                    },
                },
                "test_steps": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "step_number": {"type": "INTEGER"},
                            "action": {"type": "STRING"},
                            "expected_result": {"type": "STRING"},
                        },
                        "required": ["step_number", "action", "expected_result"],
                    },
                },
                "expected_results": {"type": "ARRAY", "items": {"type": "STRING"}},
                "assumptions": {"type": "ARRAY", "items": {"type": "STRING"}},
                "open_questions": {"type": "ARRAY", "items": {"type": "STRING"}},
            },
            "required": [
                "scenario",
                "preconditions",
                "test_data",
                "test_steps",
                "expected_results",
                "assumptions",
                "open_questions",
            ],
        }

    def _api_key(self) -> str:
        names = (self.api_key_env_var, *self._standard_key_names)
        for name in dict.fromkeys(names):
            value = os.environ.get(name)
            if value and value.strip():
                return value.strip()
        raise RuntimeError(
            "Google AI Studio API key is missing from the backend environment; "
            f"set {self.api_key_env_var} (or GOOGLE_API_KEY/GEMINI_API_KEY)"
        )
