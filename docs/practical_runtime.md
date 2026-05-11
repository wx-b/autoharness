# Practical runtime API guide

AutoHarness includes a small practical runtime path for exercising learned candidate code without claiming paper-scale parity. It is designed to produce public-safe evidence from a fresh local run: generated candidate source, a promoted candidate registry entry, rich candidate signatures, a search tree, critic/refiner mutation evidence, sandbox results, reward/win-rate checks, and non-game domain metrics.

## CLI verification

Run the practical runtime verifier with temporary artifacts:

```bash
make verify-practical-path-runtime
# practical path runtime verified
```

Run the deferred paper-scale protocol smoke check:

```bash
make verify-paper-scale-smoke
# paper-scale protocol smoke verified
```

The paper-scale smoke target verifies protocol shape only. It preserves these targets in generated evidence but does not run the costly benchmark:

- 145-game TextArena legality benchmark target.
- 16 one-player and 16 two-player end-to-end evaluation target.
- 10 parallel environments for 1000 rollout steps.
- Swapped-order two-player evaluation.

## Python practical-path API

Use `generate_practical_path_evidence` when you want a single call that exercises the runtime path and writes evidence:

```python
from pathlib import Path

from autoharness.practical import generate_practical_path_evidence

evidence = generate_practical_path_evidence(
    artifact_root=Path("tmp/practical-path"),
    status_report_path=Path("tmp/practical-path/status.md"),
    candidate_path=Path("tests/fixtures/candidates/ttt_first_available.py"),
)

print(evidence.candidate_registry_path)
print(evidence.search_tree_path)
print(evidence.completion_report_path)
```

Expected status:

```text
tmp/practical-path/candidate-registry.json
tmp/practical-path/candidate-search-tree.json
tmp/practical-path/practical-path-runtime-completion.json
```

## Candidate registry API

Promote generated or fixture-backed candidate code into a versioned registry:

```python
from pathlib import Path

from autoharness.candidates.registry import CandidateRegistry

registry = CandidateRegistry(Path("tmp/candidate-library"))
record = registry.promote(
    Path("tests/fixtures/candidates/ttt_first_available.py"),
    provenance={"source_kind": "local_fixture"},
    minimum_metrics={"legal_action_rate": 1.0},
)

module = registry.load(record.candidate_id)
print(record.candidate_id)
print(module.propose_action("Available Moves: [0], [1]"))
```

Expected output shape:

```text
candidate-...
[0]
```

The registry writes `candidate-registry.json` plus a copy of each promoted candidate under `candidates/`. Promotion validates the candidate contract and rejects a reused candidate id with different source content.

## Rich candidate signatures

Candidates may expose the legacy verifier pair or the richer practical contract:

```python
def propose_action(board: str) -> str: ...
def parse_state(board: str) -> dict[str, object]: ...
def legal_actions(state: dict[str, object]) -> list[str]: ...
def score_action(state: dict[str, object], action: str) -> float: ...
def explain_decision(state: dict[str, object], action: str) -> str: ...
```

The compatibility floor is still `propose_action`. A practical candidate must also expose either `is_legal_action` or the richer `parse_state` / `legal_actions` / `score_action` trio.

## Paper-scale protocol API

Use `write_paper_scale_protocol_evidence` to write the PYL-632 protocol evidence without running the expensive benchmark:

```python
from pathlib import Path

from autoharness.benchmarking.paper_scale import write_paper_scale_protocol_evidence

evidence = write_paper_scale_protocol_evidence(
    artifact_root=Path("tmp/paper-scale"),
    status_report_path=Path("tmp/paper-scale/status.md"),
)

print(evidence.protocol_status)
print(evidence.full_benchmark_executed)
```

Expected output:

```text
smoke_verified_full_run_deferred
False
```

Full paper-scale runs require a separate operator-approved budget window. The smoke verifier intentionally exits if `--run-full-benchmarks` is passed.
