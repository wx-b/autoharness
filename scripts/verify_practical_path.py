from __future__ import annotations

import json
from pathlib import Path

from autoharness.practical import generate_practical_path_evidence


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    artifact_root = repo / "docs" / "status" / "artifacts" / "practical-path"
    status_report = repo / "docs" / "status" / "autoharness_practical_path_evidence.md"
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
        evidence.status_report_path,
    ]
    missing = [path for path in required_paths if not Path(path).exists()]
    if missing:
        raise SystemExit(f"Missing practical-path artifacts: {missing}")

    sweep = json.loads(Path(evidence.textarena_sweep_path).read_text())
    if sweep["parallel_envs"] < 10 or sweep["rollout_steps"] < 1000:
        raise SystemExit("TextArena sweep config does not support required scale")

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

    print("practical path evidence verified")


if __name__ == "__main__":
    main()
