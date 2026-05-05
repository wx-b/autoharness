from __future__ import annotations

from collections import deque

from .base import Provider, ProviderResult


class FixtureProvider(Provider):
    def __init__(
        self,
        *,
        response_text: str | None = None,
        sequence: list[str] | None = None,
        model: str = "fixture-model",
    ) -> None:
        values = sequence or ([response_text] if response_text is not None else None) or ["left"]
        self._responses = deque(values)
        self._fallback = values[-1]
        self._model = model

    def generate(self, prompt: str) -> ProviderResult:
        del prompt
        text = self._responses.popleft() if self._responses else self._fallback
        return ProviderResult(text=text, provider="fixture", model=self._model, latency_ms=0.0)
