import re


def propose_action(board: str) -> str:
    match = re.search(r"Available Moves:\s*(.*)", board)
    if match is None:
        return "[0]"
    tokens = re.findall(r"\[[^\]]+\]", match.group(1))
    return tokens[0] if tokens else "[0]"


def is_legal_action(board: str, action: str) -> bool:
    return action in board
