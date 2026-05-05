# Requirement coverage: REQ-002-suite-refinement-001, REQ-002-suite-refinement-005
from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Literal, cast

from autoharness.artifacts.models import SuiteCaseResult, SuiteSummary
from autoharness.artifacts.store import ArtifactStore
from autoharness.benchmarks.fixtures import (
    FixtureBenchmark,
    FixtureCase,
    coerce_fixture_case,
)
from autoharness.providers.base import Provider
from autoharness.runtime.loop import run_episode


def run_fixture_suite(
    *,
    suite_id: str,
    cases: Sequence[FixtureCase | dict[str, object]],
    provider_factory: Callable[[FixtureCase], Provider],
    retry_limit: int,
    artifact_root: Path,
    prompt_prefix: str = "Return only the action.",
    candidate_count: int = 1,
    temperature: float | None = None,
    top_p: float | None = None,
) -> SuiteSummary:
    store = ArtifactStore(artifact_root)
    coerced_cases = [coerce_fixture_case(case) for case in cases]
    case_results: list[SuiteCaseResult] = []
    legal_attempts = 0
    illegal_attempts = 0
    total_reward = 0.0

    for case in coerced_cases:
        case_root = artifact_root / case.case_id
        benchmark = FixtureBenchmark.from_case(case)
        provider = provider_factory(case)
        result = run_episode(
            benchmark=benchmark,
            provider=provider,
            retry_limit=retry_limit,
            artifact_root=case_root,
            prompt_prefix=prompt_prefix,
            candidate_count=candidate_count,
            temperature=temperature,
            top_p=top_p,
        )
        legal_attempts += result.legal_attempts
        illegal_attempts += result.illegal_attempts
        total_reward += result.total_reward
        case_results.append(
            SuiteCaseResult(
                case_id=case.case_id,
                run_id=result.run_id,
                status=cast(Literal["passed", "failed"], result.status),
                artifact_root=str(case_root),
                retry_count=result.retry_count,
                steps=result.steps,
                final_action=result.final_action,
                legal_attempts=result.legal_attempts,
                illegal_attempts=result.illegal_attempts,
                legal_action_rate=result.legal_action_rate,
                total_reward=result.total_reward,
            )
        )

    total_attempts = legal_attempts + illegal_attempts
    passed_cases = sum(1 for case in case_results if case.status == "passed")
    suite_summary = SuiteSummary(
        suite_id=suite_id,
        status="passed" if passed_cases == len(case_results) else "failed",
        total_cases=len(case_results),
        passed_cases=passed_cases,
        failed_cases=len(case_results) - passed_cases,
        legal_attempts=legal_attempts,
        illegal_attempts=illegal_attempts,
        legal_action_rate=(legal_attempts / total_attempts if total_attempts else 0.0),
        total_reward=total_reward,
        cases=case_results,
    )
    summary_path = store.write_suite_summary(suite_summary)
    suite_summary.summary_path = str(summary_path)
    store.write_suite_summary(suite_summary)
    return suite_summary
