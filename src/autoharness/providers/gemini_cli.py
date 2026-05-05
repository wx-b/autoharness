# Requirement coverage:
# REQ-006-provider-backed-probe-cost-auth-policy-006
# REQ-006-provider-backed-probe-cost-auth-policy-007
# REQ-006-provider-backed-probe-cost-auth-policy-011
from __future__ import annotations

import subprocess
import time
from collections.abc import Callable

from .base import GenerationConfig, Provider, ProviderResult

GeminiCliRunner = Callable[
    [list[str], str | None, float | None],
    subprocess.CompletedProcess[str],
]


class GeminiCliProvider(Provider):
    def __init__(
        self,
        *,
        model: str,
        command: str = "gemini",
        timeout_seconds: float | None = 120,
        runner: GeminiCliRunner | None = None,
    ) -> None:
        self.model = model
        self.command = command
        self.timeout_seconds = timeout_seconds
        self._runner = runner or self._run_command

    def generate(self, prompt: str) -> ProviderResult:
        return self.generate_candidates(prompt)[0]

    def generate_candidates(
        self, prompt: str, generation_config: GenerationConfig | None = None
    ) -> list[ProviderResult]:
        candidate_count = generation_config.candidate_count if generation_config else 1
        return [
            self._generate_one(prompt=prompt, candidate_index=index)
            for index in range(candidate_count)
        ]

    def _generate_one(self, *, prompt: str, candidate_index: int) -> ProviderResult:
        command = [
            self.command,
            "--model",
            self.model,
            "--prompt",
            prompt,
            "--output-format",
            "text",
            "--approval-mode",
            "plan",
        ]
        started = time.perf_counter()
        completed = self._runner(command, None, self.timeout_seconds)
        elapsed_ms = (time.perf_counter() - started) * 1000
        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            raise RuntimeError(f"Gemini CLI provider failed: {stderr or completed.returncode}")
        return ProviderResult(
            text=completed.stdout.strip(),
            provider="gemini-cli",
            model=self.model,
            latency_ms=elapsed_ms,
            metadata={
                "auth_kind": "oauth-cli",
                "candidate_index": candidate_index,
                "command": self.command,
            },
        )

    def _run_command(
        self,
        command: list[str],
        input_text: str | None,
        timeout_seconds: float | None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            input=input_text,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
