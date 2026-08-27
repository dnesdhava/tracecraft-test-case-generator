from __future__ import annotations

import re
from dataclasses import fields, is_dataclass
from enum import Enum


class SensitiveDataScanner:
    """Find secret-like values without returning the values that triggered a match."""

    _patterns = {
        "api_key": re.compile(r"(?:sk-[A-Za-z0-9_-]{12,}|ghp_[A-Za-z0-9_-]{12,})"),
        "bearer_token": re.compile(r"Bearer\s+[A-Za-z0-9._-]{12,}", re.IGNORECASE),
        "jwt": re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}"),
        "password_assignment": re.compile(
            r"(?:password|passwd|secret)\s*[:=]\s*\S+", re.IGNORECASE
        ),
        "card_number": re.compile(r"(?<![A-Za-z0-9])(?:\d[ -]?){13,19}(?![A-Za-z0-9])"),
    }

    def __init__(self, additional_patterns: tuple[str, ...] = ()) -> None:
        self._additional = tuple(re.compile(pattern) for pattern in additional_patterns)

    def scan(self, value: object) -> list[str]:
        findings: list[str] = []
        self._walk(value, "root", findings)
        return findings

    def redact(self, text: str) -> tuple[str, int]:
        total = 0
        result = text
        for name, pattern in self._patterns.items():
            result, count = pattern.subn("[REDACTED]", result)
            if name == "card_number":
                total += count
            else:
                total += count
        for pattern in self._additional:
            result, count = pattern.subn("[REDACTED]", result)
            total += count
        return result, total

    def _walk(self, value: object, path: str, findings: list[str]) -> None:
        if isinstance(value, str):
            for name, pattern in self._patterns.items():
                match = pattern.search(value)
                if match and (name != "card_number" or self._passes_luhn(match.group(0))):
                    findings.append(f"{path}:{name}")
            if any(pattern.search(value) for pattern in self._additional):
                findings.append(f"{path}:configured_pattern")
            return
        if isinstance(value, Enum):
            return
        if is_dataclass(value):
            for item in fields(value):
                self._walk(getattr(value, item.name), f"{path}.{item.name}", findings)
            return
        if isinstance(value, dict):
            for key, item in value.items():
                self._walk(item, f"{path}.{key}", findings)
            return
        if isinstance(value, (list, tuple, set)):
            for index, item in enumerate(value):
                self._walk(item, f"{path}[{index}]", findings)

    @staticmethod
    def _passes_luhn(value: str) -> bool:
        digits = re.sub(r"\D", "", value)
        if not 13 <= len(digits) <= 19:
            return False
        total = 0
        parity = len(digits) % 2
        for index, digit in enumerate(digits):
            number = int(digit)
            if index % 2 == parity:
                number *= 2
                if number > 9:
                    number -= 9
            total += number
        return total % 10 == 0
