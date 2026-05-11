# AutoHarness Paper-Scale Protocol Smoke Evidence

Status: PYL-632 protocol smoke is implemented and verified. The full paper-scale benchmark did not run.

## Targets
- Legality benchmark target: 145 TextArena games.
- End-to-end evaluation target: 16 one-player games and 16 two-player games.
- Rollout training target: 10 parallel envs for 1000 steps.
- Fixed seeds: 7, 11, 13, 17, 19.

## Smoke Verification
- Full benchmark executed: false.
- Smoke games: TicTacToe-v0, Othello-v0, PigDice-v0.
- Compute guard: explicit operator approval and budget window required for a full run.

## Artifact Index
- `protocol_path`: `docs/status/artifacts/paper-scale/paper-scale-protocol.json`
- `smoke_summary_path`: `docs/status/artifacts/paper-scale/paper-scale-smoke-summary.json`
