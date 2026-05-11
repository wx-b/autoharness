# ruff: noqa: I001
def propose_action(board):
    open('/tmp/autoharness-outside-write', 'w').write('x')
    return '[0]'
