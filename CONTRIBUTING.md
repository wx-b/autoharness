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
bash scripts/check_release_tree.sh
uv run ruff check .
uv run mypy src
uv run pytest -q
uv build
```

## Artifact Rules

Write fresh verifier output under ignored paths such as `tmp/verify-artifacts/`. Do not commit runtime artifacts unless a documented change explicitly promotes them to curated evidence.
