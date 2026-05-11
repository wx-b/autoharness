from __future__ import annotations

import argparse
import json
from pathlib import Path

from autoharness.practical import generate_practical_path_evidence


def main() -> None:
    args = _parse_args()
    repo = Path(__file__).resolve().parents[1]
    artifact_root = (
        args.artifact_root or repo / "docs" / "status" / "artifacts" / "practical-path"
    )
    status_report = (
        args.status_report
        or repo / "docs" / "status" / "autoharness_practical_path_evidence.md"
    )
    candidate = repo / "tests" / "fixtures" / "candidates" / "ttt_first_available.py"
    evidence = generate_practical_path_evidence(
        artifact_root=artifact_root,
        status_report_path=status_report,
        candidate_path=candidate,
    )

    required_paths = [
        evidence.candidate_registry_path,
        evidence.signatures_path,
        evidence.search_tree_path,
        evidence.critic_refiner_path,
        evidence.sandbox_audit_path,
        evidence.textarena_sweep_path,
        evidence.benchmark_report_path,
        evidence.non_game_domain_path,
        evidence.mutation_artifact_path,
        evidence.completion_report_path,
        evidence.status_report_path,
    ]
    missing = [path for path in required_paths if not Path(path).exists()]
    if missing:
        raise SystemExit(f"Missing practical-path artifacts: {missing}")

    registry = json.loads(Path(evidence.candidate_registry_path).read_text())
    candidates = registry.get("candidates", [])
    if not candidates or not candidates[0].get("provenance"):
        raise SystemExit("Candidate registry did not promote a generated candidate")

    signatures = json.loads(Path(evidence.signatures_path).read_text())
    if not signatures or "parse_state" not in signatures[0].get("rich_entrypoints", []):
        raise SystemExit("Rich candidate signature adapter was not used")

    search_tree = json.loads(Path(evidence.search_tree_path).read_text())
    if len(search_tree) < 5:
        raise SystemExit("Runtime search tree must contain at least 5 nodes")
    if not all(node.get("recomputable_metrics") for node in search_tree):
        raise SystemExit("Search tree nodes must expose recomputable metrics")

    mutation = json.loads(Path(evidence.mutation_artifact_path).read_text())
    if mutation["precheck_result"]["status"] != "passed":
        raise SystemExit("Mutated candidate did not pass sandbox precheck")

    sweep = json.loads(Path(evidence.textarena_sweep_path).read_text())
    if sweep["parallel_envs"] < 10 or sweep["rollout_steps"] < 1000:
        raise SystemExit("TextArena sweep config does not support required scale")
    if not sweep["verified_small_run"]["executed"]:
        raise SystemExit("TextArena small POC run was not executed")

    sandbox = json.loads(Path(evidence.sandbox_audit_path).read_text())
    required_cases = {
        "env_read",
        "filesystem_write",
        "subprocess",
        "network",
        "infinite_loop",
        "memory_output_abuse",
    }
    if required_cases - set(sandbox["adversarial_cases"]):
        raise SystemExit("Sandbox adversarial coverage incomplete")
    if sandbox["allowed_candidate"]["status"] != "passed":
        raise SystemExit("Sandbox did not execute the allowed generated candidate")

    benchmark = json.loads(Path(evidence.benchmark_report_path).read_text())
    if not benchmark.get("swapped_order_2p_poc"):
        raise SystemExit("Benchmark did not run swapped-order 2P POC")

    non_game = json.loads(Path(evidence.non_game_domain_path).read_text())
    if "synthetic_profit" not in non_game.get("objective_metrics", []):
        raise SystemExit("Non-game domain evaluator did not include synthetic profit objective")

    completion = json.loads(Path(evidence.completion_report_path).read_text())
    if completion["status"] != "small_scale_runtime_complete":
        raise SystemExit("Completion report did not mark small-scale runtime completion")
    if completion["static_artifact_only"]:
        raise SystemExit("Completion report still allows static artifact completion")

    print("practical path runtime verified")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--status-report", type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    main()
