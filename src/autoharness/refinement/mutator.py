from __future__ import annotations

from autoharness.artifacts.models import CriticSummary

LATEST_AVAILABLE_MOVES_RULE = "latest_available_moves"
_SEARCH_PATTERN = 'match = re.search(r"Available Moves:\\s*(.*)", board)'
_TOKEN_PATTERN = 'tokens = re.findall(r"\\[[^\\]]+\\]", match.group(1))'
_REPLACEMENT = "\n".join(
    [
        'matches = re.findall(r"Available Moves:\\s*(.*)", board)',
        "    if not matches:",
        '        return "[0]"',
        '    tokens = re.findall(r"\\[[^\\]]+\\]", matches[-1])',
    ]
)


class DeterministicPatchMutator:
    def select_rule_name(
        self,
        *,
        critic_summary: CriticSummary,
        patch_plan_summary: str,
    ) -> str:
        lowered_plan = patch_plan_summary.lower()
        if self._should_use_latest_moves_rule(
            critic_summary=critic_summary,
            lowered_plan=lowered_plan,
        ):
            return LATEST_AVAILABLE_MOVES_RULE
        raise ValueError("No deterministic mutation rule matched the patch plan and source")

    def mutate(
        self,
        *,
        source: str,
        critic_summary: CriticSummary,
        patch_plan_summary: str,
    ) -> str:
        rule_name = self.select_rule_name(
            critic_summary=critic_summary,
            patch_plan_summary=patch_plan_summary,
        )
        if rule_name == LATEST_AVAILABLE_MOVES_RULE:
            return self._apply_latest_moves_rule(source)
        raise ValueError("No deterministic mutation rule matched the patch plan and source")

    def _should_use_latest_moves_rule(
        self,
        *,
        critic_summary: CriticSummary,
        lowered_plan: str,
    ) -> bool:
        allowed_failure_types = {"illegal_not_in_set", "repeated_invalid"}
        if critic_summary.failure_type not in allowed_failure_types:
            return False
        keywords = (
            "final available moves",
            "latest legal action set",
            "latest available moves",
            "final move list",
        )
        return any(keyword in lowered_plan for keyword in keywords) or (
            "latest legal action set" in critic_summary.recommended_change.lower()
        )

    def _apply_latest_moves_rule(self, source: str) -> str:
        if _SEARCH_PATTERN not in source or _TOKEN_PATTERN not in source:
            raise ValueError("No deterministic mutation rule matched the patch plan and source")
        return source.replace(
            "\n".join(
                [
                    _SEARCH_PATTERN,
                    "    if match is None:",
                    '        return "[0]"',
                    f"    {_TOKEN_PATTERN}",
                ]
            ),
            _REPLACEMENT,
        )
