# Requirement coverage:
# REQ-002-suite-refinement-002, REQ-002-suite-refinement-003
# REQ-002-suite-refinement-004, REQ-002-suite-refinement-005
from __future__ import annotations

import json
from pathlib import Path

from autoharness.artifacts.models import CampaignSummary
from autoharness.benchmarks.fixtures import FixtureCase
from autoharness.providers.fixture import FixtureProvider
from autoharness.refinement.campaign import (
    SuiteRefinementCampaignRunner,
    validate_campaign_artifacts,
)

OBSERVATION_WITH_HISTORY = """
[GAME] Current Board:
 0 | 1 | 2
Available Moves: '[0]', '[1]', '[2]'
[Player 0] [0]
[GAME] Current Board:
 O | 1 | 2
Available Moves: '[1]', '[2]'
""".strip()


def test_suite_refinement_campaign_runner_converges_and_writes_lineage(
    tmp_path: Path,
) -> None:
    cases = [
        FixtureCase(
            case_id="case-a",
            observation=OBSERVATION_WITH_HISTORY,
            valid_actions=["[1]", "[2]"],
        ),
        FixtureCase(
            case_id="case-b",
            observation=OBSERVATION_WITH_HISTORY,
            valid_actions=["[1]", "[2]"],
        ),
    ]
    patch_provider = FixtureProvider(
        response_text="Parse the final Available Moves block and emit exactly one move."
    )

    result = SuiteRefinementCampaignRunner().run(
        suite_id="toy-dev",
        candidate_path=Path("tests/fixtures/candidates/ttt_first_historical_move.py"),
        cases=cases,
        patch_provider=patch_provider,
        artifact_root=tmp_path,
        retry_limit=1,
        max_iterations=1,
    )

    assert result.status == "converged"
    assert result.stop_reason == "converged"
    assert result.iterations_attempted == 1
    assert Path(result.candidate_lineage_path).exists()
    assert Path(result.campaign_summary_path).exists()
    lines = Path(result.candidate_lineage_path).read_text().strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    second = json.loads(lines[1])
    assert first["case_ids"] == ["case-a", "case-b"]
    assert isinstance(first["ranking_score"], float)
    assert first["selected_case_id"] == "case-a"
    assert first["mutation_family"] == "latest_available_moves"
    assert first["promoted_for_refinement"] is True
    assert isinstance(first["candidate_hash"], str)
    assert second["parent_candidate_hash"] == first["candidate_hash"]
    assert second["stop_reason"] == "converged"


def test_suite_refinement_campaign_runner_stops_on_unsupported_mutation(
    tmp_path: Path,
) -> None:
    candidate_path = tmp_path / "always_illegal.py"
    candidate_path.write_text(
        "\n".join(
            [
                "def propose_action(board: str) -> str:",
                "    del board",
                '    return "[0]"',
                "",
                "def is_legal_action(board: str, action: str) -> bool:",
                "    del board",
                "    return action.startswith('[')",
            ]
        )
    )
    cases = [
        FixtureCase(
            case_id="case-a",
            observation=OBSERVATION_WITH_HISTORY,
            valid_actions=["[1]", "[2]"],
        )
    ]
    patch_provider = FixtureProvider(
        response_text="Parse the final Available Moves block and emit exactly one move."
    )

    result = SuiteRefinementCampaignRunner().run(
        suite_id="toy-dev",
        candidate_path=candidate_path,
        cases=cases,
        patch_provider=patch_provider,
        artifact_root=tmp_path,
        retry_limit=1,
        max_iterations=1,
    )

    assert result.status == "failed"
    assert result.stop_reason == "unsupported_mutation"
    lineage = Path(result.candidate_lineage_path).read_text().strip().splitlines()
    assert len(lineage) == 1
    assert json.loads(lineage[0])["stop_reason"] == "unsupported_mutation"


def test_suite_refinement_campaign_runner_stops_on_no_improvement(
    tmp_path: Path,
) -> None:
    candidate_path = tmp_path / "no_improvement.py"
    candidate_path.write_text(
        "\n".join(
            [
                "import re",
                "",
                "def propose_action(board: str) -> str:",
                '    match = re.search(r"Available Moves:\\s*(.*)", board)',
                "    if match is None:",
                '        return "[0]"',
                '    tokens = re.findall(r"\\[[^\\]]+\\]", match.group(1))',
                "    del tokens",
                '    return "[9]"',
                "",
                "def is_legal_action(board: str, action: str) -> bool:",
                "    del board",
                "    return action.startswith('[')",
            ]
        )
    )
    cases = [
        FixtureCase(
            case_id="case-a",
            observation=OBSERVATION_WITH_HISTORY,
            valid_actions=["[1]", "[2]"],
        )
    ]
    patch_provider = FixtureProvider(
        response_text="Parse the final Available Moves block and emit exactly one move."
    )

    result = SuiteRefinementCampaignRunner().run(
        suite_id="toy-dev",
        candidate_path=candidate_path,
        cases=cases,
        patch_provider=patch_provider,
        artifact_root=tmp_path,
        retry_limit=1,
        max_iterations=2,
    )

    assert result.status == "failed"
    assert result.stop_reason == "no_improvement"
    lines = Path(result.candidate_lineage_path).read_text().strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[-1])["stop_reason"] == "no_improvement"


