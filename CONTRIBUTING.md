# Contributing

AutoHarness is developed as a Python 3.12 package.

## Setup

```bash
uv sync --extra dev
```

Install optional extras only when working on the related surface:

```bash
uv sync --extra dev --extra textarena --extra providers --extra preflight
```

## Checks

Run these before opening a change:

```bash
scripts/check_public_boundary.sh
uv run ruff check .
uv run mypy src
uv run pytest -q
uv build
```

## Artifact Rules

Write fresh verifier output under ignored paths such as `tmp/verify-artifacts/`. Do not commit runtime artifacts unless a spec explicitly promotes them to curated evidence.

Private/local agent artifacts must stay out of the public repository.
