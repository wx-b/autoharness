from __future__ import annotations

from pydantic import BaseModel

from autoharness.artifacts.models import CriticSummary, FailureBundle
from autoharness.providers.base import Provider


class PatchPlan(BaseModel):
    summary: str
    prompt: str
    provider: str
    model: str


class LLMPatchRefiner:
    def __init__(self, *, provider: Provider) -> None:
        self.provider = provider

    def build_prompt(self, *, bundle: FailureBundle, critic_summary: CriticSummary) -> str:
        legal_actions = ", ".join(critic_summary.current_legal_actions) or "none"
        attempts = ", ".join(bundle.attempts) or "none"
        return "\n".join(
            [
                "You are planning the next patch for an action-verifier candidate.",
                f"Failure type: {critic_summary.failure_type}",
                f"Root cause: {critic_summary.root_cause}",
                f"Current legal actions: {legal_actions}",
                f"Failed attempts: {attempts}",
                "Return a concise patch plan that fixes the observed failure.",
            ]
        )

    def plan(self, *, bundle: FailureBundle, critic_summary: CriticSummary) -> PatchPlan:
        prompt = self.build_prompt(bundle=bundle, critic_summary=critic_summary)
        result = self.provider.generate(prompt)
        return PatchPlan(
            summary=result.text.strip(),
            prompt=prompt,
            provider=result.provider,
            model=result.model,
        )
