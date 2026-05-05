# Requirement coverage:
# REQ-003-toy-benchmarking-001, REQ-003-toy-benchmarking-002
# REQ-003-toy-benchmarking-004, REQ-003-toy-benchmarking-005
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from autoharness.benchmarking import (
    load_benchmark_matrix,
    run_benchmark_matrix,
    write_benchmark_report,
)
from autoharness.benchmarking.models import (
    BenchmarkSuiteResult,
    BenchmarkSummary,
    CandidateBenchmarkSummary,
)
from autoharness.benchmarking.runner import _candidate_sort_key


def test_load_benchmark_matrix_rejects_duplicate_suite_labels(tmp_path: Path) -> None:
    suite_path = _write_suite_manifest(tmp_path / "suite.yaml")
    candidate_path = _write_candidate(tmp_path / "candidate.py", kind="always_legal")
    matrix_path = _write_matrix(
        tmp_path / "matrix.yaml",
        suites=[
            {"label": "dev", "manifest": suite_path.name},
            {"label": "dev", "manifest": suite_path.name},
        ],
        candidates=[{"label": "alpha", "path": candidate_path.name}],
    )

    with pytest.raises(ValueError, match="Duplicate suite label: dev"):
        load_benchmark_matrix(matrix_path)


def test_load_benchmark_matrix_rejects_duplicate_candidate_labels(tmp_path: Path) -> None:
    suite_path = _write_suite_manifest(tmp_path / "suite.yaml")
    candidate_path = _write_candidate(tmp_path / "candidate.py", kind="always_legal")
    matrix_path = _write_matrix(
        tmp_path / "matrix.yaml",
        suites=[{"label": "dev", "manifest": suite_path.name}],
        candidates=[
            {"label": "alpha", "path": candidate_path.name},
            {"label": "alpha", "path": candidate_path.name},
        ],
    )

    with pytest.raises(ValueError, match="Duplicate candidate label: alpha"):
        load_benchmark_matrix(matrix_path)


def test_load_benchmark_matrix_rejects_unreadable_paths(tmp_path: Path) -> None:
    suite_path = _write_suite_manifest(tmp_path / "suite.yaml")
    matrix_path = _write_matrix(
        tmp_path / "matrix.yaml",
        suites=[{"label": "dev", "manifest": suite_path.name}],
        candidates=[{"label": "alpha", "path": "missing_candidate.py"}],
    )

    with pytest.raises(ValueError, match="Candidate path is not readable"):
        load_benchmark_matrix(matrix_path)


def test_load_benchmark_matrix_rejects_non_fixture_suite_manifests(tmp_path: Path) -> None:
    suite_path = _write_suite_manifest(
        tmp_path / "textarena.yaml",
        benchmark_kind="textarena",
    )
    candidate_path = _write_candidate(tmp_path / "candidate.py", kind="always_legal")
    matrix_path = _write_matrix(
        tmp_path / "matrix.yaml",
        suites=[{"label": "dev", "manifest": suite_path.name}],
        candidates=[{"label": "alpha", "path": candidate_path.name}],
    )

    with pytest.raises(ValueError, match="Suite manifest must define a fixture suite"):
        load_benchmark_matrix(matrix_path)


