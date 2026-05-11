# AutoHarness

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-0f766e)](LICENSE)
[![Package status: alpha](https://img.shields.io/badge/status-alpha-f59e0b)](CHANGELOG.md)
[![CLI: Typer](https://img.shields.io/badge/cli-Typer-111827)](https://typer.tiangolo.com/)

AutoHarness is a package-first CLI for reproducible action-verifier experiments. It helps researchers and eval engineers turn candidate agent code into auditable evidence: deterministic local runs, benchmark leaderboards, TextArena smoke checks, and provider probes that require explicit dry-run, preflight, and budget evidence.

Use it when you need a small harness that can answer:

- Did this candidate choose legal actions?
- Did it improve on dev and holdout fixtures?
- Which candidate wins under the same benchmark matrix?
- Can a provider-backed run pass preflight and budget gates before any live call?

It is inspired by the AutoHarness paper: [Lou et al., "AutoHarness: improving LLM agents by automatically synthesizing a code harness"](https://arxiv.org/abs/2603.03329). This repository is a clean-room scaffold for verifier-first experimentation; it does not claim paper-scale parity.

<p>
  <img src="https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/othello-gameplay-review.gif" alt="Terminal demo showing AutoHarness replaying an Othello trace with legal moves, board flips, score changes, and a final run summary." width="100%">
</p>

## Quickstart

```bash
git clone https://github.com/wx-b/autoharness.git
cd autoharness
uv sync --extra dev
uv run autoharness verify --manifest manifests/offline_smoke.yaml --artifact-root tmp/verify-artifacts/offline-smoke
# Verification passed for run <run-id>
```

That first run needs no provider credentials. It writes ignored local artifacts under `tmp/verify-artifacts/offline-smoke/`.

Check the artifacts:

```bash
ls tmp/verify-artifacts/offline-smoke
# resolved-manifest.json  run-summary.json  trace.json
```

## What You Get

- Manifest-driven verifier runs with deterministic local fixtures.
- Benchmark matrices that compare candidate modules and write leaderboards.
- TextArena smoke manifests for checking real environment integration.
- Provider probe commands with dry-run, preflight, and budget evidence before live calls.
- Structured JSON artifacts for legality, reward, retries, failure bundles, and summaries.
- A practical runtime path that promotes generated candidates into a versioned registry, records rich signatures, persists a candidate search tree, and runs critic/refiner and sandbox evidence.
- A paper-scale protocol smoke check for the deferred 145-game and 16/16 evaluation targets without running costly full benchmarks.
- A small Python package surface that is easy to test, inspect, and extend.

## Common Workflows

Run the CLI:

```bash
uv run autoharness --help
# Commands: verify, campaign, benchmark, provider-probe, provider-report
```

Compare candidate modules with the toy benchmark matrix:

```bash
uv run autoharness benchmark --matrix manifests/toy_benchmark_matrix.yaml --artifact-root tmp/verify-artifacts/toy-benchmark-matrix
# Top candidate: robust (.../benchmark-summary.json, .../leaderboard.md)
```

Run a deterministic refinement campaign:

```bash
uv run autoharness campaign \
  --candidate tests/fixtures/candidates/ttt_latest_move_parser.py \
  --dev-manifest manifests/toy_refinement_dev.yaml \
  --holdout-manifest manifests/toy_refinement_holdout.yaml \
  --artifact-root tmp/verify-artifacts/refinement \
  --patch-text "prefer exact legal actions" \
  --max-iterations 1
# Campaign converged: .../tests/fixtures/candidates/ttt_latest_move_parser.py (.../campaign-summary.json)
```

Verify the practical runtime path:

```bash
make verify-practical-path-runtime
# practical path runtime verified
```

This uses a temporary artifact root and exercises the runtime candidate registry, rich candidate contract, search tree, critic/refiner mutation, sandbox policy, fixed-seed TextArena sweep POC, reward/win-rate benchmark POC, and non-game objective evaluator.

Smoke-test the deferred paper-scale protocol without running the costly benchmark:

```bash
make verify-paper-scale-smoke
# paper-scale protocol smoke verified
```

The smoke verifier preserves the 145-game legality target, 16 one-player and 16 two-player evaluation targets, and 10-parallel-env/1000-step rollout target while confirming `full_benchmark_executed=false`.

Dry-run a provider probe before any live call:

```bash
uv sync --extra dev --extra preflight
uv run autoharness provider-probe \
  --manifest manifests/provider_probe_model_preflight_free.yaml \
  --artifact-root tmp/provider-probes/model-preflight-free \
  --max-spend-usd 1.00
# Provider probe dry-run passed (.../provider-probe-preflight.json, .../provider-probe-budget.json)
```

Summarize provider evidence:

```bash
uv run autoharness provider-report \
  --probe-root tmp/provider-probes/model-preflight-free \
  --output-root tmp/provider-probes/report
# Provider evidence report written to .../provider-evidence-report.json and .../provider-evidence-report.md
```

<details>
<summary><strong>More Game Traces</strong></summary>

These traces show why AutoHarness records actions, legality, rewards, and summaries instead of only command success.

### PigDice Risk Trace

![AutoHarness PigDice risk trace](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/pigdice-risk-review.gif)

The policy only chooses legal actions, but it keeps rolling, repeatedly busts, and finishes with `total_reward=0.0`.

### TicTacToe Movement Trace

![AutoHarness TicTacToe movement trace](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/tictactoe-gameplay-review.gif)

The trace replays a real TextArena TicTacToe run and leaves the machine-checkable summary on screen.

</details>

## How It Works

```text
manifest.yaml
  -> candidate provider
  -> candidate registry and rich signature contract
  -> benchmark suite
  -> action verifier
  -> critic/refiner and search controller
  -> generated-code sandbox
  -> artifact store
  -> JSON summaries, traces, leaderboards, provider evidence
```

The package keeps experiment control in manifests and writes artifacts outside source by default. Verifier logic is deterministic for local fixtures; provider-backed paths require explicit preflight and budget evidence.

See [docs/practical_runtime.md](docs/practical_runtime.md) for practical runtime API examples, [docs/architecture/overview.md](docs/architecture/overview.md) for the component map, and [docs/artifact_policy.md](docs/artifact_policy.md) for tracked source versus generated output rules.

## Models and Provider Checks

The paper uses Gemini-2.5-Flash to synthesize harness code and compares resulting agents against larger models such as Gemini-2.5-Pro and GPT-5.2-High. AutoHarness does not bundle those paper experiments or require a specific hosted model for local verification.

For day-to-day testing, start with deterministic fixture manifests and TextArena smoke checks. When a provider-backed path is useful, AutoHarness can run [ModelPreflight](https://github.com/pylit-ai/model-preflight) routes, Gemini CLI, Gemini SDK, OpenRouter, or local candidate modules through manifest `provider` settings. ModelPreflight is the easiest starting point when you want a reusable provider sanity check before committing budget to larger runs.

Recommended path:

1. Use fixture manifests for normal development and CI.
2. Use `uv sync --extra dev --extra preflight` plus `provider-probe` without `--run` to validate manifest, auth, and budget evidence without generation.
3. Move to a direct provider manifest only after a small canary passes with an isolated artifact root and explicit spend/quota limits.

See [docs/providers.md](docs/providers.md) for provider options, manifest examples, auth modes, and scale-up guidance.

<details>
<summary><strong>Install Options</strong></summary>

Core development install:

```bash
uv sync --extra dev
```

TextArena smoke support:

```bash
uv sync --extra dev --extra textarena
```

Provider adapters:

```bash
uv sync --extra dev --extra providers
```

[ModelPreflight](https://github.com/pylit-ai/model-preflight)-backed probes:

```bash
uv sync --extra dev --extra preflight
```

All optional surfaces:

```bash
uv sync --extra dev --extra textarena --extra providers --extra preflight
```

</details>

<details>
<summary><strong>Development Checks</strong></summary>

Run package checks before opening a change:

```bash
bash scripts/check_release_tree.sh
uv run ruff check .
uv run mypy src
uv run pytest -q
uv build
# dist/ contains the source distribution and wheel
```

</details>

<details>
<summary><strong>Repository Map</strong></summary>

- `src/autoharness/` - package code and CLI implementation.
- `manifests/` - committed fixture, TextArena, benchmark, and provider-probe manifests.
- `tests/` - package test suite.
- `demos/output/` - rendered public demo assets.
- `docs/demos.md` - demo gallery.
- `docs/practical_runtime.md` - practical runtime CLI and Python API guide.
- `docs/providers.md` - model-provider setup and scaling guide.
- `docs/architecture/overview.md` - component and data-flow overview.
- `docs/artifact_policy.md` - tracked source versus generated output policy.
- `docs/mcp/servers.md` - public MCP server notes.

</details>

<details>
<summary><strong>Citation</strong></summary>

AutoHarness is based on the research direction introduced in:

> Xinghua Lou, Miguel Lazaro-Gredilla, Antoine Dedieu, Carter Wendelken, Wolfgang Lehrach, and Kevin P. Murphy. "AutoHarness: improving LLM agents by automatically synthesizing a code harness." arXiv:2603.03329, 2026. https://doi.org/10.48550/arXiv.2603.03329

BibTeX:

```bibtex
@misc{lou2026autoharness,
  title = {AutoHarness: improving LLM agents by automatically synthesizing a code harness},
  author = {Lou, Xinghua and Lazaro-Gredilla, Miguel and Dedieu, Antoine and Wendelken, Carter and Lehrach, Wolfgang and Murphy, Kevin P.},
  year = {2026},
  eprint = {2603.03329},
  archivePrefix = {arXiv},
  primaryClass = {cs.CL},
  doi = {10.48550/arXiv.2603.03329},
  url = {https://arxiv.org/abs/2603.03329}
}
```

</details>

## Status

AutoHarness is alpha software. It is useful for verifier-first development, deterministic toy benchmarks, TextArena smoke checks, provider probes with preflight and budget evidence, and a small-scale practical runtime path with durable candidate, search, critic/refiner, sandbox, reward, and non-game evidence. Paper-scale benchmark execution remains deferred: the PYL-632 smoke protocol is implemented, but the full 145-game and 16/16 evaluation runs are not executed by default.
