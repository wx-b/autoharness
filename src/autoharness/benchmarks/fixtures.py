# Requirement coverage: REQ-002-suite-refinement-001
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

from .base import Benchmark, StepOutcome


@dataclass(slots=True)
class FixtureStep:
    observation: str
    valid_actions: list[str]


@dataclass(slots=True)
class FixtureCase:
    case_id: str
    observation: str = "Pick one of: left"
    valid_actions: list[str] = field(default_factory=lambda: ["left"])
    max_steps: int = 1
    script: list[FixtureStep] = field(default_factory=list)


class FixtureBenchmark(Benchmark):
    kind = "fixture"

    def __init__(
        self,
        *,
        observation: str = "Pick one of: left",
        valid_actions: list[str] | None = None,
        max_steps: int = 1,
        script: list[FixtureStep | dict[str, object]] | None = None,
    ) -> None:
        self.observation = observation
        self.valid_actions = valid_actions or ["left"]
        self.script = [
            coerce_fixture_step(
                step,
                default_observation=self.observation,
                default_valid_actions=self.valid_actions,
            )
            for step in script or []
        ]
        self.max_steps = len(self.script) or max_steps
        self._steps_taken = 0

    def reset(self, seed: int | None = None) -> None:
        del seed
        self._steps_taken = 0

    def get_observation(self) -> str:
        return self._current_observation()

    def is_legal(self, action: str) -> bool:
        return action.strip() in self._current_valid_actions()

    def available_actions(self, observation: str | None = None) -> list[str]:
        del observation
        return list(self._current_valid_actions())

    def step(self, action: str) -> StepOutcome:
        legal = self.is_legal(action)
        self._steps_taken += 1
        done = self._steps_taken >= self.max_steps
        reward = 1.0 if legal else -1.0
        return StepOutcome(done=done, reward=reward, metadata={"steps_taken": self._steps_taken})

    def _current_observation(self) -> str:
        if not self.script:
            return self.observation
        return self.script[self._steps_taken].observation

    def _current_valid_actions(self) -> list[str]:
        if not self.script:
            return self.valid_actions
        return self.script[self._steps_taken].valid_actions

    @classmethod
    def from_case(cls, case: FixtureCase | dict[str, Any]) -> FixtureBenchmark:
        fixture_case = coerce_fixture_case(case)
        return cls(
            observation=fixture_case.observation,
            valid_actions=list(fixture_case.valid_actions),
            max_steps=fixture_case.max_steps,
            script=list(fixture_case.script),
        )


def coerce_fixture_step(
    step: FixtureStep | dict[str, object],
    *,
    default_observation: str,
    default_valid_actions: list[str],
) -> FixtureStep:
    if isinstance(step, FixtureStep):
        return step
    observation = step.get("observation", default_observation)
    raw_valid_actions = step.get("valid_actions", default_valid_actions)
    valid_actions = cast(list[str], raw_valid_actions)
    return FixtureStep(
        observation=str(observation),
        valid_actions=[str(action) for action in valid_actions if isinstance(action, str)],
    )


def coerce_fixture_case(case: FixtureCase | dict[str, Any]) -> FixtureCase:
    if isinstance(case, FixtureCase):
        return case
    observation = str(case.get("observation", "Pick one of: left"))
    raw_valid_actions = case.get("valid_actions", ["left"])
    valid_actions = cast(list[str], raw_valid_actions)
    normalized_valid_actions = [
        str(action) for action in valid_actions if isinstance(action, str)
    ]
    raw_script = case.get("script", [])
    script = [
        coerce_fixture_step(
            step,
            default_observation=observation,
            default_valid_actions=normalized_valid_actions,
        )
        for step in cast(list[FixtureStep | dict[str, object]], raw_script)
    ]
    max_steps = int(case.get("max_steps", len(script) or 1))
    case_id = str(case.get("case_id", "")).strip()
    if not case_id:
        raise ValueError("case_id must not be empty")
    return FixtureCase(
        case_id=case_id,
        observation=observation,
        valid_actions=normalized_valid_actions,
        max_steps=max_steps,
        script=script,
    )