def test_run_benchmark_matrix_aggregates_suite_results(tmp_path: Path) -> None:
    suite_one_path = _write_suite_manifest(
        tmp_path / "suite-one.yaml",
        suite_id="suite-one",
        case_ids=["north-a", "north-b"],
    )
    suite_two_path = _write_suite_manifest(
        tmp_path / "suite-two.yaml",
        suite_id="suite-two",
        case_ids=["east-a"],
    )
    clean_candidate = _write_candidate(tmp_path / "clean.py", kind="always_legal")
    retrying_candidate = _write_candidate(tmp_path / "retrying.py", kind="retry_then_legal")
    failing_candidate = _write_candidate(tmp_path / "failing.py", kind="always_illegal")
    matrix_path = _write_matrix(
        tmp_path / "matrix.yaml",
        suites=[
            {"label": "dev", "manifest": suite_one_path.name},
            {"label": "holdout", "manifest": suite_two_path.name},
        ],
        candidates=[
            {"label": "clean", "path": clean_candidate.name},
            {"label": "retrying", "path": retrying_candidate.name},
            {"label": "failing", "path": failing_candidate.name},
        ],
    )

    summary = run_benchmark_matrix(load_benchmark_matrix(matrix_path))

    assert [candidate.candidate_label for candidate in summary.candidates] == [
        "clean",
        "retrying",
        "failing",
    ]
    assert [candidate.rank for candidate in summary.candidates] == [1, 2, 3]

    clean_summary = summary.candidates[0]
    assert clean_summary.passed_suites == 2
    assert clean_summary.failed_suites == 0
    assert clean_summary.legal_action_rate == 1.0
    assert clean_summary.total_reward == 3.0
    assert clean_summary.retry_count == 0

    retrying_summary = summary.candidates[1]
    assert retrying_summary.passed_suites == 2
    assert retrying_summary.legal_action_rate == 0.5
    assert retrying_summary.total_reward == 3.0
    assert retrying_summary.retry_count == 3

    failing_summary = summary.candidates[2]
    assert failing_summary.passed_suites == 0
    assert failing_summary.failed_suites == 2
    assert failing_summary.legal_action_rate == 0.0
    assert failing_summary.total_reward == 0.0
    assert failing_summary.retry_count == 6

    suite_result = clean_summary.suite_results[0]
    assert suite_result.suite_label == "dev"
    assert Path(suite_result.artifact_root, "suite-summary.json").exists()


def test_rank_candidates_uses_reward_retry_and_label_tiebreakers() -> None:
    ranked = sorted(
        [
            _candidate_summary("bravo", legal_action_rate=0.5, total_reward=10.0, retry_count=2),
            _candidate_summary("charlie", legal_action_rate=0.5, total_reward=8.0, retry_count=0),
            _candidate_summary("delta", legal_action_rate=0.5, total_reward=10.0, retry_count=3),
            _candidate_summary("alpha", legal_action_rate=0.5, total_reward=10.0, retry_count=2),
            _candidate_summary("omega", legal_action_rate=0.75, total_reward=1.0, retry_count=99),
        ],
        key=_candidate_sort_key,
    )
    for index, candidate in enumerate(ranked, start=1):
        candidate.rank = index

    assert [candidate.candidate_label for candidate in ranked] == [
        "omega",
        "alpha",
        "bravo",
        "delta",
        "charlie",
    ]
    assert [candidate.rank for candidate in ranked] == [1, 2, 3, 4, 5]


def test_write_benchmark_report_writes_json_and_markdown(tmp_path: Path) -> None:
    artifact_root = tmp_path / "benchmark-artifacts"
    summary = BenchmarkSummary(
        matrix_path=str(tmp_path / "matrix.yaml"),
        artifact_root=str(artifact_root),
        primary_metric="legal_action_rate",
        tie_breakers=["total_reward", "retry_count"],
        candidates=[
            CandidateBenchmarkSummary(
                candidate_label="alpha",
                candidate_path=str(tmp_path / "alpha.py"),
                artifact_root=str(artifact_root / "alpha"),
                passed_suites=1,
                failed_suites=0,
                legal_attempts=3,
                illegal_attempts=0,
                legal_action_rate=1.0,
                total_reward=3.0,
                retry_count=0,
                rank=1,
                suite_results=[
                    BenchmarkSuiteResult(
                        suite_label="dev",
                        manifest_path=str(tmp_path / "suite.yaml"),
                        artifact_root=str(artifact_root / "alpha" / "dev"),
                        summary_path=str(artifact_root / "alpha" / "dev" / "suite-summary.json"),
                        status="passed",
                        total_cases=1,
                        passed_cases=1,
                        failed_cases=0,
                        retry_count=0,
                        legal_action_rate=1.0,
                        total_reward=3.0,
                    )
                ],
            )
        ],
    )

    summary_path, leaderboard_path = write_benchmark_report(summary)

    assert summary_path == artifact_root / "benchmark-summary.json"
    assert leaderboard_path == artifact_root / "leaderboard.md"
    summary_text = summary_path.read_text()
    leaderboard_text = leaderboard_path.read_text()
    assert '"candidate_label": "alpha"' in summary_text
    assert '"suite_label": "dev"' in summary_text
    assert str(artifact_root) in summary_text
    assert "# Benchmark Leaderboard" in leaderboard_text
    assert "| 1 | alpha | 1.000 | 3.000 | 0 | 1 | 0 |" in leaderboard_text
    assert str(artifact_root) in leaderboard_text


