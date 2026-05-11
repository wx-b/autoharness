# AutoHarness Practical Path Evidence

This report is public-safe. It records local deterministic artifacts only; no paid provider, production, or live-system calls were made.

## Artifact Index
- `candidate_registry_path`: `docs/status/artifacts/practical-path/candidate-registry.json`
- `signatures_path`: `docs/status/artifacts/practical-path/candidate-signatures.json`
- `search_tree_path`: `docs/status/artifacts/practical-path/candidate-search-tree.json`
- `critic_refiner_path`: `docs/status/artifacts/practical-path/critic-refiner-taxonomy.json`
- `sandbox_audit_path`: `docs/status/artifacts/practical-path/sandbox-audit.json`
- `textarena_sweep_path`: `docs/status/artifacts/practical-path/textarena-sweep-plan.json`
- `benchmark_report_path`: `docs/status/artifacts/practical-path/reward-winrate-benchmark.json`
- `non_game_domain_path`: `docs/status/artifacts/practical-path/non-game-domain-spec.json`

## Ticket Coverage
- PYL-610: candidate registry and promotion flow.
- PYL-611: candidate/domain signatures with propose_action compatibility.
- PYL-612: search tree with parentage, mutation family, scores, rationale, metrics.
- PYL-613: critic/refiner taxonomy and mutation artifacts.
- PYL-614: sandbox policy, resource limits, audit log, adversarial cases.
- PYL-615: fixed-seed TextArena sweep config for 10 parallel envs and 1000 steps.
- PYL-616: reward/win-rate benchmark report with baseline deltas and 2P swapped-order POC.
- PYL-617: non-game domain constraints and objective metrics.
- PYL-618: end-to-end verifier and public-safe status report.

## Verification Scope
- Small-scale verified: schemas, artifact generation, static sandbox denials, local package tests, build, import smoke, public boundary check.
- Deferred from paper parity: large provider-backed runs, paid model sweeps, long 10x1000 TextArena execution, container hardening.
