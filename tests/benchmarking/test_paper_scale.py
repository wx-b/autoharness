from __future__ import annotations

import json
from pathlib import Path

from autoharness.benchmarking.paper_scale import write_paper_scale_protocol_evidence


def test_paper_scale_protocol_smoke_preserves_deferred_targets(tmp_path: Path) -> None:
    evidence = write_paper_scale_protocol_evidence(
        artifact_root=tmp_path / "paper-scale",
        status_report_path=tmp_path / "paper-scale.md",
    )

    protocol = json.loads(Path(evidence.protocol_path).read_text())
    summary = json.loads(Path(evidence.smoke_summary_path).read_text())
    status_report = Path(evidence.status_report_path).read_text()

    assert protocol["issue_id"] == "PYL-632"
    assert protocol["status"] == "smoke_verified_full_run_deferred"
    assert protocol["target"]["legality_game_count"] == 145
    assert protocol["target"]["end_to_end_one_player_games"] == 16
    assert protocol["target"]["end_to_end_two_player_games"] == 16
    assert protocol["target"]["parallel_envs"] == 10
    assert protocol["target"]["rollout_steps"] == 1000
    assert protocol["smoke_run"]["executed"] is True
    assert protocol["smoke_run"]["full_benchmark_executed"] is False
    assert "Othello-v0" in protocol["smoke_run"]["legality_smoke_games"]
    assert summary["full_benchmark_executed"] is False
    assert evidence.full_benchmark_executed is False
    assert "PYL-632" in status_report
    assert "full paper-scale benchmark did not run" in status_report