def _candidate_summary(
    label: str,
    *,
    legal_action_rate: float,
    total_reward: float,
    retry_count: int,
) -> CandidateBenchmarkSummary:
    return CandidateBenchmarkSummary(
        candidate_label=label,
        candidate_path=f"/tmp/{label}.py",
        artifact_root=f"/tmp/{label}",
        passed_suites=0,
        failed_suites=0,
        legal_attempts=0,
        illegal_attempts=0,
        legal_action_rate=legal_action_rate,
        total_reward=total_reward,
        retry_count=retry_count,
        suite_results=[],
    )


def _write_matrix(
    path: Path,
    *,
    suites: list[dict[str, str]],
    candidates: list[dict[str, str]],
) -> Path:
    payload = {
        "version": "1",
        "requirements": ["REQ-003-toy-benchmarking-001"],
        "artifacts": {"root": "benchmark-artifacts"},
        "ranking": {},
        "suites": suites,
        "candidates": candidates,
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False))
    return path


def _write_suite_manifest(
    path: Path,
    *,
    suite_id: str = "dev-suite",
    case_ids: list[str] | None = None,
    benchmark_kind: str = "fixture",
) -> Path:
    payload = {
        "version": "1",
        "requirements": ["REQ-003-toy-benchmarking-001"],
        "provider": {"kind": "fixture"},
        "benchmark": {
            "kind": benchmark_kind,
            "cases": [
                {
                    "case_id": case_id,
                    "observation": f"Case {case_id}\\nAvailable Moves: '[north]'",
                    "valid_actions": ["[north]"],
                }
                for case_id in (case_ids or ["case-a"])
            ],
        },
        "runtime": {
            "retry_limit": 1,
            "prompt_prefix": f"Suite {suite_id}",
        },
        "artifacts": {"root": f"./artifacts/{suite_id}"},
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False))
    return path


def _write_candidate(path: Path, *, kind: str) -> Path:
    candidate_source = {
        "always_legal": """
            import re

            def propose_action(board: str) -> str:
                matches = re.findall(r"Available Moves:\\s*(.*)", board)
                tokens = re.findall(r"\\[[^\\]]+\\]", matches[-1]) if matches else []
                return tokens[0] if tokens else "[missing]"

            def is_legal_action(board: str, action: str) -> bool:
                return action in board
        """,
        "retry_then_legal": """
            import re

            def propose_action(board: str) -> str:
                if "Previous action" not in board:
                    return "[illegal]"
                matches = re.findall(r"Available Moves:\\s*(.*)", board)
                tokens = re.findall(r"\\[[^\\]]+\\]", matches[-1]) if matches else []
                return tokens[0] if tokens else "[illegal]"

            def is_legal_action(board: str, action: str) -> bool:
                return action in board
        """,
        "always_illegal": """
            def propose_action(board: str) -> str:
                return "[illegal]"

            def is_legal_action(board: str, action: str) -> bool:
                return action in board
        """,
    }[kind]
    path.write_text(textwrap.dedent(candidate_source).strip() + "\n")
    return path