def test_suite_refinement_campaign_runner_gates_champion_on_holdout_success(
    tmp_path: Path,
) -> None:
    dev_cases = [
        FixtureCase(
            case_id="dev-a",
            observation=OBSERVATION_WITH_HISTORY,
            valid_actions=["[1]", "[2]"],
        )
    ]
    holdout_cases = [
        FixtureCase(
            case_id="holdout-a",
            observation=OBSERVATION_WITH_HISTORY,
            valid_actions=["[1]", "[2]"],
        )
    ]
    patch_provider = FixtureProvider(
        response_text="Parse the final Available Moves block and emit exactly one move."
    )

    result = SuiteRefinementCampaignRunner().run(
        suite_id="toy-dev",
        candidate_path=Path("tests/fixtures/candidates/ttt_first_historical_move.py"),
        cases=dev_cases,
        holdout_cases=holdout_cases,
        minimum_holdout_legal_action_rate=1.0,
        patch_provider=patch_provider,
        artifact_root=tmp_path,
        retry_limit=1,
        max_iterations=1,
    )

    assert result.status == "converged"
    assert result.stop_reason == "converged"
    assert result.holdout_suite_summary is not None
    assert result.holdout_suite_summary.status == "passed"
    summary = CampaignSummary.model_validate_json(Path(result.campaign_summary_path).read_text())
    assert summary.holdout_gate_passed is True
    validate_campaign_artifacts(summary)


def test_suite_refinement_campaign_runner_fails_on_holdout_regression(
    tmp_path: Path,
) -> None:
    dev_cases = [
        FixtureCase(
            case_id="dev-a",
            observation=OBSERVATION_WITH_HISTORY,
            valid_actions=["[1]", "[2]"],
        )
    ]
    holdout_cases = [
        FixtureCase(
            case_id="holdout-a",
            observation=OBSERVATION_WITH_HISTORY,
            valid_actions=["[2]"],
        )
    ]
    patch_provider = FixtureProvider(
        response_text="Parse the final Available Moves block and emit exactly one move."
    )

    result = SuiteRefinementCampaignRunner().run(
        suite_id="toy-dev",
        candidate_path=Path("tests/fixtures/candidates/ttt_first_historical_move.py"),
        cases=dev_cases,
        holdout_cases=holdout_cases,
        patch_provider=patch_provider,
        artifact_root=tmp_path,
        retry_limit=1,
        max_iterations=1,
    )

    assert result.status == "failed"
    assert result.stop_reason == "holdout_regression"
    assert result.holdout_suite_summary is not None
    assert result.holdout_suite_summary.status == "failed"
    summary = CampaignSummary.model_validate_json(Path(result.campaign_summary_path).read_text())
    assert summary.holdout_gate_passed is False


def test_validate_campaign_artifacts_fails_when_holdout_summary_is_missing(
    tmp_path: Path,
) -> None:
    dev_cases = [
        FixtureCase(
            case_id="dev-a",
            observation=OBSERVATION_WITH_HISTORY,
            valid_actions=["[1]", "[2]"],
        )
    ]
    holdout_cases = [
        FixtureCase(
            case_id="holdout-a",
            observation=OBSERVATION_WITH_HISTORY,
            valid_actions=["[1]", "[2]"],
        )
    ]
    patch_provider = FixtureProvider(
        response_text="Parse the final Available Moves block and emit exactly one move."
    )

    result = SuiteRefinementCampaignRunner().run(
        suite_id="toy-dev",
        candidate_path=Path("tests/fixtures/candidates/ttt_first_historical_move.py"),
        cases=dev_cases,
        holdout_cases=holdout_cases,
        patch_provider=patch_provider,
        artifact_root=tmp_path,
        retry_limit=1,
        max_iterations=1,
    )
    summary = CampaignSummary.model_validate_json(Path(result.campaign_summary_path).read_text())
    holdout_path = Path(summary.holdout_suite_summary_path)
    holdout_path.unlink()

    try:
        validate_campaign_artifacts(summary)
    except RuntimeError as exc:
        assert "holdout_suite_summary" in str(exc)
    else:
        raise AssertionError("Expected validate_campaign_artifacts to fail")
