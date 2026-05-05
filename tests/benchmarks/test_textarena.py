# Requirement coverage: REQ-001-bootstrap-002, REQ-001-bootstrap-003
# REQ-005-low-cost-textarena-smoke-expansion-002
# REQ-005-low-cost-textarena-smoke-expansion-003
# REQ-005-low-cost-textarena-smoke-expansion-008
import pytest

from autoharness.benchmarks.textarena import (
    TextArenaBenchmark,
    extract_available_actions,
    strip_available_moves,
)

OBSERVATION = """
[GAME] Current Board:
 0 | 1 | 2
Available Moves: '[0]', '[1]', '[2]'
""".strip()

OBSERVATION_WITH_HISTORY = """
[GAME] Current Board:
 0 | 1 | 2
Available Moves: '[0]', '[1]', '[2]'
[Player 0] [0]
[GAME] Current Board:
 O | 1 | 2
Available Moves: '[1]', '[2]'
""".strip()

OBSERVATION_WITH_VALID_MOVES = """
[GAME] Game Board:
Valid moves: '[2, 3]', '[3, 2]'
""".strip()

OBSERVATION_WITH_AVAILABLE_ACTIONS = """
[GAME] Current score: 0
Available actions: '[roll]' or '[hold]'
""".strip()

OBSERVATION_WITH_NO_VALID_MOVES_AFTER_HISTORY = """
[GAME] Game Board:
Valid moves: '[1, 3]', '[3, 3]'
Scores - Black: 8, White: 5
[GAME] Game Board:
No valid moves - you may have to skip.
Scores - Black: 9, White: 6
""".strip()


def test_extract_available_actions_reads_moves_line() -> None:
    assert extract_available_actions(OBSERVATION) == ["[0]", "[1]", "[2]"]


def test_extract_available_actions_reads_valid_moves_line() -> None:
    assert extract_available_actions(OBSERVATION_WITH_VALID_MOVES) == [
        "[2, 3]",
        "[3, 2]",
    ]


def test_extract_available_actions_reads_available_actions_line() -> None:
    assert extract_available_actions(OBSERVATION_WITH_AVAILABLE_ACTIONS) == [
        "[roll]",
        "[hold]",
    ]


def test_extract_available_actions_uses_last_moves_line() -> None:
    assert extract_available_actions(OBSERVATION_WITH_HISTORY) == ["[1]", "[2]"]


def test_extract_available_actions_no_valid_moves_overrides_history() -> None:
    # REQ-006-provider-backed-probe-cost-auth-policy-015
    assert extract_available_actions(OBSERVATION_WITH_NO_VALID_MOVES_AFTER_HISTORY) == []


def test_strip_available_moves_removes_moves_line() -> None:
    stripped = strip_available_moves(
        "\n".join(
            [
                OBSERVATION,
                OBSERVATION_WITH_VALID_MOVES,
                OBSERVATION_WITH_AVAILABLE_ACTIONS,
            ]
        )
    )
    assert "Available Moves:" not in stripped
    assert "Valid moves:" not in stripped
    assert "Available actions:" not in stripped


def test_textarena_benchmark_passes_options_to_environment(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeEnv:
        def reset(self, num_players: int, seed: int | None = None) -> None:
            del num_players, seed

        def get_observation(self) -> tuple[int, str]:
            return (0, OBSERVATION)

        def step(self, action: str) -> tuple[bool, dict[str, object]]:
            del action
            return (True, {})

        def close(self) -> tuple[dict[int, float], dict[str, object]]:
            return ({0: 0.0}, {})

    def fake_make_env(
        self: TextArenaBenchmark,
        env_id: str,
        options: dict[str, object],
    ) -> FakeEnv:
        del self
        captured["env_id"] = env_id
        captured["options"] = options
        return FakeEnv()

    monkeypatch.setattr(TextArenaBenchmark, "_make_env", fake_make_env)
    TextArenaBenchmark(
        env_id="Othello-v0",
        num_players=2,
        seed=7,
        options={"board_size": 4, "show_valid": True},
    )

    assert captured == {
        "env_id": "Othello-v0",
        "options": {"board_size": 4, "show_valid": True},
    }


def test_textarena_benchmark_terminal_step_uses_close_rewards(monkeypatch) -> None:
    class FakeEnv:
        def __init__(self) -> None:
            self.closed = False

        def reset(self, num_players: int, seed: int | None = None) -> None:
            del num_players, seed

        def get_observation(self) -> tuple[int, str]:
            return (0, OBSERVATION)

        def step(self, action: str) -> tuple[bool, dict[str, object]]:
            assert action == "[0]"
            return (True, {"reason": "finished"})

        def close(self) -> tuple[dict[int, float], dict[str, object]]:
            self.closed = True
            return ({0: 1.0, 1: -1.0}, {"winner": 0})

    monkeypatch.setattr(
        TextArenaBenchmark,
        "_make_env",
        lambda self, env_id, options: FakeEnv(),
    )
    benchmark = TextArenaBenchmark(env_id="TicTacToe-v0", num_players=2, seed=7)
    benchmark.reset()
    _ = benchmark.get_observation()
    outcome = benchmark.step("[0]")
    assert outcome.done is True
    assert outcome.reward == 1.0
    assert outcome.metadata["game_info"] == {"winner": 0}
    assert outcome.metadata["final_rewards"] == {0: 1.0, 1: -1.0}


def test_textarena_benchmark_accepts_skip_text_when_no_valid_moves(monkeypatch) -> None:
    # REQ-006-provider-backed-probe-cost-auth-policy-015
    class FakeEnv:
        def reset(self, num_players: int, seed: int | None = None) -> None:
            del num_players, seed

        def get_observation(self) -> tuple[int, str]:
            return (1, OBSERVATION_WITH_NO_VALID_MOVES_AFTER_HISTORY)

        def step(self, action: str) -> tuple[bool, dict[str, object]]:
            assert action == "No valid moves for White. Skipping turn."
            return (True, {"reason": "skipped"})

        def close(self) -> tuple[dict[int, float], dict[str, object]]:
            return ({1: 0.0}, {"reason": "closed"})

    monkeypatch.setattr(
        TextArenaBenchmark,
        "_make_env",
        lambda self, env_id, options: FakeEnv(),
    )
    benchmark = TextArenaBenchmark(env_id="Othello-v0", num_players=2, seed=7)
    benchmark.reset()
    observation = benchmark.get_observation()

    assert benchmark.available_actions(observation) == []
    assert benchmark.is_legal("No valid moves for White. Skipping turn.") is True
    assert benchmark.is_legal("[3, 3]") is True
    assert benchmark.is_legal("") is False


def test_textarena_benchmark_tictactoe_smoke() -> None:
    pytest.importorskip("textarena")
    benchmark = TextArenaBenchmark(env_id="TicTacToe-v0", num_players=2, seed=7)
    benchmark.reset()
    observation = benchmark.get_observation()
    legal_actions = extract_available_actions(observation)
    assert legal_actions
    assert benchmark.is_legal(legal_actions[0]) is True
    outcome = benchmark.step(legal_actions[0])
    assert outcome.done is False
