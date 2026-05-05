from __future__ import annotations

# Requirement coverage:
# REQ-006-provider-backed-probe-cost-auth-policy-016
from pathlib import Path
from types import SimpleNamespace

from autoharness.providers.base import GenerationConfig
from autoharness.providers.model_preflight import ModelPreflightProvider


class FakeGateway:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def completion(self, messages, **kwargs):  # type: ignore[no-untyped-def]
        self.calls.append({"messages": messages, **kwargs})
        return SimpleNamespace(
            id="resp-1",
            model="local/llama3.1",
            usage=SimpleNamespace(prompt_tokens=12, completion_tokens=3, total_tokens=15),
            choices=[
                SimpleNamespace(message=SimpleNamespace(content='{"move": "[0, 1]"}')),
                SimpleNamespace(message=SimpleNamespace(content='{"move": "[1, 0]"}')),
            ],
        )


def test_model_preflight_provider_uses_configured_group_and_generation_options(
    tmp_path: Path,
) -> None:
    gateway = FakeGateway()

    provider = ModelPreflightProvider(
        group="local_fast",
        config_path=tmp_path / "model-preflight.yaml",
        gateway_factory=lambda config_path: gateway,
    )

    results = provider.generate_candidates(
        "Choose one legal action.",
        GenerationConfig(candidate_count=2, temperature=0.2, top_p=0.9),
    )

    assert [result.text for result in results] == ['{"move": "[0, 1]"}', '{"move": "[1, 0]"}']
    assert [result.provider for result in results] == ["model-preflight", "model-preflight"]
    assert [result.model for result in results] == ["local/llama3.1", "local/llama3.1"]
    assert [result.metadata["candidate_index"] for result in results] == [0, 1]
    assert results[0].metadata["group"] == "local_fast"
    assert results[0].metadata["response_id"] == "resp-1"
    assert results[0].metadata["usage"] == {
        "prompt_tokens": 12,
        "completion_tokens": 3,
        "total_tokens": 15,
    }
    assert gateway.calls == [
        {
            "messages": [{"role": "user", "content": "Choose one legal action."}],
            "group": "local_fast",
            "temperature": 0.2,
            "top_p": 0.9,
            "n": 2,
        }
    ]


def test_model_preflight_provider_falls_back_to_repeated_single_generations() -> None:
    calls = 0

    class SingleChoiceGateway:
        def completion(self, messages, **kwargs):  # type: ignore[no-untyped-def]
            nonlocal calls
            calls += 1
            return SimpleNamespace(
                id=f"resp-{calls}",
                model="openrouter/free-model",
                usage={},
                choices=[
                    SimpleNamespace(message=SimpleNamespace(content=f"move-{calls}")),
                ],
            )

    provider = ModelPreflightProvider(
        group="free_fast",
        gateway_factory=lambda config_path: SingleChoiceGateway(),
    )

    results = provider.generate_candidates(
        "Choose one legal action.",
        GenerationConfig(candidate_count=2),
    )

    assert [result.text for result in results] == ["move-1", "move-2"]
    assert [result.metadata["candidate_index"] for result in results] == [0, 1]
