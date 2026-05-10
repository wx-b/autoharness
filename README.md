# AutoHarness

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-0f766e)](LICENSE)
[![Package status: alpha](https://img.shields.io/badge/status-alpha-f59e0b)](CHANGELOG.md)
[![CLI: Typer](https://img.shields.io/badge/cli-Typer-111827)](https://typer.tiangolo.com/)

AutoHarness is a package-first CLI for reproducible action-verifier experiments. It helps researchers and eval engineers turn candidate agent code into auditable evidence: deterministic local runs, benchmark leaderboards, TextArena smoke checks, and guarded provider probes.

Use it when you need a small harness that can answer:

- Did this candidate choose legal actions?
- Did it improve on dev and holdout fixtures?
- Which candidate wins under the same benchmark matrix?
- Can a provider-backed run pass preflight and budget gates before any live call?

It is inspired by the AutoHarness paper: [Lou et al., "AutoHarness: improving LLM agents by automatically synthesizing a code harness"](https://arxiv.org/abs/2603.03329). This repository is a clean-room scaffold for verifier-first experimentation; it does not claim paper-scale parity.

<p>
  <img src="https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/quickstart.gif" alt="Terminal demo showing AutoHarness verifying the offline smoke manifest and printing the structured run summary." width="100%">
</p>

<p>
  <sub>Video formats: <a href="https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/quickstart.mp4">MP4</a> | <a href="https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/quickstart.webm">WebM</a>. More demos: <a href="docs/demos.md">docs/demos.md</a>.</sub>
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

Dry-run a provider probe before any live call:

```bash
uv sync --extra dev --extra preflight
uv run autoharness provider-probe \
  --manifest manifests/provider_probe_model_preflight_free.yaml \
  --artifact-root tmp/provider-probes/model-preflight-free \
  --max-spend-usd 1.00 \
  --dry-run
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
<summary><strong>More Demos</strong></summary>

The README keeps the first-success demo above the fold. Deeper walkthroughs live in [docs/demos.md](docs/demos.md).

### Benchmark Matrix

![AutoHarness benchmark matrix](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/benchmark-matrix.gif)

Video: [MP4](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/benchmark-matrix.mp4) | [WebM](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/benchmark-matrix.webm).

### Provider Probe Dry Run

![AutoHarness provider probe dry run](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/provider-probe.gif)

Video: [MP4](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/provider-probe.mp4) | [WebM](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/provider-probe.webm).

</details>

## How It Works

```text
manifest.yaml
  -> candidate provider
  -> benchmark suite
  -> action verifier
  -> artifact store
  -> JSON summaries, traces, leaderboards, provider evidence
```

The package keeps experiment control in manifests and writes artifacts outside source by default. Verifier logic is deterministic for local fixtures; provider-backed paths require explicit preflight and budget evidence.

See [docs/architecture/overview.md](docs/architecture/overview.md) for the component map and [docs/artifact_policy.md](docs/artifact_policy.md) for tracked source versus generated output rules.

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
- `tests/` - public package test suite.
- `demos/output/` - rendered public demo assets.
- `docs/demos.md` - demo gallery.
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
