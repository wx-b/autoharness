# Requirement coverage: REQ-001-bootstrap-004
from autoharness.artifacts.models import FailureBundle
from autoharness.critics.deterministic import DeterministicCritic


def test_deterministic_critic_classifies_illegal_not_in_set() -> None:
    bundle = FailureBundle(
        run_id="run-1",
        reason="illegal-action-exhausted",
        observation="Available Moves: '[1]', '[2]'",
        attempts=["[8]", "[7]"],
        current_legal_actions=["[1]", "[2]"],
    )

    summary = DeterministicCritic().summarize(bundle)

    assert summary.failure_type == "illegal_not_in_set"
    assert summary.current_legal_actions == ["[1]", "[2]"]
    assert "latest legal action set" in summary.root_cause.lower()


def test_deterministic_critic_classifies_format_error_for_blank_action() -> None:
    bundle = FailureBundle(
        run_id="run-2",
        reason="illegal-action-exhausted",
        observation="Available Moves: '[1]', '[2]'",
        attempts=["", "   "],
        current_legal_actions=["[1]", "[2]"],
    )

    summary = DeterministicCritic().summarize(bundle)

    assert summary.failure_type == "format_error"
    assert "empty or whitespace-only" in summary.root_cause
