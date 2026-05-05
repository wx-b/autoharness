import re


def propose_action(board: str) -> str:
    matches = re.findall(r"Available Moves:\s*(.*)", board)
    if not matches:
        return "[0]"
    tokens = re.findall(r"\[[^\]]+\]", matches[-1])
    return tokens[0] if tokens else "[0]"


def is_legal_action(board: str, action: str) -> bool:
    return action in board
