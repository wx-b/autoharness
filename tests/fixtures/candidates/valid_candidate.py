def propose_action(board: str) -> str:
    return board.strip()


def is_legal_action(board: str, action: str) -> bool:
    return action in board
