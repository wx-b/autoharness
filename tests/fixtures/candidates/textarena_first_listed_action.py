import re

ACTION_LIST_PATTERN = re.compile(
    r"(?:Available Moves|Available actions|Valid moves):\s*(.*)",
    re.IGNORECASE,
)
BRACKETED_ACTION_PATTERN = re.compile(r"\[[^\]]+\]")


def _listed_actions(observation: str) -> list[str]:
    matches = ACTION_LIST_PATTERN.findall(observation)
    if not matches:
        return []
    return BRACKETED_ACTION_PATTERN.findall(matches[-1])


def propose_action(board: str) -> str:
    actions = _listed_actions(board)
    return actions[0] if actions else "[0]"


def is_legal_action(board: str, action: str) -> bool:
    return action in _listed_actions(board)
