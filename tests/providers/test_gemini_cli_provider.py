# Requirement coverage:
# REQ-006-provider-backed-probe-cost-auth-policy-006
# REQ-006-provider-backed-probe-cost-auth-policy-007
# REQ-006-provider-backed-probe-cost-auth-policy-011
from __future__ import annotations

import subprocess

from autoharness.providers.base import GenerationConfig
from autoharness.providers.gemini_cli import GeminiCliProvider


def test_gemini_cli_provider_uses_headless_cli_prompt() -> None:
    calls: list[tuple[list[str], str | None, float | None]] = []

    def fake_runner(
        command: list[str],
        input_text: str | None,
        timeout_seconds: float | None,
    ) -> subprocess.CompletedProcess[str]:
        calls.append((command, input_text, timeout_seconds))
        return subprocess.CompletedProcess(command, 0, stdout="[A1]\n", stderr="")

    provider = GeminiCliProvider(
        model="gemini-2.5-flash",
        command="gemini",
        timeout_seconds=12,
        runner=fake_runner,
    )

    result = provider.generate("Choose one legal action.")

    assert result.text == "[A1]"
    assert result.provider == "gemini-cli"
    assert result.model == "gemini-2.5-flash"
    assert result.metadata["auth_kind"] == "oauth-cli"
    assert calls == [
        (
            [
                "gemini",
                "--model",
                "gemini-2.5-flash",
                "--prompt",
                "Choose one legal action.",
                "--output-format",
                "text",
                "--approval-mode",
                "plan",
            ],
            None,
            12,
        )
    ]


def test_gemini_cli_provider_repeats_for_candidate_count() -> None:
    index = 0

    def fake_runner(
        command: list[str],
        input_text: str | None,
        timeout_seconds: float | None,
    ) -> subprocess.CompletedProcess[str]:
        nonlocal index
        index += 1
        return subprocess.CompletedProcess(command, 0, stdout=f"move-{index}", stderr="")

    provider = GeminiCliProvider(
        model="gemini-2.5-flash",
        runner=fake_runner,
    )

    results = provider.generate_candidates(
        "Choose one legal action.",
        GenerationConfig(candidate_count=2),
    )

    assert [result.text for result in results] == ["move-1", "move-2"]
    assert [result.metadata["candidate_index"] for result in results] == [0, 1]
