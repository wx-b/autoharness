# Requirement coverage: REQ-001-bootstrap-001
from pathlib import Path

import pytest

from autoharness.candidates.contracts import (
    CandidateContractError,
    load_candidate_module,
    validate_action_verifier_module,
)

FIXTURE_DIR = Path("tests/fixtures/candidates")


def test_validate_action_verifier_module_accepts_valid_candidate() -> None:
    module = load_candidate_module(FIXTURE_DIR / "valid_candidate.py")
    validate_action_verifier_module(module)


def test_validate_action_verifier_module_rejects_invalid_signature() -> None:
    module = load_candidate_module(FIXTURE_DIR / "invalid_candidate.py")
    with pytest.raises(CandidateContractError):
        validate_action_verifier_module(module)
