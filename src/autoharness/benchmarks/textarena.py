# Requirement coverage: REQ-001-bootstrap-002, REQ-001-bootstrap-003
# REQ-005-low-cost-textarena-smoke-expansion-002
# REQ-005-low-cost-textarena-smoke-expansion-008
from __future__ import annotations

import re
from typing import Any, cast

from .base import Benchmark, StepOutcome

ACTION_LIST_MARKER_PATTERN = re.compile(
    r"(?:Available Moves|Available actions|Valid moves):\s*(.*)",
    re.IGNORECASE,
)
BRACKETED_ACTION_PATTERN = re.compile(r"\[[^\]]+\]")
NO_VALID_MOVES_PATTERN = re.compile(r"No valid moves", re.IGNORECASE)


def extract_available_actions(observation: str) -> list[str]:
    # REQ-006-provider-backed-probe-cost-auth-policy-015: later no-move markers
    # override stale historical valid-move lines from TextArena observations.
    latest_marker_kind = ""
    latest_marker_payload = ""
    for line in observation.splitlines():
        if NO_VALID_MOVES_PATTERN.search(line):
            latest_marker_kind = "none"
            latest_marker_payload = ""
            continue
        match = ACTION_LIST_MARKER_PATTERN.search(line)
        if match is not None:
            latest_marker_kind = "actions"
            latest_marker_payload = match.group(1)
    if latest_marker_kind != "actions":
        return []
    return BRACKETED_ACTION_PATTERN.findall(latest_marker_payload)


def has_no_valid_moves(observation: str) -> bool:
    latest_marker_kind = ""
    for line in observation.splitlines():
        if NO_VALID_MOVES_PATTERN.search(line):
            latest_marker_kind = "none"
            continue
        if ACTION_LIST_MARKER_PATTERN.search(line) is not None:
            latest_marker_kind = "actions"
    return latest_marker_kind == "none"


def strip_available_moves(observation: str) -> str:
    lines = observation.splitlines()
    filtered_lines = [
        line for line in lines if ACTION_LIST_MARKER_PATTERN.search(line) is None
    ]
    return "\n".join(filtered_lines).strip()


class TextArenaBenchmark(Benchmark):
    kind = "textarena"

    def __init__(
        self,
        *,
        env_id: str,
        num_players: int,
        seed: int | None = None,
        strip_moves: bool = False,
        options: dict[str, Any] | None = None,
    ) -> None:
        self.env_id = env_id
        self.num_players = num_players
        self.seed = seed
        self.strip_moves = strip_moves
        self.options = dict(options or {})
        self._env = self._make_env(env_id, self.options)
        self._current_player_id: int | None = None
        self._raw_observation = ""
        self._closed = False

    def _make_env(self, env_id: str, options: dict[str, Any]) -> Any:
        try:
            import textarena as ta  # type: ignore[import-untyped]
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "textarena is not installed; add the textarena extra to use TextArenaBenchmark"
            ) from exc
        return ta.make(env_id=env_id, **options)

    def reset(self, seed: int | None = None) -> None:
        reset_seed = self.seed if seed is None else seed
        self._env.reset(num_players=self.num_players, seed=reset_seed)
        self._current_player_id = None
        self._raw_observation = ""
        self._closed = False

    def get_observation(self) -> str:
        player_id, observation = self._env.get_observation()
        self._current_player_id = int(player_id)
        observation_text = cast(str, observation)
        self._raw_observation = observation_text
        if self.strip_moves:
            return strip_available_moves(observation_text)
        return observation_text

    def is_legal(self, action: str) -> bool:
        # REQ-006-provider-backed-probe-cost-auth-policy-015
        if has_no_valid_moves(self._raw_observation):
            return bool(action.strip())
        return action.strip() in extract_available_actions(self._raw_observation)

    def available_actions(self, observation: str | None = None) -> list[str]:
        source = self._raw_observation if observation is None else observation
        return extract_available_actions(source)

    def step(self, action: str) -> StepOutcome:
        done, info = self._env.step(action=action)
        metadata = dict(info or {})
        reward = 0.0
        if done and not self._closed:
            final_rewards, game_info = self._env.close()
            self._closed = True
            metadata["final_rewards"] = final_rewards
            metadata["game_info"] = game_info
            if self._current_player_id is not None and final_rewards is not None:
                reward = float(final_rewards.get(self._current_player_id, 0.0))
        return StepOutcome(done=done, reward=reward, metadata=metadata)
