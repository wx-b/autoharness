import re


def propose_action(board: str) -> str:
    lines = [line.strip() for line in board.splitlines() if line.strip()]
    observation_line = lines[1] if len(lines) > 1 else ""
    match = re.search(r"Available Moves:\s*(.*)", observation_line)
    if match is None:
        return "[retry]"
    quoted_move = re.search(r"'(\[[^\]]+\])'", match.group(1))
    if quoted_move is not None:
        return f"'{quoted_move.group(1)}'"
    moves = re.findall(r"\[[^\]]+\]", match.group(1))
    return moves[0] if moves else "[retry]"


def is_legal_action(board: str, action: str) -> bool:
    return action in board
