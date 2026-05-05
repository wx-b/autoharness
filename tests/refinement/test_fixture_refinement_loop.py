# Requirement coverage: REQ-001-bootstrap-002
from pathlib import Path

from autoharness.benchmarks.fixtures import FixtureBenchmark
from autoharness.providers.fixture import FixtureProvider
from autoharness.refinement.loop import FixtureRefinementRunner

OBSERVATION_WITH_HISTORY = """
[GAME] Current Board:
 0 | 1 | 2
Available Moves: '[0]', '[1]', '[2]'
[Player 0] [0]
[GAME] Current Board:
 O | 1 | 2
Available Moves: '[1]', '[2]'
""".strip()


def test_fixture_refinement_runner_converges_on_single_case(tmp_path: Path) -> None:
    benchmark = FixtureBenchmark(
        observation=OBSERVATION_WITH_HISTORY,
        valid_actions=["[1]", "[2]"],
        max_steps=1,
    )
    patch_provider = FixtureProvider(
        response_text="Parse the final Available Moves block and emit exactly one move."
    )

    result = FixtureRefinementRunner().run(
        candidate_path=Path("tests/fixtures/candidates/ttt_first_historical_move.py"),
        benchmark=benchmark,
        patch_provider=patch_provider,
        artifact_root=tmp_path,
        retry_limit=1,
        max_iterations=1,
    )

    assert result.status == "converged"
    assert result.iterations_attempted == 1
    assert result.final_episode.status == "passed"
    assert Path(result.final_candidate_path).exists()
    assert "matches = re.findall" in Path(result.final_candidate_path).read_text()
    assert (tmp_path / "iteration-00" / "failure-bundle.json").exists()
    assert (tmp_path / "iteration-01" / "run-summary.json").exists()


def test_fixture_refinement_runner_writes_search_trace_and_summary(tmp_path: Path) -> None:
    benchmark = FixtureBenchmark(
        observation=OBSERVATION_WITH_HISTORY,
        valid_actions=["[1]", "[2]"],
        max_steps=1,
    )
    patch_provider = FixtureProvider(
        response_text="Parse the final Available Moves block and emit exactly one move."
    )

    result = FixtureRefinementRunner().run(
        candidate_path=Path("tests/fixtures/candidates/ttt_first_historical_move.py"),
        benchmark=benchmark,
        patch_provider=patch_provider,
        artifact_root=tmp_path,
        retry_limit=1,
        max_iterations=1,
    )

    assert result.status == "converged"
    trace_path = tmp_path / "search-trace.jsonl"
    summary_path = tmp_path / "refinement-summary.json"
    assert trace_path.exists()
    assert summary_path.exists()
    trace_lines = trace_path.read_text().strip().splitlines()
    assert len(trace_lines) == 2
    summary_text = summary_path.read_text()
    assert '"status": "converged"' in summary_text
    expected_summary = (
        '"patch_plan_summary": '
        '"Parse the final Available Moves block and emit exactly one move."'
    )
    assert expected_summary in summary_text
