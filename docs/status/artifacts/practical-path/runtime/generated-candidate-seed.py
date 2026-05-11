from __future__ import annotations

import re


def parse_state(board: str) -> dict[str, object]:
    matches = re.findall(r"Available Moves:\s*(.*)", board)
    moves = re.findall(r"\[[^\]]+\]", matches[-1]) if matches else ["[0]"]
    return {"available_moves": moves, "raw": board}


def legal_actions(state: dict[str, object]) -> list[str]:
    return list(state.get("available_moves", []))


def score_action(state: dict[str, object], action: str) -> float:
    return 1.0 if action in legal_actions(state) else -1.0


def propose_action(board: str) -> str:
    match = re.search(r"Available Moves:\s*(.*)", board)
    if match is None:
        return "[0]"
    tokens = re.findall(r"\[[^\]]+\]", match.group(1))
    return tokens[0] if tokens else "[0]"


def explain_decision(state: dict[str, object], action: str) -> str:
    return f"selected {action} from {legal_actions(state)}"


def is_legal_action(board: str, action: str) -> bool:
    return action in legal_actions(parse_state(board))
