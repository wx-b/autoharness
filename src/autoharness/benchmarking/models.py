# Requirement coverage:
# REQ-003-toy-benchmarking-001, REQ-003-toy-benchmarking-002
# REQ-003-toy-benchmarking-004, REQ-003-toy-benchmarking-005
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

PrimaryMetric = Literal["legal_action_rate"]
TieBreakerMetric = Literal["total_reward", "retry_count"]


def _default_tie_breakers() -> list[TieBreakerMetric]:
    return ["total_reward", "retry_count"]


class BenchmarkSuiteConfig(BaseModel):
    label: str
    manifest: Path

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("suite label must not be empty")
        return normalized


class BenchmarkCandidateConfig(BaseModel):
    label: str
    path: Path

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("candidate label must not be empty")
        return normalized


class BenchmarkRankingConfig(BaseModel):
    primary_metric: PrimaryMetric = "legal_action_rate"
    tie_breakers: list[TieBreakerMetric] = Field(default_factory=_default_tie_breakers)


class BenchmarkArtifactConfig(BaseModel):
    root: Path


class BenchmarkMatrix(BaseModel):
    version: str = "1"
    requirements: list[str] = Field(default_factory=list)
    path: Path
    suites: list[BenchmarkSuiteConfig]
    candidates: list[BenchmarkCandidateConfig]
    ranking: BenchmarkRankingConfig = Field(default_factory=BenchmarkRankingConfig)
    artifacts: BenchmarkArtifactConfig

    @field_validator("suites")
    @classmethod
    def validate_suites(cls, value: list[BenchmarkSuiteConfig]) -> list[BenchmarkSuiteConfig]:
        if not value:
            raise ValueError("benchmark matrix must contain at least one suite")
        labels = [suite.label for suite in value]
        if len(labels) != len(set(labels)):
            raise ValueError("duplicate suite labels are not allowed")
        return value

    @field_validator("candidates")
    @classmethod
    def validate_candidates(
        cls, value: list[BenchmarkCandidateConfig]
    ) -> list[BenchmarkCandidateConfig]:
        if not value:
            raise ValueError("benchmark matrix must contain at least one candidate")
        labels = [candidate.label for candidate in value]
        if len(labels) != len(set(labels)):
            raise ValueError("duplicate candidate labels are not allowed")
        return value


class BenchmarkSuiteResult(BaseModel):
    suite_label: str
    manifest_path: str
    artifact_root: str
    summary_path: str
    status: Literal["passed", "failed"]
    total_cases: int
    passed_cases: int
    failed_cases: int
    retry_count: int
    legal_action_rate: float
    total_reward: float


class CandidateBenchmarkSummary(BaseModel):
    candidate_label: str
    candidate_path: str
    artifact_root: str
    passed_suites: int
    failed_suites: int
    retry_count: int
    legal_attempts: int
    illegal_attempts: int
    legal_action_rate: float
    total_reward: float
    rank: int | None = None
    suite_results: list[BenchmarkSuiteResult] = Field(default_factory=list)


class BenchmarkSummary(BaseModel):
    matrix_path: str
    artifact_root: str
    primary_metric: PrimaryMetric
    tie_breakers: list[TieBreakerMetric] = Field(default_factory=list)
    candidates: list[CandidateBenchmarkSummary] = Field(default_factory=list)
    summary_path: str | None = None
    leaderboard_path: str | None = None


__all__ = [
    "BenchmarkArtifactConfig",
    "BenchmarkCandidateConfig",
    "BenchmarkMatrix",
    "BenchmarkRankingConfig",
    "BenchmarkSuiteConfig",
    "BenchmarkSuiteResult",
    "BenchmarkSummary",
    "CandidateBenchmarkSummary",
]
