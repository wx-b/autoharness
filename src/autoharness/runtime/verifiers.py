from __future__ import annotations

# Requirement coverage:
# REQ-006-provider-backed-probe-cost-auth-policy-012
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from autoharness.benchmarks.base import Benchmark
from autoharness.providers.base import ProviderResult


@dataclass(slots=True)
class CandidateAssessment:
    index: int
    provider_result: ProviderResult
    action: str
    legal: bool
    verifier_scores: dict[str, float]
    total_score: float

    def as_metadata(self) -> dict[str, object]:
        return {
            "candidate_index": self.index,
            "action": self.action,
            "legal": self.legal,
            "provider_metadata": self.provider_result.metadata,
            "verifier_scores": self.verifier_scores,
            "total_score": self.total_score,
        }


def build_action_schema(legal_actions: Sequence[str] | None) -> dict[str, object] | None:
    if not legal_actions:
        return None
    return {
        "type": "object",
        "properties": {
            "move": {"type": "string", "enum": list(legal_actions)},
        },
        "required": ["move"],
    }


def extract_action_text(
    result: ProviderResult,
    legal_actions: Sequence[str] | None = None,
) -> str:
    parsed_response = result.metadata.get("parsed_response")
    if isinstance(parsed_response, Mapping):
        move = parsed_response.get("move")
        if isinstance(move, str):
            return _normalize_embedded_legal_action(move.strip(), legal_actions)
    text = result.text.strip()
    if not text:
        return ""
    if text.startswith("{"):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return text
        if isinstance(payload, Mapping):
            move = payload.get("move")
            if isinstance(move, str):
                return _normalize_embedded_legal_action(move.strip(), legal_actions)
    return _normalize_embedded_legal_action(text, legal_actions)


def _normalize_embedded_legal_action(
    action: str,
    legal_actions: Sequence[str] | None,
) -> str:
    if not action or not legal_actions or action in legal_actions:
        return action
    role_prefixed = re.fullmatch(r"\[[A-Za-z][A-Za-z0-9 _-]*\]\s+(?P<move>.+)", action)
    if role_prefixed is None:
        return action
    move = role_prefixed.group("move").strip()
    matches = [legal_action for legal_action in legal_actions if legal_action == move]
    if len(matches) == 1:
        return move
    return action


def assess_candidates(
    *,
    candidates: Sequence[ProviderResult],
    benchmark: Benchmark,
    prior_actions: Sequence[str],
    legal_actions: Sequence[str] | None,
) -> list[CandidateAssessment]:
    legal_action_set = set(legal_actions or [])
    prior_action_set = {action.strip() for action in prior_actions}
    assessments: list[CandidateAssessment] = []
    for index, candidate in enumerate(candidates):
        action = extract_action_text(candidate, legal_actions)
        format_score = 1.0 if action else 0.0
        benchmark_legal = benchmark.is_legal(action) if action else False
        candidate_legal_flag = candidate.metadata.get("candidate_legal")
        candidate_legal = candidate_legal_flag if isinstance(candidate_legal_flag, bool) else True
        legality_score = 1.0 if benchmark_legal and candidate_legal else 0.0
        state_score = 1.0 if not legal_action_set or action in legal_action_set else 0.0
        repeat_score = 0.0 if action in prior_action_set else 1.0
        total_score = (
            0.15 * format_score
            + 0.55 * legality_score
            + 0.20 * state_score
            + 0.10 * repeat_score
        )
        verifier_scores = {
            "format": format_score,
            "legality": legality_score,
            "state_consistency": state_score,
            "repeat_penalty": repeat_score,
        }
        assessments.append(
            CandidateAssessment(
                index=index,
                provider_result=candidate,
                action=action,
                legal=bool(format_score and legality_score and state_score),
                verifier_scores=verifier_scores,
                total_score=total_score,
            )
        )
    return assessments
