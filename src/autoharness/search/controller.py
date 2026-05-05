# Requirement coverage: REQ-001-bootstrap-002
from __future__ import annotations

import random
from collections.abc import Callable

from autoharness.search.models import SearchNode


class BetaThompsonController:
    def __init__(
        self,
        *,
        sampler: Callable[[float, float], float] | None = None,
        seed: int | None = None,
    ) -> None:
        self._rng = random.Random(seed)
        self._sampler = sampler

    def record_result(
        self,
        *,
        node: SearchNode,
        legal_actions: int,
        illegal_actions: int,
    ) -> SearchNode:
        return node.model_copy(
            update={
                "legal_actions": node.legal_actions + legal_actions,
                "illegal_actions": node.illegal_actions + illegal_actions,
            }
        )

    def sample_score(self, node: SearchNode) -> float:
        alpha = 1.0 + float(node.legal_actions)
        beta = 1.0 + float(node.illegal_actions)
        if self._sampler is not None:
            return self._sampler(alpha, beta)
        return self._rng.betavariate(alpha, beta)

    def score(self, node: SearchNode) -> float:
        return node.posterior_mean

    def select_node(self, nodes: list[SearchNode]) -> SearchNode:
        return max(nodes, key=lambda node: (self.sample_score(node), node.node_id))


class BestFirstProgramSearchController:
    def __init__(
        self,
        *,
        legality_weight: float = 1.0,
        reward_weight: float = 0.3,
        exception_weight: float = 0.2,
        latency_weight: float = 0.001,
        novelty_weight: float = 0.1,
    ) -> None:
        self.legality_weight = legality_weight
        self.reward_weight = reward_weight
        self.exception_weight = exception_weight
        self.latency_weight = latency_weight
        self.novelty_weight = novelty_weight

    def record_result(
        self,
        *,
        node: SearchNode,
        legal_actions: int,
        illegal_actions: int,
        reward_total: float = 0.0,
        exception_count: int = 0,
        latency_ms: float = 0.0,
        novelty_bonus: float | None = None,
    ) -> SearchNode:
        updated_novelty = node.novelty_bonus if novelty_bonus is None else novelty_bonus
        return node.model_copy(
            update={
                "legal_actions": node.legal_actions + legal_actions,
                "illegal_actions": node.illegal_actions + illegal_actions,
                "reward_total": node.reward_total + reward_total,
                "exception_count": node.exception_count + exception_count,
                "latency_ms": latency_ms or node.latency_ms,
                "novelty_bonus": updated_novelty,
            }
        )

    def score(self, node: SearchNode) -> float:
        return (
            self.legality_weight * node.legality_rate
            + self.reward_weight * node.reward_total
            - self.exception_weight * node.exception_count
            - self.latency_weight * node.latency_ms
            + self.novelty_weight * node.novelty_bonus
        )

    def select_node(self, nodes: list[SearchNode]) -> SearchNode:
        return max(nodes, key=lambda node: (self.score(node), node.node_id))


ThompsonStyleController = BetaThompsonController
