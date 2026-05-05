from __future__ import annotations

import json
import time
from urllib import request

from .auth import read_api_key
from .base import GenerationConfig, Provider, ProviderResult


class OpenRouterProvider(Provider):
    def __init__(
        self,
        *,
        model: str,
        env_var: str = "OPENROUTER_API_KEY",
        api_base: str = "https://openrouter.ai/api/v1",
    ) -> None:
        self.model = model
        self.env_var = env_var
        self.api_base = api_base.rstrip("/")

    def generate(self, prompt: str) -> ProviderResult:
        return self.generate_candidates(prompt)[0]

    def generate_candidates(
        self, prompt: str, generation_config: GenerationConfig | None = None
    ) -> list[ProviderResult]:
        api_key = read_api_key(self.env_var)
        payload_data: dict[str, object] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if generation_config is not None:
            payload_data["n"] = generation_config.candidate_count
            if generation_config.temperature is not None:
                payload_data["temperature"] = generation_config.temperature
            if generation_config.top_p is not None:
                payload_data["top_p"] = generation_config.top_p
        payload = json.dumps(payload_data).encode("utf-8")
        req = request.Request(
            f"{self.api_base}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        started = time.perf_counter()
        with request.urlopen(req) as response:  # noqa: S310
            body = json.loads(response.read().decode("utf-8"))
        elapsed_ms = (time.perf_counter() - started) * 1000
        results: list[ProviderResult] = []
        for index, choice in enumerate(body["choices"]):
            text = choice["message"]["content"]
            results.append(
                ProviderResult(
                    text=text,
                    provider="openrouter",
                    model=self.model,
                    latency_ms=elapsed_ms,
                    metadata={
                        "response_id": body.get("id"),
                        "candidate_index": index,
                    },
                )
            )
        return results
