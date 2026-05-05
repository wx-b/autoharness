import re

_MOVE_LIST_RE = re.compile(
    r"^\s*(?:(?:available|legal|valid)\s+(?:moves|actions)|current\s+legal\s+actions|action\s+aliases)\s*:\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)
_MOVE_RE = re.compile(r"\[[^\]\r\n]+\]")


def _latest_moves(board: str) -> list[str]:
    move_lists = _MOVE_LIST_RE.findall(board)
    if not move_lists:
        return []
    return _MOVE_RE.findall(move_lists[-1])


def propose_action(board: str) -> str:
    moves = _latest_moves(board)
    return moves[0] if moves else "[0]"


def is_legal_action(board: str, action: str) -> bool:
    normalized_action = action.strip().strip("'\"")
    return normalized_action in _latest_moves(board)
