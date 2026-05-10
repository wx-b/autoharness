# CLI Demos

These public demos show common AutoHarness workflows with local fixture manifests and no provider credentials required unless a command explicitly opts in.

## First Successful Verification

![AutoHarness quickstart verification](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/quickstart.gif)

Video: [MP4](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/quickstart.mp4) | [WebM](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/quickstart.webm)

This demo is for new users. It verifies the offline smoke manifest and prints the structured run summary without requiring provider credentials.

## Benchmark Matrix

![AutoHarness benchmark matrix](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/benchmark-matrix.gif)

Video: [MP4](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/benchmark-matrix.mp4) | [WebM](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/benchmark-matrix.webm)

This demo is for evaluators comparing candidates. It runs the toy benchmark matrix, writes a leaderboard and summary, then lists the candidate artifacts.

## Provider Probe Dry Run

![AutoHarness provider probe dry run](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/provider-probe.gif)

Video: [MP4](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/provider-probe.mp4) | [WebM](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/provider-probe.webm)

This demo is for advanced setup. It exercises the guarded provider-probe path in dry-run mode, writes preflight and budget evidence, then creates the provider evidence report.
