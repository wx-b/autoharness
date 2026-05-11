from __future__ import annotations

import argparse
import json
from pathlib import Path

from autoharness.benchmarking.paper_scale import write_paper_scale_protocol_evidence


def main() -> None:
    args = _parse_args()
    if args.run_full_benchmarks:
        raise SystemExit(
            "Full paper-scale benchmarks are intentionally disabled in this smoke verifier"
        )

    repo = Path(__file__).resolve().parents[1]
    artifact_root = (
        args.artifact_root or repo / "docs" / "status" / "artifacts" / "paper-scale"
    )
    status_report = (
        args.status_report or repo / "docs" / "status" / "paper_scale_protocol_smoke.md"
    )
    evidence = write_paper_scale_protocol_evidence(
        artifact_root=artifact_root,
        status_report_path=status_report,
    )

    required_paths = [
        evidence.protocol_path,
        evidence.smoke_summary_path,
        evidence.status_report_path,
    ]
    missing = [path for path in required_paths if not Path(path).exists()]
    if missing:
        raise SystemExit(f"Missing paper-scale protocol artifacts: {missing}")

    protocol = json.loads(Path(evidence.protocol_path).read_text())
    target = protocol["target"]
    smoke_run = protocol["smoke_run"]
    if target["legality_game_count"] != 145:
        raise SystemExit("Paper-scale protocol must preserve the 145-game legality target")
    if target["end_to_end_one_player_games"] != 16:
        raise SystemExit("Paper-scale protocol must preserve the 16 one-player target")
    if target["end_to_end_two_player_games"] != 16:
        raise SystemExit("Paper-scale protocol must preserve the 16 two-player target")
    if target["parallel_envs"] != 10 or target["rollout_steps"] != 1000:
        raise SystemExit("Paper-scale protocol must preserve 10 envs and 1000 rollout steps")
    if smoke_run["full_benchmark_executed"]:
        raise SystemExit("Smoke verifier must not execute the full benchmark")
    if not smoke_run["executed"]:
        raise SystemExit("Smoke verifier did not execute")
    if len(smoke_run["legality_smoke_games"]) < 3:
        raise SystemExit("Smoke verifier must cover multiple representative game adapters")

    print("paper-scale protocol smoke verified")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--status-report", type=Path)
    parser.add_argument("--run-full-benchmarks", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    main()
