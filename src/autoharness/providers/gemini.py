from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping
from importlib import import_module
from typing import Any

from .auth import read_api_key, read_google_project
from .base import GenerationConfig, Provider, ProviderResult


class GeminiProvider(Provider):
    def __init__(
        self,
        *,
        model: str,
        auth_kind: str = "oauth-adc",
        env_var: str = "GEMINI_API_KEY",
        project: str | None = None,
        location: str | None = None,
        client_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.model = model
        self.auth_kind = auth_kind
        self.env_var = env_var
        self.project = project or read_google_project()
        self.location = location
        self._client_factory = client_factory

    def _build_client(self) -> Any:
        if self._client_factory is not None:
            return self._client_factory()
        try:
            genai = import_module("google.genai")
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "google-genai is not installed; add the providers extra to use GeminiProvider"
            ) from exc

        if self.auth_kind == "api-key":
            return genai.Client(api_key=read_api_key(self.env_var))

        kwargs: dict[str, object] = {"vertexai": True}
        if self.project:
            kwargs["project"] = self.project
        if self.location:
            kwargs["location"] = self.location
        return genai.Client(**kwargs)

    def generate(self, prompt: str) -> ProviderResult:
        return self.generate_candidates(prompt)[0]

    def generate_candidates(
        self, prompt: str, generation_config: GenerationConfig | None = None
    ) -> list[ProviderResult]:
        client = self._build_client()
        started = time.perf_counter()
        config = self._build_generation_config(generation_config)
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config or None,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        usage = self._usage_to_dict(getattr(response, "usage_metadata", None))
        response_id = getattr(response, "response_id", None)
        candidates = getattr(response, "candidates", None)
        if isinstance(candidates, list) and candidates:
            return [
                self._candidate_to_result(
                    candidate=candidate,
                    elapsed_ms=elapsed_ms,
                    response_id=response_id,
                    usage=usage,
                    candidate_index=index,
                )
                for index, candidate in enumerate(candidates)
            ]
        text = self._extract_text(response)
        return [
            ProviderResult(
                text=text,
                provider="gemini",
                model=self.model,
                latency_ms=elapsed_ms,
                metadata=self._build_metadata(
                    text=text,
                    response_id=response_id,
                    usage=usage,
                    candidate_index=0,
                ),
            )
        ]

    def _build_generation_config(
        self, generation_config: GenerationConfig | None
    ) -> dict[str, object]:
        if generation_config is None:
            return {}
        config: dict[str, object] = {"candidate_count": generation_config.candidate_count}
        if generation_config.temperature is not None:
            config["temperature"] = generation_config.temperature
        if generation_config.top_p is not None:
            config["top_p"] = generation_config.top_p
        if generation_config.response_schema is not None:
            config["response_mime_type"] = "application/json"
            config["response_json_schema"] = generation_config.response_schema
        return config

    def _candidate_to_result(
        self,
        *,
        candidate: Any,
        elapsed_ms: float,
        response_id: object,
        usage: dict[str, object],
        candidate_index: int,
    ) -> ProviderResult:
        text = self._extract_text(candidate)
        return ProviderResult(
            text=text,
            provider="gemini",
            model=self.model,
            latency_ms=elapsed_ms,
            metadata=self._build_metadata(
                text=text,
                response_id=response_id,
                usage=usage,
                candidate_index=candidate_index,
            ),
        )

    def _build_metadata(
        self,
        *,
        text: str,
        response_id: object,
        usage: dict[str, object],
        candidate_index: int,
    ) -> dict[str, object]:
        metadata: dict[str, object] = {"candidate_index": candidate_index}
        if isinstance(response_id, str):
            metadata["response_id"] = response_id
        if usage:
            metadata["usage"] = usage
        parsed = self._parse_json_text(text)
        if parsed is not None:
            metadata["parsed_response"] = parsed
        return metadata

    def _extract_text(self, payload: object) -> str:
        text = getattr(payload, "text", None)
        if isinstance(text, str):
            return text
        content = getattr(payload, "content", None)
        parts = getattr(content, "parts", None)
        if isinstance(parts, list):
            fragments = [
                part.text for part in parts if isinstance(getattr(part, "text", None), str)
            ]
            if fragments:
                return "".join(fragments)
        if isinstance(payload, Mapping):
            raw_text = payload.get("text")
            if isinstance(raw_text, str):
                return raw_text
        return ""

    def _parse_json_text(self, text: str) -> dict[str, object] | None:
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

    def _usage_to_dict(self, usage_metadata: object) -> dict[str, object]:
        if usage_metadata is None:
            return {}
        result: dict[str, object] = {}
        for field_name in (
            "prompt_token_count",
            "candidates_token_count",
            "total_token_count",
        ):
            value = getattr(usage_metadata, field_name, None)
            if isinstance(value, (int, float, str)):
                result[field_name] = value
        return result
