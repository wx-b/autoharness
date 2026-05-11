# Architecture overview

## Purpose
Enduring technical structure of autoharness. Task-level implementation detail belongs outside the public release tree.

## High-level components
- Candidate runtime - loads candidate modules, enforces legacy and rich interfaces, promotes generated candidates into a versioned registry, and applies sandbox restrictions.
- Benchmark suites - deterministic toy environments plus a narrow TextArena smoke adapter.
- Benchmarking matrix - compares multiple candidate modules across committed suites and emits stable leaderboard artifacts.
- Search and refinement controller - exposes beta-Thompson and best-first selection, summarizes failures, and drives bounded iterative improvement.
- Evaluator and verifier - computes legal-action and reward metrics, applies multi-verifier reranking, checks artifacts, and produces a single pass-fail surface.
- Provider probe - exposes an opt-in, dry-run-first path for live model-backed Gemini probes and ModelPreflight-backed dev tests with provider preflight, dependency checks, budget evidence, and manual `--run` approval.
- Paper-scale protocol smoke - preserves the deferred 145-game and 16/16 evaluation targets without running costly benchmark sweeps by default.
- Artifact store - preserves manifests, traces, failure bundles, and candidate snapshots as durable evidence.

## Data flow
1. Load a candidate module or refinement backend under a fixed suite configuration.
2. Run seed-locked episodes through the benchmark layer with bounded retry, structured candidate generation, and verifier reranking on illegal actions.
3. Promote generated candidates into a registry and record signatures, provenance, hashes, and minimum metrics.
4. Emit step traces, failure bundles, critic summaries, search-tree nodes, sandbox audits, and suite metrics into the artifact store.
5. Feed structured failure evidence into the search or refinement controller for deterministic classification and patch planning.
6. Run matrix-level comparison across committed suites when candidate benchmarking is requested, then emit JSON and Markdown benchmark reports.
7. Run the paper-scale protocol smoke check when validating deferred benchmark shape without paying full compute cost.
8. Aggregate verifier outputs into a single command surface for local and later CI use.
9. Keep generated verification output under ignored local paths unless it is deliberately promoted as release evidence.

## Boundaries
- External boundary: TextArena for the real-environment smoke path and optional live LLM providers for non-blocking synthesis.
- Internal boundary: deterministic fixture-backed verification remains required even when optional live integrations are present.
- Cost boundary: `make verify` remains provider-free; live provider probing is only through explicit `provider-probe --run` commands and is not part of default local or CI verification. Paper-scale benchmark execution is also guarded; `make verify-paper-scale-smoke` validates protocol shape without running the full 145-game or 16/16 evaluation protocol.

## Dependencies
- Python runtime and standard repo verification tooling once the implementation scaffold lands.
- TextArena for the first external environment adapter.
- Gemini CLI for the first live Gemini probe, using the CLI's existing OAuth login state.
- `google-genai` through the optional `providers` extra only for the separate SDK OAuth/ADC provider path; this is distinct from API-key authentication.
- `model-preflight` through the optional `preflight` extra for dogfooding free provider groups and locally hosted model groups from the machine-local ModelPreflight config.

## Out of scope for this doc
- Per-change rollout, file lists, and verification steps belong outside the public release tree.
