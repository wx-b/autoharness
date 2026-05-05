from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field, field_validator


class GenerationConfig(BaseModel):
    candidate_count: int = 1
    temperature: float | None = None
    top_p: float | None = None
    response_schema: dict[str, object] | None = None

    @field_validator("candidate_count")
    @classmethod
    def validate_candidate_count(cls, value: int) -> int:
        if value < 1:
            raise ValueError("candidate_count must be at least 1")
        return value


class ProviderResult(BaseModel):
    text: str
    provider: str
    model: str
    latency_ms: float | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class Provider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> ProviderResult:
        raise NotImplementedError

    def generate_candidates(
        self, prompt: str, generation_config: GenerationConfig | None = None
    ) -> list[ProviderResult]:
        candidate_count = generation_config.candidate_count if generation_config is not None else 1
        return [self.generate(prompt) for _ in range(candidate_count)]
