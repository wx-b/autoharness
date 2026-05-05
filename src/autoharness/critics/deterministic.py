# Requirement coverage: REQ-001-bootstrap-004
from __future__ import annotations

from autoharness.artifacts.models import CriticSummary, FailureBundle, FailureType


class DeterministicCritic:
    def summarize(self, bundle: FailureBundle) -> CriticSummary:
        failure_type = bundle.failure_type or self._classify(bundle)
        root_cause, recommended_change = self._describe(failure_type)
        return CriticSummary(
            run_id=bundle.run_id,
            failure_type=failure_type,
            root_cause=root_cause,
            current_legal_actions=list(bundle.current_legal_actions),
            attempts=list(bundle.attempts),
            recommended_change=recommended_change,
        )

    def _classify(self, bundle: FailureBundle) -> FailureType:
        stripped_attempts = [attempt.strip() for attempt in bundle.attempts]
        if any(not attempt for attempt in stripped_attempts):
            return "format_error"
        if stripped_attempts and len(set(stripped_attempts)) == 1 and len(stripped_attempts) > 1:
            return "repeated_invalid"
        legal_actions = set(bundle.current_legal_actions)
        if legal_actions and all(attempt not in legal_actions for attempt in stripped_attempts):
            return "illegal_not_in_set"
        return "illegal_state_conflict"

    def _describe(self, failure_type: FailureType) -> tuple[str, str]:
        if failure_type == "format_error":
            return (
                "Candidate produced an empty or whitespace-only action instead of a valid move.",
                "Ensure action generation always returns a non-empty move string before emitting.",
            )
        if failure_type == "repeated_invalid":
            return (
                "Candidate repeated the same illegal action instead of adapting to "
                "benchmark feedback.",
                "Consume the retry warning and re-parse the current legal action "
                "set before retrying.",
            )
        if failure_type == "illegal_not_in_set":
            return (
                "Candidate emitted an action outside the latest legal action set "
                "exposed by the benchmark.",
                "Parse the latest legal action set from the observation and emit "
                "exactly one listed move.",
            )
        return (
            "Candidate action did not match the benchmark state implied by the "
            "current observation.",
            "Validate benchmark-state assumptions before emitting an action and "
            "fall back to the current legal action set.",
        )
