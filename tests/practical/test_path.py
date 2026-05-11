from __future__ import annotations

import json
from pathlib import Path
from typing import get_args

from autoharness.practical import FailureTaxonomy, generate_practical_path_evidence


def test_practical_path_evidence_covers_required_contracts(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.py"
    candidate.write_text(
        "def propose_action(observation: str) -> str:\n"
        "    return observation.splitlines()[0]\n"
    )

    evidence = generate_practical_path_evidence(
        artifact_root=tmp_path / "artifacts",
        status_report_path=tmp_path / "status.md",
        candidate_path=candidate,
    )

    registry = json.loads(Path(evidence.candidate_registry_path).read_text())
    signatures = json.loads(Path(evidence.signatures_path).read_text())
    search_tree = json.loads(Path(evidence.search_tree_path).read_text())
    critic_refiner = json.loads(Path(evidence.critic_refiner_path).read_text())
    sandbox = json.loads(Path(evidence.sandbox_audit_path).read_text())
    sweep = json.loads(Path(evidence.textarena_sweep_path).read_text())
    benchmark = json.loads(Path(evidence.benchmark_report_path).read_text())
    non_game = json.loads(Path(evidence.non_game_domain_path).read_text())
    mutation = json.loads(Path(evidence.mutation_artifact_path).read_text())
    completion = json.loads(Path(evidence.completion_report_path).read_text())

    assert registry["registry_version"] == "1"
    assert registry["candidates"][0]["provenance"]["source_kind"] == "runtime_generated_mutation"
    assert "parse_state" in signatures[0]["rich_entrypoints"]
    assert len(search_tree) >= 5
    assert search_tree[1]["parent_id"] == "root"
    assert set(critic_refiner["failure_taxonomy"]) == set(get_args(FailureTaxonomy))
    assert mutation["precheck_result"]["status"] == "passed"
    assert sandbox["allowed_candidate"]["status"] == "passed"
    assert sandbox["adversarial_cases"]["network"] == "denied"
    assert sweep["parallel_envs"] == 10
    assert sweep["rollout_steps"] == 1000
    assert sweep["verified_small_run"]["executed"] is True
    assert benchmark["swapped_order_2p_poc"] is True
    assert "synthetic_profit" in non_game["objective_metrics"]
    assert completion["status"] == "small_scale_runtime_complete"
    assert completion["static_artifact_only"] is False
    assert "PYL-618" in Path(evidence.status_report_path).read_text()
