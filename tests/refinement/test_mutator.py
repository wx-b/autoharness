from pathlib import Path

import pytest

from autoharness.artifacts.models import CriticSummary
from autoharness.refinement.mutator import DeterministicPatchMutator


def test_deterministic_mutator_rewrites_stale_available_moves_parser() -> None:
    source = Path("tests/fixtures/candidates/ttt_first_historical_move.py").read_text()
    critic_summary = CriticSummary(
        run_id="run-1",
        failure_type="illegal_not_in_set",
        root_cause="Candidate emitted an action outside the latest legal action set.",
        current_legal_actions=["[1]", "[2]"],
        attempts=["[0]", "[0]"],
        recommended_change="Parse the latest legal action set from the observation.",
    )

    mutated_source = DeterministicPatchMutator().mutate(
        source=source,
        critic_summary=critic_summary,
        patch_plan_summary="Parse the final Available Moves block and emit exactly one move.",
    )

    assert "matches = re.findall" in mutated_source
    assert "matches[-1]" in mutated_source
    assert "match = re.search" not in mutated_source


def test_deterministic_mutator_raises_when_no_rule_matches() -> None:
    critic_summary = CriticSummary(
        run_id="run-2",
        failure_type="illegal_state_conflict",
        root_cause="Unsupported failure family for this mutator.",
        current_legal_actions=[],
        attempts=["noop"],
        recommended_change="Do something unrelated.",
    )

    with pytest.raises(ValueError, match="No deterministic mutation rule matched"):
        DeterministicPatchMutator().mutate(
            source="def propose_action(board: str) -> str:\n    return board\n",
            critic_summary=critic_summary,
            patch_plan_summary="Do something unrelated.",
        )
