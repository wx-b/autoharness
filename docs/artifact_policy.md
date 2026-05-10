# Artifact Policy

Runtime outputs are reproducible artifacts, not source. They should be written under ignored local paths such as `tmp/verify-artifacts/` and should not be committed by default.

## Ignored Runtime Output

- `tmp/`
- `artifacts/`
- `generated/`
- local provider probe traces and failure bundles

## Release Rule

A release candidate should pass checks from a clean tree without rewriting tracked artifact snapshots.

## Curated Demo Media

Demo assets under `demos/output/` are committed because they are public documentation, not runtime evidence. Runtime evidence and verifier output should stay under ignored artifact directories unless explicitly promoted.
