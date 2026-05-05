from __future__ import annotations

from pydantic import BaseModel


class SearchNode(BaseModel):
    node_id: str
    candidate_hash: str
    parent_id: str | None = None
    legal_actions: int = 0
    illegal_actions: int = 0
    reward_total: float = 0.0
    exception_count: int = 0
    latency_ms: float = 0.0
    novelty_bonus: float = 0.0

    @property
    def posterior_mean(self) -> float:
        return (1 + self.legal_actions) / (2 + self.legal_actions + self.illegal_actions)

    @property
    def legality_rate(self) -> float:
        total = self.legal_actions + self.illegal_actions
        if total == 0:
            return 0.0
        return self.legal_actions / total
