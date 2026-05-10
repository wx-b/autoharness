# CLI Demos

This gallery keeps the README focused while preserving deeper proof recordings for evaluators.

## First Successful Verification

![AutoHarness quickstart verification](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/quickstart.gif)

Video: [MP4](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/quickstart.mp4) | [WebM](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/quickstart.webm)

This demo is for new users. It verifies the offline smoke manifest and prints the structured run summary without requiring provider credentials.

## Campaign Proof

![AutoHarness campaign proof](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/campaign-proof-review.gif)

Video: [MP4](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/campaign-proof-review.mp4) | [WebM](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/campaign-proof-review.webm)

This proof shows a refinement campaign changing behavior: the baseline repeats an illegal stale action, the refined candidate selects from the current legal moves, and the holdout passes.

## Benchmark Proof

![AutoHarness benchmark proof](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/benchmark-proof-review.gif)

Video: [MP4](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/benchmark-proof-review.mp4) | [WebM](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/benchmark-proof-review.webm)

This proof shows ranking by behavior, not command completion. The robust candidate is the only one that passes both suites.

## Progress Timeline

![AutoHarness progress timeline](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/progress-timeline-review.gif)

Video: [MP4](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/progress-timeline-review.mp4) | [WebM](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/progress-timeline-review.webm)

This timeline shows fixture-backed candidate progression from stale-history failures to alias handling and then robust legal-action behavior.

## Gameplay Traces

The README uses Othello as the hero because the board flips make state changes visible immediately. PigDice and TicTacToe remain collapsed in the README so the first page does not become an animation gallery.

## Provider Probe Dry Run

![AutoHarness provider probe dry run](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/provider-probe.gif)

Video: [MP4](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/provider-probe.mp4) | [WebM](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/provider-probe.webm)

This demo is for provider integration checks. It runs the probe in dry-run mode, validates the manifest and budget guardrails, and writes preflight artifacts without making live provider calls.
