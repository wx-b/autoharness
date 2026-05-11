from __future__ import annotations

from pathlib import Path

import pytest

from autoharness.candidates.contracts import CandidateContractError
from autoharness.candidates.registry import CandidateRegistry


def test_registry_promote_list_show_load_export_hash_and_provenance(tmp_path: Path) -> None:
    source = tmp_path / "candidate.py"
    source.write_text(
        "def propose_action(board):\n"
        "    return '[0]'\n\n"
        "def is_legal_action(board, action):\n"
        "    return action == '[0]'\n"
    )
    registry = CandidateRegistry(tmp_path / "registry")

    first = registry.promote(
        source,
        candidate_id="candidate-a",
        provenance={"run_id": "tmp-run"},
        minimum_metrics={"legal_action_rate": 1.0},
    )
    second = registry.promote(source, candidate_id="candidate-a")

    assert first == second
    assert registry.hash(source) == first.source_sha256
    assert registry.list()[0].candidate_id == "candidate-a"
    assert registry.show("candidate-a") == first
    assert registry.provenance("candidate-a")["run_id"] == "tmp-run"
    assert registry.load("candidate-a").propose_action("board") == "[0]"
    export_path = registry.export(tmp_path / "exported-registry.json")
    assert "candidate-a" in export_path.read_text()


def test_registry_rejects_malformed_candidate(tmp_path: Path) -> None:
    source = tmp_path / "bad.py"
    source.write_text("def helper():\n    return None\n")
    registry = CandidateRegistry(tmp_path / "registry")

    with pytest.raises(CandidateContractError):
        registry.promote(source)
