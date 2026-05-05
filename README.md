# AutoHarness

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-0f766e)](LICENSE)
[![Package status: alpha](https://img.shields.io/badge/status-alpha-f59e0b)](CHANGELOG.md)
[![CLI: Typer](https://img.shields.io/badge/cli-Typer-111827)](https://typer.tiangolo.com/)

AutoHarness is a package-first CLI for reproducible action-verifier experiments. It gives researchers and eval engineers a small, inspectable loop for running candidates against deterministic toy environments, TextArena smoke tasks, and guarded provider probes.

It is inspired by the AutoHarness paper: [Lou et al., "AutoHarness: improving LLM agents by automatically synthesizing a code harness"](https://arxiv.org/abs/2603.03329). This repository is a clean-room scaffold for verifier-first experimentation; it does not claim paper-scale parity.

## Quickstart

```bash
git clone https://github.com/wx-b/autoharness.git
cd autoharness
uv sync --extra dev
uv run autoharness verify \
  --manifest manifests/offline_smoke.yaml \
  --artifact-root tmp/verify-artifacts/offline-smoke
```

Expected result:

```text
Verification passed for run <run-id>
```

That command runs without provider credentials and writes fresh output under `tmp/`, which is ignored by default.

## What You Get

- Manifest-driven verifier runs with deterministic local fixtures.
- Benchmark matrices that compare candidate modules and write leaderboards.
- TextArena smoke manifests for checking real environment integration.
- Provider probe commands with dry-run and budget gates before live calls.
- Structured artifacts for legality, reward, failure bundles, and summaries.
- A small Python package surface that is easy to test, inspect, and extend.

## Common Commands

Run the CLI:

```bash
uv run autoharness --help
```

Expected command set:

```text
verify
campaign
benchmark
provider-probe
provider-report
```

Compare deterministic candidate baselines:

```bash
uv run autoharness benchmark \
  --matrix manifests/toy_benchmark_matrix.yaml \
  --artifact-root tmp/verify-artifacts/toy-benchmark-matrix
```

Expected result:

```text
Top candidate: robust (.../benchmark-summary.json, .../leaderboard.md)
```

Dry-run a provider-backed probe:

```bash
uv sync --extra dev --extra preflight
uv run autoharness provider-probe \
  --manifest manifests/provider_probe_model_preflight_free.yaml \
  --artifact-root tmp/verify-artifacts/provider-probe-free \
  --dry-run
```

Expected result:

```text
Provider probe dry-run passed (.../provider-probe-preflight.json, .../provider-probe-budget.json)
```

## How It Works

```text
manifest -> provider/candidate -> environment loop -> verifier -> artifact store
                                            |
                                            v
                                 summaries, failures, leaderboards
```

The package keeps the experiment loop explicit:

- Manifests describe candidates, environments, seeds, and artifact roots.
- Providers adapt candidate modules, model-preflight, Gemini, or Gemini CLI surfaces.
- Runtime loops execute episodes and collect action legality and reward signals.
- Critics and benchmarks turn run traces into inspectable summaries.
- Artifact stores persist evidence without requiring source-control churn.

See [docs/architecture/overview.md](docs/architecture/overview.md) for the fuller component map.

<details>
<summary><strong>Install Options</strong></summary>

Base development environment:

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

model-preflight backed probes:

```bash
uv sync --extra dev --extra preflight
```

All optional surfaces:

```bash
uv sync --extra dev --extra textarena --extra providers --extra preflight
```

</details>

<details>
<summary><strong>Workflow Examples</strong></summary>

Run a deterministic refinement campaign:

```bash
uv run autoharness campaign \
  --candidate tests/fixtures/candidates/ttt_latest_move_parser.py \
  --dev-manifest manifests/toy_refinement_dev.yaml \
  --holdout-manifest manifests/toy_refinement_holdout.yaml \
  --artifact-root tmp/verify-artifacts/refinement \
  --patch-text "prefer exact legal actions" \
  --max-iterations 1
```

Expected result:

```text
Campaign converged: .../tests/fixtures/candidates/ttt_latest_move_parser.py (.../campaign-summary.json)
```

Run TextArena smoke manifests after installing the `textarena` extra:

```bash
uv run autoharness verify \
  --manifest manifests/textarena_tictactoe_smoke.yaml \
  --artifact-root tmp/verify-artifacts/textarena-tictactoe
```

Expected result:

```text
Verification passed for run <run-id>
```

</details>

<details>
<summary><strong>Development Checks</strong></summary>

Run the standard gate before proposing changes:

```bash
scripts/check_public_boundary.sh
uv run ruff check .
uv run mypy src
uv run pytest -q
uv build
```

Expected result:

```text
all commands exit 0
ruff reports: All checks passed!
mypy reports: Success: no issues found in 45 source files
pytest reports: 104 passed
uv build writes an sdist and wheel under dist/
```

The first command is a source-distribution guard. It keeps the package tree focused on releaseable source and docs.

</details>

<details>
<summary><strong>Artifacts and Outputs</strong></summary>

Write fresh verifier output under `tmp/verify-artifacts/` or another ignored local path:

```bash
uv run autoharness verify \
  --manifest manifests/offline_smoke.yaml \
  --artifact-root tmp/verify-artifacts/offline-smoke
```

Runtime artifacts and generated evidence are reproducible outputs. Durable evidence should be promoted into docs deliberately rather than committed as raw run output.

See [docs/artifact_policy.md](docs/artifact_policy.md).

</details>

<details>
<summary><strong>Repository Map</strong></summary>

- `src/autoharness/` - package code and CLI implementation.
- `manifests/` - smoke, benchmark, TextArena, and provider-probe manifests.
- `tests/` - public package test suite.
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

AutoHarness is alpha software. The current public package is useful for verifier-first development, deterministic toy benchmarks, TextArena smoke checks, and guarded provider-probe plumbing. Paper-faithful critic/search reproduction, broad TextArena coverage, and full harness-as-policy experiments remain research work.
