# Requirement coverage: REQ-003-toy-benchmarking-003
# REQ-004-expanded-toy-benchmarking-artifact-policy-003
# REQ-004-expanded-toy-benchmarking-artifact-policy-004
# REQ-004-expanded-toy-benchmarking-artifact-policy-009
from pathlib import Path

from autoharness.benchmarks.fixtures import FixtureBenchmark, FixtureCase
from autoharness.candidates.contracts import (
    load_candidate_module,
    validate_action_verifier_module,
)
from autoharness.config.load import load_manifest
from autoharness.providers.candidate import CandidateModuleProvider
from autoharness.runtime.loop import run_episode
from autoharness.runtime.suites import run_fixture_suite

FIXTURE_DIR = Path("tests/fixtures/candidates")
BASELINE_CANDIDATES = {
    "robust": FIXTURE_DIR / "ttt_robust_latest_move_parser.py",
    "historical": FIXTURE_DIR / "ttt_bad_historical_parser.py",
    "latest": FIXTURE_DIR / "ttt_latest_move_parser.py",
    "fragile": FIXTURE_DIR / "ttt_retry_fragile_formatter.py",
    "negative": FIXTURE_DIR / "ttt_negative_control.py",
}
ALIAS_FAMILY_CASE_IDS = {
    "alias-family-legal-actions",
    "alias-family-valid-moves-history",
}
REPRESENTATIVE_CASES = [
    FixtureCase(
        case_id="plain-unquoted",
        observation="Available Moves: [3], [4]",
        valid_actions=["[3]"],
    ),
    FixtureCase(
        case_id="latest-only-history",
        observation="\n".join(
            [
                "Available Moves: '[0]', '[1]', '[2]'",
                "[Player 0] [0]",
                "Available Moves: '[1]', '[2]'",
            ]
        ),
        valid_actions=["[1]"],
    ),
    FixtureCase(
        case_id="quoted-single-move",
        observation="Available Moves: '[5]'",
        valid_actions=["[5]"],
    ),
    FixtureCase(
        case_id="alias-family-legal-actions",
        observation="Legal Actions: '[12]', '[13]'",
        valid_actions=["[12]"],
    ),
    FixtureCase(
        case_id="alias-family-valid-moves-history",
        observation="\n".join(
            [
                "Valid Moves: [20], [21]",
                "[Player 1] [20]",
                "Valid Moves: [21]",
            ]
        ),
        valid_actions=["[21]"],
    ),
]


def _run_suite(candidate_path: Path, artifact_root: Path):
    return run_fixture_suite(
        suite_id="toy-baseline-separation",
        cases=REPRESENTATIVE_CASES,
        provider_factory=lambda case: CandidateModuleProvider(path=candidate_path),
        retry_limit=0,
        artifact_root=artifact_root,
    )


def _case_statuses(summary):
    return {case.case_id: case.status for case in summary.cases}


def _manifest_cases(manifest_path: Path) -> list[FixtureCase]:
    manifest = load_manifest(manifest_path)
    return [
        FixtureCase(
            case_id=case.case_id,
            observation=case.observation,
            valid_actions=list(case.valid_actions),
            max_steps=case.max_steps,
            script=[step.model_dump(mode="python") for step in case.script],
        )
        for case in manifest.benchmark.cases
    ]


def test_toy_benchmark_baselines_satisfy_candidate_contract() -> None:
    for candidate_path in BASELINE_CANDIDATES.values():
        module = load_candidate_module(candidate_path)
        validate_action_verifier_module(module)


def test_robust_baseline_passes_representative_cases_with_aliases(
    tmp_path: Path,
) -> None:
    summary = _run_suite(BASELINE_CANDIDATES["robust"], tmp_path / "robust")
    statuses = _case_statuses(summary)

    assert summary.total_cases == len(REPRESENTATIVE_CASES)
    assert summary.passed_cases == len(REPRESENTATIVE_CASES)
    assert summary.failed_cases == 0
    assert summary.legal_action_rate == 1.0
    assert all(case.retry_count == 0 for case in summary.cases)
    assert all(statuses[case_id] == "passed" for case_id in ALIAS_FAMILY_CASE_IDS)


def test_robust_baseline_passes_expanded_committed_benchmark_manifests(
    tmp_path: Path,
) -> None:
    dev_summary = run_fixture_suite(
        suite_id="expanded-dev",
        cases=_manifest_cases(Path("manifests/toy_benchmark_dev.yaml")),
        provider_factory=lambda case: CandidateModuleProvider(path=BASELINE_CANDIDATES["robust"]),
        retry_limit=1,
        artifact_root=tmp_path / "robust-dev",
    )
    holdout_summary = run_fixture_suite(
        suite_id="expanded-holdout",
        cases=_manifest_cases(Path("manifests/toy_benchmark_holdout.yaml")),
        provider_factory=lambda case: CandidateModuleProvider(path=BASELINE_CANDIDATES["robust"]),
        retry_limit=1,
        artifact_root=tmp_path / "robust-holdout",
    )

    assert dev_summary.passed_cases == dev_summary.total_cases
    assert holdout_summary.passed_cases == holdout_summary.total_cases
    assert dev_summary.legal_action_rate == 1.0
    assert holdout_summary.legal_action_rate == 1.0
    assert sum(case.retry_count for case in dev_summary.cases) == 0
    assert sum(case.retry_count for case in holdout_summary.cases) == 0


def test_control_baselines_preserve_failure_modes_on_representative_cases(
    tmp_path: Path,
) -> None:
    summaries = {
        label: _run_suite(candidate_path, tmp_path / label)
        for label, candidate_path in BASELINE_CANDIDATES.items()
        if label != "robust"
    }

    latest_statuses = _case_statuses(summaries["latest"])
    assert any(latest_statuses[case_id] == "failed" for case_id in ALIAS_FAMILY_CASE_IDS)

    assert summaries["historical"].failed_cases >= 1

    assert summaries["fragile"].failed_cases >= 1

    assert summaries["negative"].passed_cases == 0
    assert summaries["negative"].legal_action_rate == 0.0


def test_retry_fragile_baseline_exhausts_retries_once_warning_is_added(tmp_path: Path) -> None:
    benchmark_case = FixtureCase(
        case_id="quoted-retry-fragility",
        observation="Available Moves: '[5]'",
        valid_actions=["[5]"],
    )
    result = run_episode(
        benchmark=FixtureBenchmark.from_case(benchmark_case),
        provider=CandidateModuleProvider(path=BASELINE_CANDIDATES["fragile"]),
        retry_limit=1,
        artifact_root=tmp_path,
    )

    assert result.status == "failed"
    assert result.retry_count == 2
    assert result.legal_attempts == 0
    assert result.illegal_attempts == 2
    assert result.final_action == "[retry]"
