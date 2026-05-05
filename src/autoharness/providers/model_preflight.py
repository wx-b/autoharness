# Requirement coverage:
# REQ-006-provider-backed-probe-cost-auth-policy-006
# REQ-006-provider-backed-probe-cost-auth-policy-007
# REQ-006-provider-backed-probe-cost-auth-policy-016
from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from importlib import import_module
from pathlib import Path
from typing import Any

from .base import GenerationConfig, Provider, ProviderResult

ModelPreflightGatewayFactory = Callable[[Path | None], Any]


class ModelPreflightProvider(Provider):
    """AutoHarness provider backed by the published model-preflight package."""

    def __init__(
        self,
        *,
        group: str,
        config_path: Path | None = None,
        gateway_factory: ModelPreflightGatewayFactory | None = None,
    ) -> None:
        self.group = group
        self.config_path = config_path
        self._gateway_factory = gateway_factory or _default_gateway_factory

    def generate(self, prompt: str) -> ProviderResult:
        return self.generate_candidates(prompt)[0]

    def generate_candidates(
        self, prompt: str, generation_config: GenerationConfig | None = None
    ) -> list[ProviderResult]:
        candidate_count = generation_config.candidate_count if generation_config else 1
        gateway = self._gateway_factory(self.config_path)
        response = self._completion(
            gateway=gateway,
            prompt=prompt,
            generation_config=generation_config,
            candidate_count=candidate_count,
        )
        results = self._response_to_results(response)
        if len(results) >= candidate_count:
            return _renumber_candidates(results[:candidate_count])
        if candidate_count == 1:
            return results
        repeated_results = results
        for _ in range(candidate_count - len(results)):
            response = self._completion(
                gateway=gateway,
                prompt=prompt,
                generation_config=generation_config,
                candidate_count=1,
            )
            repeated_results.extend(self._response_to_results(response))
        return _renumber_candidates(repeated_results[:candidate_count])

    def _completion(
        self,
        *,
        gateway: Any,
        prompt: str,
        generation_config: GenerationConfig | None,
        candidate_count: int,
    ) -> Any:
        kwargs: dict[str, object] = {"group": self.group, "n": candidate_count}
        if generation_config is not None:
            if generation_config.temperature is not None:
                kwargs["temperature"] = generation_config.temperature
            if generation_config.top_p is not None:
                kwargs["top_p"] = generation_config.top_p
        return gateway.completion(
            [{"role": "user", "content": prompt}],
            **kwargs,
        )

    def _response_to_results(self, response: Any) -> list[ProviderResult]:
        choices = getattr(response, "choices", None)
        if not isinstance(choices, list):
            choices = []
        model = getattr(response, "model", None)
        model_name = model if isinstance(model, str) and model else self.group
        response_id = getattr(response, "id", None)
        usage = _usage_to_dict(getattr(response, "usage", None))
        results: list[ProviderResult] = []
        for index, choice in enumerate(choices):
            text = _choice_text(choice)
            metadata: dict[str, object] = {
                "candidate_index": index,
                "group": self.group,
            }
            if isinstance(response_id, str):
                metadata["response_id"] = response_id
            if usage:
                metadata["usage"] = usage
            parsed = _parse_json_text(text)
            if parsed is not None:
                metadata["parsed_response"] = parsed
            results.append(
                ProviderResult(
                    text=text,
                    provider="model-preflight",
                    model=model_name,
                    metadata=metadata,
                )
            )
        if results:
            return results
        return [
            ProviderResult(
                text="",
                provider="model-preflight",
                model=model_name,
                metadata={"candidate_index": 0, "group": self.group},
            )
        ]


def _default_gateway_factory(config_path: Path | None) -> Any:
    try:
        config_module = import_module("model_preflight.config")
        router_module = import_module("model_preflight.router")
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "model-preflight is not installed; rerun with the preflight extra"
        ) from exc
    return router_module.ModelGateway(config_module.load_config(config_path))


def _renumber_candidates(results: list[ProviderResult]) -> list[ProviderResult]:
    renumbered: list[ProviderResult] = []
    for index, result in enumerate(results):
        metadata = {**result.metadata, "candidate_index": index}
        renumbered.append(result.model_copy(update={"metadata": metadata}))
    return renumbered


def _choice_text(choice: Any) -> str:
    message = getattr(choice, "message", None)
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(choice, Mapping):
        raw_message = choice.get("message")
        if isinstance(raw_message, Mapping):
            raw_content = raw_message.get("content")
            if isinstance(raw_content, str):
                return raw_content
    return ""


def _usage_to_dict(usage: object) -> dict[str, object]:
    if usage is None:
        return {}
    if isinstance(usage, Mapping):
        return {str(key): value for key, value in usage.items()}
    result: dict[str, object] = {}
    for name in (
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "prompt_token_count",
        "candidates_token_count",
        "total_token_count",
    ):
        value = getattr(usage, name, None)
        if isinstance(value, (int, float, str)):
            result[name] = value
    return result


def _parse_json_text(text: str) -> dict[str, object] | None:
    stripped = text.strip()
    if not stripped.startswith("{"):
        return None
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict):
        return payload
    return None
