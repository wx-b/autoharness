# Requirement coverage: REQ-001-bootstrap-002, REQ-001-bootstrap-004
from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from autoharness.artifacts.models import FailureBundle, RunSummary, StepRecord
from autoharness.artifacts.store import ArtifactStore
from autoharness.benchmarks.base import Benchmark
from autoharness.critics.deterministic import DeterministicCritic
from autoharness.providers.base import GenerationConfig, Provider
from autoharness.runtime.models import EpisodeResult
from autoharness.runtime.verifiers import assess_candidates, build_action_schema


def run_episode(
    *,
    benchmark: Benchmark,
    provider: Provider,
    retry_limit: int,
    artifact_root: Path,
    prompt_prefix: str = "Return only the action.",
    candidate_count: int = 1,
    temperature: float | None = None,
    top_p: float | None = None,
) -> EpisodeResult:
    benchmark.reset()
    store = ArtifactStore(artifact_root)
    critic = DeterministicCritic()
    run_id = os.getenv("AUTOHARNESS_RUN_ID") or uuid4().hex
    trace: list[StepRecord] = []
    retry_count = 0
    steps = 0
    final_action: str | None = None
    warning_context = ""
    legal_attempts = 0
    illegal_attempts = 0
    total_reward = 0.0

    while True:
        observation = benchmark.get_observation()
        legal_actions = benchmark.available_actions(observation)
        legal_action_taken = False
        for attempt_index in range(retry_limit + 1):
            prompt = f"{prompt_prefix}\n\n{warning_context}{observation}"
            generation_config = GenerationConfig(
                candidate_count=candidate_count,
                temperature=temperature,
                top_p=top_p,
                response_schema=build_action_schema(legal_actions),
            )
            if hasattr(provider, "generate_candidates"):
                candidates = provider.generate_candidates(prompt, generation_config)
            else:
                candidates = [provider.generate(prompt)]
            prior_actions = [record.action for record in trace if record.step_index == steps]
            assessments = assess_candidates(
                candidates=candidates,
                benchmark=benchmark,
                prior_actions=prior_actions,
                legal_actions=legal_actions,
            )
            selected = max(assessments, key=lambda assessment: assessment.total_score)
            generated = selected.provider_result
            action = selected.action
            legal = selected.legal
            trace.append(
                StepRecord(
                    step_index=steps,
                    attempt_index=attempt_index,
                    observation=observation,
                    action=action,
                    legal=legal,
                    provider=generated.provider,
                    metadata={
                        "selected_candidate_index": selected.index,
                        "verifier_scores": selected.verifier_scores,
                        "candidate_assessments": [
                            assessment.as_metadata() for assessment in assessments
                        ],
                    },
                )
            )
            final_action = action
            if legal:
                legal_attempts += 1
                outcome = benchmark.step(action)
                total_reward += outcome.reward
                steps += 1
                legal_action_taken = True
                if outcome.done:
                    trace_path = store.write_trace(trace)
                    total_attempts = legal_attempts + illegal_attempts
                    summary = RunSummary(
                        run_id=run_id,
                        status="passed",
                        steps=steps,
                        retry_count=retry_count,
                        provider=generated.provider,
                        benchmark=benchmark.kind,
                        legal_attempts=legal_attempts,
                        illegal_attempts=illegal_attempts,
                        legal_action_rate=(
                            legal_attempts / total_attempts if total_attempts else 0.0
                        ),
                        total_reward=total_reward,
                    )
                    summary.trace_path = str(trace_path)
                    summary_path = store.write_summary(summary)
                    summary.summary_path = str(summary_path)
                    store.write_summary(summary)
                    return EpisodeResult(
                        run_id=run_id,
                        status="passed",
                        retry_count=retry_count,
                        steps=steps,
                        final_action=final_action,
                        provider=generated.provider,
                        benchmark=benchmark.kind,
                        legal_attempts=legal_attempts,
                        illegal_attempts=illegal_attempts,
                        legal_action_rate=(
                            legal_attempts / total_attempts if total_attempts else 0.0
                        ),
                        total_reward=total_reward,
                    )
                warning_context = ""
                break
            illegal_attempts += 1
            retry_count += 1
            warning_context = (
                f"Previous action '{action}' was illegal. Return a legal action only.\n\n"
            )

        if not legal_action_taken:
            observation = benchmark.get_observation()
            attempts = [
                record.action for record in trace if record.step_index == steps
            ]
            failure_bundle = FailureBundle(
                run_id=run_id,
                reason="illegal-action-exhausted",
                observation=observation,
                attempts=attempts,
                current_legal_actions=benchmark.available_actions(observation) or [],
                prior_attempts_summary=[
                    {
                        "action": record.action,
                        "legal": record.legal,
                        "verifier_scores": record.metadata.get("verifier_scores", {}),
                    }
                    for record in trace
                    if record.step_index == steps
                ],
            )
            critic_summary = critic.summarize(failure_bundle)
            failure_bundle.failure_type = critic_summary.failure_type
            store.write_failure_bundle(failure_bundle)
            store.write_critic_summary(critic_summary)
            failed_summary = RunSummary(
                run_id=run_id,
                status="failed",
                steps=steps,
                retry_count=retry_count,
                provider=trace[-1].provider if trace else "unknown",
                benchmark=benchmark.kind,
                legal_attempts=legal_attempts,
                illegal_attempts=illegal_attempts,
                legal_action_rate=(
                    legal_attempts / (legal_attempts + illegal_attempts)
                    if (legal_attempts + illegal_attempts)
                    else 0.0
                ),
                total_reward=total_reward,
            )
            trace_path = store.write_trace(trace)
            failed_summary.trace_path = str(trace_path)
            summary_path = store.write_summary(failed_summary)
            failed_summary.summary_path = str(summary_path)
            store.write_summary(failed_summary)
            return EpisodeResult(
                run_id=run_id,
                status="failed",
                retry_count=retry_count,
                steps=steps,
                final_action=final_action,
                provider=failed_summary.provider,
                benchmark=benchmark.kind,
                legal_attempts=legal_attempts,
                illegal_attempts=illegal_attempts,
                legal_action_rate=failed_summary.legal_action_rate,
                total_reward=total_reward,
            )
