# Requirement coverage: REQ-001-bootstrap-001
from __future__ import annotations

import inspect
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

from pydantic import BaseModel, Field


class CandidateContractError(ValueError):
    """Raised when a candidate module does not satisfy the action-verifier contract."""


class CandidateSignature(BaseModel):
    contract_version: str = "2"
    candidate_id: str
    path: str
    source_sha256: str
    domain: str = "textarena"
    entrypoints: list[str] = Field(default_factory=list)
    compatible_entrypoint: str = "propose_action"
    rich_entrypoints: list[str] = Field(default_factory=list)
    supports_legacy_action_verifier: bool = False
    accepted_observation_shapes: list[str] = Field(default_factory=list)
    output_contract: str = "single legal action string"


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


def validate_candidate_contract(module: ModuleType) -> None:
    _validate_one_arg(module, "propose_action")
    has_rich_contract = all(
        hasattr(module, name) for name in ["parse_state", "legal_actions", "score_action"]
    )
    has_legacy_contract = hasattr(module, "is_legal_action")
    if not has_rich_contract and not has_legacy_contract:
        raise CandidateContractError(
            "Candidate must expose rich parse_state/legal_actions/score_action "
            "or legacy is_legal_action"
        )
    if hasattr(module, "parse_state"):
        _validate_one_arg(module, "parse_state")
    if hasattr(module, "legal_actions"):
        _validate_one_arg(module, "legal_actions")
    if hasattr(module, "score_action"):
        _validate_function_arity(module, "score_action", 2)
    if hasattr(module, "explain_decision"):
        _validate_function_arity(module, "explain_decision", 2)
    if hasattr(module, "is_legal_action"):
        _validate_function_arity(module, "is_legal_action", 2)


def build_candidate_signature(
    *,
    module: ModuleType,
    candidate_id: str,
    path: Path,
    source_sha256: str,
    domain: str = "textarena",
) -> CandidateSignature:
    validate_candidate_contract(module)
    entrypoints = [
        name
        for name, value in vars(module).items()
        if callable(value) and not name.startswith("_")
    ]
    rich_entrypoints = [
        name
        for name in [
            "parse_state",
            "legal_actions",
            "score_action",
            "propose_action",
            "explain_decision",
            "update_memory",
        ]
        if hasattr(module, name)
    ]
    return CandidateSignature(
        candidate_id=candidate_id,
        path=str(path),
        source_sha256=source_sha256,
        domain=domain,
        entrypoints=sorted(entrypoints),
        rich_entrypoints=rich_entrypoints,
        supports_legacy_action_verifier=hasattr(module, "is_legal_action"),
        accepted_observation_shapes=[
            "TextArena observation with Available Moves/Legal Actions",
            "fixture observation with explicit valid_actions",
            "non-game observation dictionaries with constraints and metrics",
        ],
    )


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


def _validate_one_arg(module: ModuleType, name: str) -> None:
    _validate_function_arity(module, name, 1)


def _validate_function_arity(module: ModuleType, name: str, expected_arity: int) -> None:
    fn = getattr(module, name, None)
    if fn is None:
        raise CandidateContractError(f"Missing required function: {name}")
    signature = inspect.signature(fn)
    parameters = list(signature.parameters.values())
    required_or_positional = [
        parameter
        for parameter in parameters
        if parameter.kind
        in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        )
        and parameter.default is inspect.Parameter.empty
    ]
    if len(required_or_positional) != expected_arity:
        arg_names = [parameter.name for parameter in parameters]
        raise CandidateContractError(
            f"{name} must accept {expected_arity} required arguments, found {arg_names}"
        )
