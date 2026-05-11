from __future__ import annotations

from pydantic import BaseModel, Field


class SearchNode(BaseModel):
    node_id: str
    candidate_hash: str
    parent_id: str | None = None
    candidate_id: str | None = None
    mutation_family: str = "seed"
    selected_rationale: str = ""
    raw_trace_links: list[str] = Field(default_factory=list)
    controller_state: dict[str, object] = Field(default_factory=dict)
    node_scores: dict[str, float] = Field(default_factory=dict)
    recomputable_metrics: dict[str, float] = Field(default_factory=dict)
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
