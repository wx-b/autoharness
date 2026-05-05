# Requirement coverage:
# REQ-003-toy-benchmarking-002, REQ-003-toy-benchmarking-005
from __future__ import annotations

from pathlib import Path

from autoharness.artifacts.store import ArtifactStore
from autoharness.benchmarks.fixtures import FixtureCase, coerce_fixture_case
from autoharness.config.load import load_manifest
from autoharness.config.models import Manifest
from autoharness.providers.candidate import CandidateModuleProvider
from autoharness.runtime.suites import run_fixture_suite

from .models import (
    BenchmarkCandidateConfig,
    BenchmarkMatrix,
    BenchmarkSuiteResult,
    BenchmarkSummary,
    CandidateBenchmarkSummary,
)


def run_benchmark_matrix(matrix: BenchmarkMatrix) -> BenchmarkSummary:
    candidate_summaries = [
        _run_candidate(matrix=matrix, candidate=candidate) for candidate in matrix.candidates
    ]
    ranked_candidates = sorted(candidate_summaries, key=_candidate_sort_key)
    for index, candidate in enumerate(ranked_candidates, start=1):
        candidate.rank = index
    return BenchmarkSummary(
        matrix_path=str(matrix.path),
        artifact_root=str(matrix.artifacts.root),
        primary_metric=matrix.ranking.primary_metric,
        tie_breakers=list(matrix.ranking.tie_breakers),
        candidates=ranked_candidates,
    )


def write_benchmark_report(summary: BenchmarkSummary) -> tuple[Path, Path]:
    store = ArtifactStore(Path(summary.artifact_root))
    summary_path = store.write_benchmark_summary(summary)
    summary.summary_path = str(summary_path)
    leaderboard_path = store.write_benchmark_leaderboard(_render_leaderboard(summary))
    summary.leaderboard_path = str(leaderboard_path)
    store.write_benchmark_summary(summary)
    return summary_path, leaderboard_path


def _run_candidate(
    *,
    matrix: BenchmarkMatrix,
    candidate: BenchmarkCandidateConfig,
) -> CandidateBenchmarkSummary:
    suite_results: list[BenchmarkSuiteResult] = []
    passed_suites = 0
    failed_suites = 0
    retry_count = 0
    legal_attempts = 0
    illegal_attempts = 0
    total_reward = 0.0
    candidate_root = matrix.artifacts.root / candidate.label

    for suite in matrix.suites:
        manifest = load_manifest(suite.manifest)
        suite_root = candidate_root / suite.label

        def provider_factory(
            case: FixtureCase,
            path: Path = candidate.path,
        ) -> CandidateModuleProvider:
            return _build_provider(path, case)

        suite_summary = run_fixture_suite(
            suite_id=suite.label,
            cases=_load_fixture_cases(manifest),
            provider_factory=provider_factory,
            retry_limit=manifest.runtime.retry_limit,
            artifact_root=suite_root,
            prompt_prefix=manifest.runtime.prompt_prefix,
        )
        suite_retry_count = sum(case.retry_count for case in suite_summary.cases)
        passed_suites += int(suite_summary.status == "passed")
        failed_suites += int(suite_summary.status == "failed")
        retry_count += suite_retry_count
        legal_attempts += suite_summary.legal_attempts
        illegal_attempts += suite_summary.illegal_attempts
        total_reward += suite_summary.total_reward
        suite_results.append(
            BenchmarkSuiteResult(
                suite_label=suite.label,
                manifest_path=str(suite.manifest),
                artifact_root=str(suite_root),
                summary_path=str(suite_summary.summary_path),
                status=suite_summary.status,
                total_cases=suite_summary.total_cases,
                passed_cases=suite_summary.passed_cases,
                failed_cases=suite_summary.failed_cases,
                retry_count=suite_retry_count,
                legal_action_rate=suite_summary.legal_action_rate,
                total_reward=suite_summary.total_reward,
            )
        )

    total_attempts = legal_attempts + illegal_attempts
    return CandidateBenchmarkSummary(
        candidate_label=candidate.label,
        candidate_path=str(candidate.path),
        artifact_root=str(candidate_root),
        passed_suites=passed_suites,
        failed_suites=failed_suites,
        retry_count=retry_count,
        legal_attempts=legal_attempts,
        illegal_attempts=illegal_attempts,
        legal_action_rate=(legal_attempts / total_attempts if total_attempts else 0.0),
        total_reward=total_reward,
        suite_results=suite_results,
    )


