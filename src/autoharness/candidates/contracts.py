# Requirement coverage: REQ-001-bootstrap-001
from __future__ import annotations

import inspect
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType


class CandidateContractError(ValueError):
    """Raised when a candidate module does not satisfy the action-verifier contract."""


def load_candidate_module(path: Path) -> ModuleType:
    spec = spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise CandidateContractError(f"Could not load candidate module from {path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_action_verifier_module(module: ModuleType) -> None:
    _validate_function(module, "propose_action", ["board"])
    _validate_function(module, "is_legal_action", ["board", "action"])


def _validate_function(module: ModuleType, name: str, expected_args: list[str]) -> None:
    fn = getattr(module, name, None)
    if fn is None:
        raise CandidateContractError(f"Missing required function: {name}")
    signature = inspect.signature(fn)
    arg_names = list(signature.parameters.keys())
    if arg_names != expected_args:
        raise CandidateContractError(
            f"{name} must accept arguments {expected_args}, found {arg_names}"
        )
