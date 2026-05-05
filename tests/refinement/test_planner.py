from autoharness.artifacts.models import FailureBundle
from autoharness.critics.deterministic import DeterministicCritic
from autoharness.providers.base import ProviderResult
from autoharness.refinement.planner import LLMPatchRefiner


def test_llm_patch_refiner_uses_critic_summary_in_prompt() -> None:
    prompts: list[str] = []

    class RecordingProvider:
        def generate(self, prompt: str) -> ProviderResult:
            prompts.append(prompt)
            return ProviderResult(
                text="Parse the final Available Moves block and emit exactly one move.",
                provider="fixture",
                model="fixture-model",
            )

    bundle = FailureBundle(
        run_id="run-1",
        reason="illegal-action-exhausted",
        observation="Available Moves: '[1]', '[2]'",
        attempts=["[8]", "[7]"],
        current_legal_actions=["[1]", "[2]"],
    )
    critic_summary = DeterministicCritic().summarize(bundle)

    plan = LLMPatchRefiner(provider=RecordingProvider()).plan(
        bundle=bundle,
        critic_summary=critic_summary,
    )

    assert prompts
    assert "illegal_not_in_set" in prompts[0]
    assert "[1]" in prompts[0]
    assert plan.summary == "Parse the final Available Moves block and emit exactly one move."
    assert plan.provider == "fixture"
