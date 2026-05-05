# Requirement coverage: REQ-002-suite-refinement-001
# REQ-006-provider-backed-probe-cost-auth-policy-016
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class AuthConfig(BaseModel):
    kind: Literal["none", "api-key", "oauth-adc", "oauth-cli"] = "none"
    env_var: str | None = None
    project: str | None = None
    location: str | None = None


class ProviderConfig(BaseModel):
    kind: Literal[
        "fixture",
        "openrouter",
        "gemini",
        "gemini-cli",
        "model-preflight",
        "candidate",
    ]
    model: str = "fixture-model"
    auth: AuthConfig = Field(default_factory=AuthConfig)
    path: Path | None = None
    use_docker: bool = False
    sandbox_image: str | None = None
    response_text: str | None = None
    sequence: list[str] = Field(default_factory=list)
    candidate_count: int = 1
    temperature: float | None = None
    top_p: float | None = None
    options: dict[str, Any] = Field(default_factory=dict)

    @field_validator("candidate_count")
    @classmethod
    def validate_candidate_count(cls, value: int) -> int:
        if value < 1:
            raise ValueError("candidate_count must be at least 1")
        return value


class FixtureStepConfig(BaseModel):
    observation: str
    valid_actions: list[str] = Field(default_factory=list)


class FixtureCaseConfig(BaseModel):
    case_id: str
    observation: str = "Pick one of: left"
    valid_actions: list[str] = Field(default_factory=lambda: ["left"])
    max_steps: int = 1
    script: list[FixtureStepConfig] = Field(default_factory=list)

    @field_validator("case_id")
    @classmethod
    def validate_case_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("case_id must not be empty")
        return normalized

    @field_validator("max_steps")
    @classmethod
    def validate_max_steps(cls, value: int) -> int:
        if value < 1:
            raise ValueError("max_steps must be at least 1")
        return value


class BenchmarkConfig(BaseModel):
    kind: Literal["fixture", "textarena"]
    env_id: str | None = None
    num_players: int = 1
    seed: int | None = None
    strip_available_moves: bool = False
    observation: str = "Pick one of: left"
    valid_actions: list[str] = Field(default_factory=lambda: ["left"])
    max_steps: int = 1
    script: list[FixtureStepConfig] = Field(default_factory=list)
    cases: list[FixtureCaseConfig] = Field(default_factory=list)
    options: dict[str, Any] = Field(default_factory=dict)

    @field_validator("max_steps")
    @classmethod
    def validate_max_steps(cls, value: int) -> int:
        if value < 1:
            raise ValueError("max_steps must be at least 1")
        return value

    @field_validator("num_players")
    @classmethod
    def validate_num_players(cls, value: int) -> int:
        if value < 1:
            raise ValueError("num_players must be at least 1")
        return value

    @field_validator("cases")
    @classmethod
    def validate_cases(cls, value: list[FixtureCaseConfig]) -> list[FixtureCaseConfig]:
        case_ids = [case.case_id for case in value]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("fixture case_ids must be unique")
        return value


class RuntimeConfig(BaseModel):
    retry_limit: int = 1
    prompt_prefix: str = "Return only the action."

    @field_validator("retry_limit")
    @classmethod
    def validate_retry_limit(cls, value: int) -> int:
        if value < 0:
            raise ValueError("retry_limit must be non-negative")
        return value


class VerificationConfig(BaseModel):
    deterministic_runs: int = 1
    min_legal_action_rate: float | None = None

    @field_validator("deterministic_runs")
    @classmethod
    def validate_deterministic_runs(cls, value: int) -> int:
        if value < 1:
            raise ValueError("deterministic_runs must be at least 1")
        return value

    @field_validator("min_legal_action_rate")
    @classmethod
    def validate_min_legal_action_rate(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if value < 0.0 or value > 1.0:
            raise ValueError("min_legal_action_rate must be between 0 and 1")
        return value


class ArtifactConfig(BaseModel):
    root: Path


class Manifest(BaseModel):
    version: str = "1"
    requirements: list[str] = Field(default_factory=list)
    provider: ProviderConfig
    benchmark: BenchmarkConfig
    runtime: RuntimeConfig
    verification: VerificationConfig = Field(default_factory=VerificationConfig)
    artifacts: ArtifactConfig
