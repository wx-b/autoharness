import re


def propose_action(board: str) -> str:
    matches = re.findall(r"Available Moves:\s*(.*)", board)
    if not matches:
        return "[0]"
    moves = re.findall(r"\[[^\]]+\]", matches[-1])
    return moves[0] if moves else "[0]"


def is_legal_action(board: str, action: str) -> bool:
    return action in board
