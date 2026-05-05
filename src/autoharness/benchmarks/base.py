from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class StepOutcome:
    done: bool
    reward: float
    metadata: dict[str, Any] = field(default_factory=dict)


class Benchmark(ABC):
    kind: str

    @abstractmethod
    def reset(self, seed: int | None = None) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_observation(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def is_legal(self, action: str) -> bool:
        raise NotImplementedError

    def available_actions(self, observation: str | None = None) -> list[str] | None:
        del observation
        return None

    @abstractmethod
    def step(self, action: str) -> StepOutcome:
        raise NotImplementedError