def _build_provider(candidate_path: Path, case: FixtureCase) -> CandidateModuleProvider:
    del case
    return CandidateModuleProvider(path=candidate_path)


def _load_fixture_cases(manifest: Manifest) -> list[FixtureCase]:
    benchmark = manifest.benchmark
    if benchmark.kind != "fixture" or not benchmark.cases:
        raise ValueError("benchmark matrix only supports fixture suite manifests with cases")
    return [coerce_fixture_case(case.model_dump(mode="python")) for case in benchmark.cases]


def _candidate_sort_key(candidate: CandidateBenchmarkSummary) -> tuple[float, float, int, str]:
    return (
        -candidate.legal_action_rate,
        -candidate.total_reward,
        candidate.retry_count,
        candidate.candidate_label,
    )


def _render_leaderboard(summary: BenchmarkSummary) -> str:
    suite_labels = sorted(
        {
            suite_result.suite_label
            for candidate in summary.candidates
            for suite_result in candidate.suite_results
        }
    )
    lines = [
        "# Benchmark Leaderboard",
        "",
        f"- Matrix: `{summary.matrix_path}`",
        f"- Artifact root: `{summary.artifact_root}`",
        (
            "- Ranking: `legal_action_rate desc, total_reward desc, "
            "retry_count asc, candidate_label asc`"
        ),
        (
            f"- Suites: {', '.join(f'`{label}`' for label in suite_labels)}"
            if suite_labels
            else "- Suites: none"
        ),
        "",
        (
            "| Rank | Candidate | Legal Action Rate | Total Reward | "
            "Retry Count | Passed Suites | Failed Suites |"
        ),
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for candidate in summary.candidates:
        lines.append(
            "| "
            f"{candidate.rank} | "
            f"{candidate.candidate_label} | "
            f"{candidate.legal_action_rate:.3f} | "
            f"{candidate.total_reward:.3f} | "
            f"{candidate.retry_count} | "
            f"{candidate.passed_suites} | "
            f"{candidate.failed_suites} |"
        )
    lines.append("")
    for candidate in summary.candidates:
        lines.extend(
            [
                f"## Rank {candidate.rank}: {candidate.candidate_label}",
                "",
                f"- Candidate path: `{candidate.candidate_path}`",
                f"- Artifact root: `{candidate.artifact_root}`",
                (
                    "- Aggregate metrics: "
                    f"legal_action_rate={candidate.legal_action_rate:.3f}, "
                    f"total_reward={candidate.total_reward:.3f}, "
                    f"retry_count={candidate.retry_count}, "
                    f"passed_suites={candidate.passed_suites}, "
                    f"failed_suites={candidate.failed_suites}"
                ),
                "",
                (
                    "| Suite | Status | Cases | Passed | Failed | Legal Action Rate | "
                    "Total Reward | Retry Count | Artifact Root |"
                ),
                "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for suite_result in candidate.suite_results:
            lines.append(
                "| "
                f"{suite_result.suite_label} | "
                f"{suite_result.status} | "
                f"{suite_result.total_cases} | "
                f"{suite_result.passed_cases} | "
                f"{suite_result.failed_cases} | "
                f"{suite_result.legal_action_rate:.3f} | "
                f"{suite_result.total_reward:.3f} | "
                f"{suite_result.retry_count} | "
                f"`{suite_result.artifact_root}` |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
