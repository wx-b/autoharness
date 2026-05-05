from __future__ import annotations

from pydantic import BaseModel


class EpisodeResult(BaseModel):
    run_id: str
    status: str
    retry_count: int
    steps: int
    final_action: str | None = None
    provider: str
    benchmark: str
    legal_attempts: int = 0
    illegal_attempts: int = 0
    legal_action_rate: float = 0.0
    total_reward: float = 0.0

    def determinism_signature(self) -> tuple[object, ...]:
        return (
            self.status,
            self.retry_count,
            self.steps,
            self.final_action,
            self.provider,
            self.benchmark,
            self.legal_attempts,
            self.illegal_attempts,
            round(self.legal_action_rate, 6),
            round(self.total_reward, 6),
        )
