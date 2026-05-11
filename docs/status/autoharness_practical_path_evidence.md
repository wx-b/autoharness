# AutoHarness Practical Path Evidence

Status: small-scale runtime practical path is complete. The verifier generates a candidate, classifies a real failure bundle, mutates the candidate, promotes it through the registry, runs sandbox checks, executes a fixed-seed sweep POC, runs reward/win-rate comparisons, and evaluates non-game objective domains.

Scope guard: this is not paper parity. Deferred paper-scale work remains the full 145-game legality benchmark and the full 16 1P / 16 2P protocol.

## Artifact Index
- `candidate_registry_path`: `docs/status/artifacts/practical-path/candidate-registry.json`
- `signatures_path`: `docs/status/artifacts/practical-path/candidate-signatures.json`
- `search_tree_path`: `docs/status/artifacts/practical-path/candidate-search-tree.json`
- `critic_refiner_path`: `docs/status/artifacts/practical-path/critic-refiner-runtime.json`
- `mutation_artifact_path`: `docs/status/artifacts/practical-path/mutation-artifact.json`
- `sandbox_audit_path`: `docs/status/artifacts/practical-path/sandbox-audit.json`
- `textarena_sweep_path`: `docs/status/artifacts/practical-path/textarena-sweep-plan.json`
- `benchmark_report_path`: `docs/status/artifacts/practical-path/reward-winrate-benchmark.json`
- `non_game_domain_path`: `docs/status/artifacts/practical-path/non-game-domain-report.json`
- `completion_report_path`: `docs/status/artifacts/practical-path/practical-path-runtime-completion.json`

## Ticket Coverage
- PYL-610: runtime candidate registry promote/list/show/load/export/hash/provenance.
- PYL-611: versioned rich candidate signature with legacy compatibility.
- PYL-612: runtime search tree with five hypotheses, parentage, scores, and traces.
- PYL-613: critic/refiner consumes failure bundle and emits mutation artifact.
- PYL-614: local sandbox executes allowed candidate and denies adversarial cases.
- PYL-615: fixed-seed TextArena sweep config and small local POC execution.
- PYL-616: reward and swapped-order win-rate benchmark with negative control.
- PYL-617: non-game domain constraints, objectives, metric reducers, reports.
- PYL-618: end-to-end runtime verifier and public-safe status report.
