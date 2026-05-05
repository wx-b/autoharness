# Requirement coverage: REQ-001-bootstrap-002
from autoharness.search.controller import (
    BestFirstProgramSearchController,
    BetaThompsonController,
    ThompsonStyleController,
)
from autoharness.search.models import SearchNode


def test_controller_updates_node_stats() -> None:
    node = SearchNode(node_id="n1", candidate_hash="abc")
    controller = ThompsonStyleController()
    updated = controller.record_result(node=node, legal_actions=3, illegal_actions=1)
    assert updated.legal_actions == 3
    assert updated.illegal_actions == 1
    assert controller.score(updated) > 0.5


def test_beta_thompson_controller_selects_by_sampled_score() -> None:
    samples = iter([0.1, 0.9])
    controller = BetaThompsonController(sampler=lambda alpha, beta: next(samples))
    first = SearchNode(node_id="n1", candidate_hash="a", legal_actions=10, illegal_actions=0)
    second = SearchNode(node_id="n2", candidate_hash="b", legal_actions=0, illegal_actions=10)
    selected = controller.select_node([first, second])
    assert selected.node_id == "n2"


def test_best_first_program_search_controller_uses_weighted_score() -> None:
    controller = BestFirstProgramSearchController()
    stronger = SearchNode(
        node_id="n1",
        candidate_hash="a",
        legal_actions=8,
        illegal_actions=2,
        reward_total=5.0,
        exception_count=0,
        latency_ms=50.0,
        novelty_bonus=0.2,
    )
    weaker = SearchNode(
        node_id="n2",
        candidate_hash="b",
        legal_actions=8,
        illegal_actions=2,
        reward_total=1.0,
        exception_count=2,
        latency_ms=150.0,
        novelty_bonus=0.0,
    )
    assert controller.select_node([stronger, weaker]).node_id == "n1"
