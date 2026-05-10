# CLI Demos

These demos are generated from committed VHS tapes so the README media stays reproducible. The tapes use local fixture manifests only, isolate artifacts under `/tmp`, and avoid provider calls unless a command explicitly opts in.

## First Successful Verification

![AutoHarness quickstart verification](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/quickstart.gif)

- Source: [`demos/tapes/quickstart.tape`](../demos/tapes/quickstart.tape)
- Video: [MP4](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/quickstart.mp4) | [WebM](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/quickstart.webm)

The hero demo shows the no-credential path: run `verify` against `manifests/offline_smoke.yaml`, then inspect the structured run summary.

## Benchmark Matrix

![AutoHarness benchmark matrix](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/benchmark-matrix.gif)

- Source: [`demos/tapes/benchmark-matrix.tape`](../demos/tapes/benchmark-matrix.tape)
- Video: [MP4](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/benchmark-matrix.mp4) | [WebM](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/benchmark-matrix.webm)

This demo is for evaluators comparing candidates. It runs the toy benchmark matrix, writes a leaderboard and summary, then shows the top candidates without exposing local paths.

## Provider Probe Dry Run

![AutoHarness provider probe dry run](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/provider-probe.gif)

- Source: [`demos/tapes/provider-probe.tape`](../demos/tapes/provider-probe.tape)
- Video: [MP4](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/provider-probe.mp4) | [WebM](https://raw.githubusercontent.com/wx-b/autoharness/main/demos/output/provider-probe.webm)

This demo is for advanced setup. It exercises the guarded provider-probe path in dry-run mode, writes preflight and budget evidence, then summarizes the probe output.

## Regenerate

```bash
vhs validate "demos/tapes/*.tape"
vhs demos/tapes/quickstart.tape
vhs demos/tapes/benchmark-matrix.tape
vhs demos/tapes/provider-probe.tape
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,duration demos/output/quickstart.mp4
```

> **Expected output**
>
> ```text
> demos/output/quickstart.mp4 reports one video stream with nonzero width, height, and duration.
> ```

The `Render CLI demos` GitHub Actions workflow rerenders the tapes when demo sources, manifests, fixtures, or CLI code change and fails if committed media drifts.
