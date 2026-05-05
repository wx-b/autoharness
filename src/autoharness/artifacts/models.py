# Requirement coverage:
# REQ-002-suite-refinement-001, REQ-002-suite-refinement-005
# REQ-003-toy-benchmarking-002, REQ-003-toy-benchmarking-005
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

FailureType = Literal[
    "format_error",
    "illegal_not_in_set",
    "illegal_state_conflict",
    "sandbox_error",
    "timeout",
    "exception",
    "repeated_invalid",
    "env_contract_mismatch",
]


class StepRecord(BaseModel):
    step_index: int
    attempt_index: int
    observation: str
    action: str
    legal: bool
    provider: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunSummary(BaseModel):
    run_id: str
    status: Literal["passed", "failed"]
    steps: int
    retry_count: int
    provider: str
    benchmark: str
    legal_attempts: int = 0
    illegal_attempts: int = 0
    legal_action_rate: float = 0.0
    total_reward: float = 0.0
    summary_path: str | None = None
    trace_path: str | None = None


class FailureBundle(BaseModel):
    run_id: str
    reason: Literal["illegal-action-exhausted"]
    observation: str
    attempts: list[str]
    current_legal_actions: list[str] = Field(default_factory=list)
    failure_type: FailureType | None = None
    env_feedback: dict[str, Any] = Field(default_factory=dict)
    prior_attempts_summary: list[dict[str, object]] = Field(default_factory=list)


class CriticSummary(BaseModel):
    run_id: str
    failure_type: FailureType
    root_cause: str
    current_legal_actions: list[str] = Field(default_factory=list)
    attempts: list[str] = Field(default_factory=list)
    recommended_change: str


class VerificationRunSummary(BaseModel):
    run_index: int
    run_id: str
    status: Literal["passed", "failed"]
    legal_action_rate: float
    total_reward: float
    retry_count: int
    steps: int
    final_action: str | None = None
    artifact_root: str
    determinism_signature: list[object]


class VerificationSummary(BaseModel):
    manifest_path: str
    deterministic_runs: int
    deterministic: bool
    min_legal_action_rate: float | None = None
    min_observed_legal_action_rate: float
    runs: list[VerificationRunSummary] = Field(default_factory=list)


class ProviderProbePreflightReport(BaseModel):
    manifest_path: str
    artifact_root: str
    provider: str
    model: str
    auth_kind: str
    auth_ready: bool
    codex_oauth_supported: bool = False
    messages: list[str] = Field(default_factory=list)


class ProviderProbeBudgetReport(BaseModel):
    max_spend_usd: float
    estimated_spend_usd: float = 0.0
    actual_spend_usd: float = 0.0
    status: Literal["planned", "complete", "partial", "blocked"] = "planned"
    usage_metadata_present: bool = False
    messages: list[str] = Field(default_factory=list)


class ProviderProbeSummary(BaseModel):
    status: Literal["dry-run", "passed", "failed", "blocked"]
    dry_run: bool
    provider: str
    model: str
    auth_kind: str
    artifact_root: str
    max_spend_usd: float
    actual_spend_usd: float = 0.0
    usage: dict[str, object] = Field(default_factory=dict)
    usage_metadata_status: Literal["not_applicable", "complete", "partial"] = (
        "not_applicable"
    )
    run_summary_path: str | None = None
    preflight_report_path: str | None = None
    budget_report_path: str | None = None
    messages: list[str] = Field(default_factory=list)


class SearchTraceRecord(BaseModel):
    iteration: int
    node_id: str
    parent_id: str | None = None
    candidate_path: str
    candidate_hash: str
    status: Literal["passed", "failed"]
    legal_actions: int
    illegal_actions: int
    legal_action_rate: float
    total_reward: float
    selected_for_refinement: bool = False
    patch_plan_summary: str | None = None


class RefinementSummary(BaseModel):
    status: Literal["converged", "failed"]
    iterations_attempted: int
    initial_candidate_path: str
    final_candidate_path: str
    final_run_id: str
    failure_type: FailureType | None = None
    patch_plan_summary: str | None = None
    search_trace_path: str | None = None


class SuiteCaseResult(BaseModel):
    case_id: str
    run_id: str
    status: Literal["passed", "failed"]
    artifact_root: str
    retry_count: int
    steps: int
    final_action: str | None = None
    legal_attempts: int = 0
    illegal_attempts: int = 0
    legal_action_rate: float = 0.0
    total_reward: float = 0.0


class SuiteSummary(BaseModel):
    suite_id: str
    status: Literal["passed", "failed"]
    total_cases: int
    passed_cases: int
    failed_cases: int
    legal_attempts: int = 0
    illegal_attempts: int = 0
    legal_action_rate: float = 0.0
    total_reward: float = 0.0
    cases: list[SuiteCaseResult] = Field(default_factory=list)
    summary_path: str | None = None


CampaignStopReason = Literal[
    "converged",
    "unsupported_mutation",
    "no_improvement",
    "budget_exhausted",
    "holdout_regression",
    "missing_artifacts",
]


class CandidateLineageRecord(BaseModel):
    iteration: int
    candidate_path: str
    candidate_hash: str
    parent_candidate_hash: str | None = None
    suite_artifact_root: str
    suite_summary_path: str | None = None
    status: Literal["passed", "failed"]
    ranking_score: float
    case_ids: list[str] = Field(default_factory=list)
    failed_case_ids: list[str] = Field(default_factory=list)
    selected_case_id: str | None = None
    mutation_family: str | None = None
    promoted_for_refinement: bool = False
    stop_reason: CampaignStopReason | None = None
    legal_action_rate: float = 0.0
    total_reward: float = 0.0


class CampaignSummary(BaseModel):
    status: Literal["converged", "failed"]
    stop_reason: CampaignStopReason
    iterations_attempted: int
    initial_candidate_path: str
    final_candidate_path: str
    final_candidate_hash: str
    candidate_lineage_path: str | None = None
    final_suite_summary_path: str | None = None
    holdout_suite_summary_path: str | None = None
    holdout_gate_passed: bool | None = None


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
    primary_metric: Literal["legal_action_rate"]
    tie_breakers: list[Literal["total_reward", "retry_count"]] = Field(default_factory=list)
    candidates: list[CandidateBenchmarkSummary] = Field(default_factory=list)
    summary_path: str | None = None
    leaderboard_path: str | None = None
