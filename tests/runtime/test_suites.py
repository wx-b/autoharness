# Requirement coverage: REQ-002-suite-refinement-001
from pathlib import Path

from autoharness.benchmarks.fixtures import FixtureCase
from autoharness.providers.fixture import FixtureProvider
from autoharness.runtime.suites import run_fixture_suite


def test_run_fixture_suite_writes_case_artifacts_and_summary(tmp_path: Path) -> None:
    cases = [
        FixtureCase(
            case_id="case-north",
            observation="Legal Actions: 'north'",
            valid_actions=["north"],
        ),
        FixtureCase(
            case_id="case-east",
            observation="Legal Actions: 'east'",
            valid_actions=["east"],
        ),
    ]
    responses = {
        "case-north": "north",
        "case-east": "east",
    }

    summary = run_fixture_suite(
        suite_id="toy-dev",
        cases=cases,
        provider_factory=lambda case: FixtureProvider(
            response_text=responses[case.case_id],
        ),
        retry_limit=0,
        artifact_root=tmp_path,
    )

    assert summary.status == "passed"
    assert summary.total_cases == 2
    assert summary.passed_cases == 2
    assert summary.failed_cases == 0
    assert summary.legal_action_rate == 1.0
    assert [case.case_id for case in summary.cases] == ["case-north", "case-east"]
    assert (tmp_path / "suite-summary.json").exists()
    assert (tmp_path / "case-north" / "run-summary.json").exists()
    assert (tmp_path / "case-east" / "run-summary.json").exists()


def test_run_fixture_suite_reports_failed_cases_in_aggregate_summary(tmp_path: Path) -> None:
    cases = [
        FixtureCase(
            case_id="case-north",
            observation="Legal Actions: 'north'",
            valid_actions=["north"],
        ),
        FixtureCase(
            case_id="case-east",
            observation="Legal Actions: 'east'",
            valid_actions=["east"],
        ),
    ]
    responses = {
        "case-north": "north",
        "case-east": "west",
    }

    summary = run_fixture_suite(
        suite_id="toy-dev",
        cases=cases,
        provider_factory=lambda case: FixtureProvider(
            response_text=responses[case.case_id],
        ),
        retry_limit=0,
        artifact_root=tmp_path,
    )

    assert summary.status == "failed"
    assert summary.total_cases == 2
    assert summary.passed_cases == 1
    assert summary.failed_cases == 1
    assert summary.legal_action_rate == 0.5
    assert summary.cases[1].case_id == "case-east"
    assert summary.cases[1].status == "failed"
