# Requirement coverage: REQ-001-bootstrap-001
from pathlib import Path

import pytest

from autoharness.candidates.contracts import (
    CandidateContractError,
    build_candidate_signature,
    load_candidate_module,
    validate_action_verifier_module,
    validate_candidate_contract,
)

FIXTURE_DIR = Path("tests/fixtures/candidates")


def test_validate_action_verifier_module_accepts_valid_candidate() -> None:
    module = load_candidate_module(FIXTURE_DIR / "valid_candidate.py")
    validate_action_verifier_module(module)


def test_validate_action_verifier_module_rejects_invalid_signature() -> None:
    module = load_candidate_module(FIXTURE_DIR / "invalid_candidate.py")
    with pytest.raises(CandidateContractError):
        validate_action_verifier_module(module)


def test_validate_candidate_contract_accepts_rich_signature(tmp_path: Path) -> None:
    candidate = tmp_path / "rich.py"
    candidate.write_text(
        "def parse_state(board):\n"
        "    return {'actions': ['[0]']}\n\n"
        "def legal_actions(state):\n"
        "    return state['actions']\n\n"
        "def score_action(state, action):\n"
        "    return 1.0 if action in state['actions'] else -1.0\n\n"
        "def propose_action(board):\n"
        "    return '[0]'\n"
    )
    module = load_candidate_module(candidate)

    validate_candidate_contract(module)
    signature = build_candidate_signature(
        module=module,
        candidate_id="rich",
        path=candidate,
        source_sha256="abc",
    )

    assert signature.contract_version == "2"
    assert "parse_state" in signature.rich_entrypoints
    assert signature.supports_legacy_action_verifier is False
