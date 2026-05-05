# Requirement coverage: REQ-001-bootstrap-002
from __future__ import annotations

import hashlib
from pathlib import Path

from pydantic import BaseModel

from autoharness.artifacts.models import (
    FailureBundle,
    FailureType,
    RefinementSummary,
    SearchTraceRecord,
)
from autoharness.artifacts.store import ArtifactStore
from autoharness.benchmarks.base import Benchmark
from autoharness.critics.deterministic import DeterministicCritic
from autoharness.providers.base import Provider
from autoharness.providers.candidate import CandidateModuleProvider
from autoharness.refinement.mutator import DeterministicPatchMutator
from autoharness.refinement.planner import LLMPatchRefiner, PatchPlan
from autoharness.runtime.loop import run_episode
from autoharness.runtime.models import EpisodeResult
from autoharness.search.controller import BetaThompsonController
from autoharness.search.models import SearchNode


class FixtureRefinementResult(BaseModel):
    status: str
    iterations_attempted: int
    final_candidate_path: str
    final_episode: EpisodeResult
    search_trace_path: str
    refinement_summary_path: str


class FixtureRefinementRunner:
    def __init__(
        self,
        *,
        critic: DeterministicCritic | None = None,
        mutator: DeterministicPatchMutator | None = None,
        search_controller: BetaThompsonController | None = None,
    ) -> None:
        self.critic = critic or DeterministicCritic()
        self.mutator = mutator or DeterministicPatchMutator()
        self.search_controller = search_controller or BetaThompsonController(seed=0)

    def run(
        self,
        *,
        candidate_path: Path,
        benchmark: Benchmark,
        patch_provider: Provider,
        artifact_root: Path,
        retry_limit: int,
        max_iterations: int = 1,
        prompt_prefix: str = "Return only the action.",
    ) -> FixtureRefinementResult:
        root_store = ArtifactStore(artifact_root)
        refiner = LLMPatchRefiner(provider=patch_provider)
        search_trace: list[SearchTraceRecord] = []
        current_candidate_path = candidate_path
        current_patch_plan: PatchPlan | None = None
        last_failure_type: FailureType | None = None

        for iteration in range(max_iterations + 1):
            iteration_root = artifact_root / f"iteration-{iteration:02d}"
            provider = CandidateModuleProvider(path=current_candidate_path)
            episode = run_episode(
                benchmark=benchmark,
                provider=provider,
                retry_limit=retry_limit,
                artifact_root=iteration_root,
                prompt_prefix=prompt_prefix,
            )
            source = current_candidate_path.read_text()
            node = self.search_controller.record_result(
                node=SearchNode(
                    node_id=f"candidate-{iteration:02d}",
                    candidate_hash=_hash_source(source),
                    parent_id=f"candidate-{iteration - 1:02d}" if iteration > 0 else None,
                ),
                legal_actions=episode.legal_attempts,
                illegal_actions=episode.illegal_attempts,
            )
            search_trace.append(
                SearchTraceRecord(
                    iteration=iteration,
                    node_id=node.node_id,
                    parent_id=node.parent_id,
                    candidate_path=str(current_candidate_path),
                    candidate_hash=node.candidate_hash,
                    status="passed" if episode.status == "passed" else "failed",
                    legal_actions=episode.legal_attempts,
                    illegal_actions=episode.illegal_attempts,
                    legal_action_rate=episode.legal_action_rate,
                    total_reward=episode.total_reward,
                    selected_for_refinement=(
                        episode.status == "failed" and iteration < max_iterations
                    ),
                    patch_plan_summary=(
                        current_patch_plan.summary if current_patch_plan is not None else None
                    ),
                )
            )
            if episode.status == "passed":
                return self._finish(
                    root_store=root_store,
                    artifact_root=artifact_root,
                    status="converged",
                    iterations_attempted=iteration,
                    candidate_path=candidate_path,
                    final_candidate_path=current_candidate_path,
                    final_episode=episode,
                    failure_type=last_failure_type,
                    patch_plan=current_patch_plan,
                    search_trace=search_trace,
                )
            if iteration == max_iterations:
                return self._finish(
                    root_store=root_store,
                    artifact_root=artifact_root,
                    status="failed",
                    iterations_attempted=iteration,
                    candidate_path=candidate_path,
                    final_candidate_path=current_candidate_path,
                    final_episode=episode,
                    failure_type=last_failure_type,
                    patch_plan=current_patch_plan,
                    search_trace=search_trace,
                )

            failure_bundle = FailureBundle.model_validate_json(
                (iteration_root / "failure-bundle.json").read_text()
            )
            critic_summary = self.critic.summarize(failure_bundle)
            current_patch_plan = refiner.plan(
                bundle=failure_bundle,
                critic_summary=critic_summary,
            )
            last_failure_type = critic_summary.failure_type
            mutated_source = self.mutator.mutate(
                source=source,
                critic_summary=critic_summary,
                patch_plan_summary=current_patch_plan.summary,
            )
            current_candidate_path = (
                artifact_root / f"iteration-{iteration + 1:02d}" / "candidate.py"
            )
            current_candidate_path.parent.mkdir(parents=True, exist_ok=True)
            current_candidate_path.write_text(mutated_source)

        raise RuntimeError("refinement loop terminated without producing a final episode")

    def _finish(
        self,
        *,
        root_store: ArtifactStore,
        artifact_root: Path,
        status: str,
        iterations_attempted: int,
        candidate_path: Path,
        final_candidate_path: Path,
        final_episode: EpisodeResult,
        failure_type: FailureType | None,
        patch_plan: PatchPlan | None,
        search_trace: list[SearchTraceRecord],
    ) -> FixtureRefinementResult:
        search_trace_path = root_store.write_search_trace(search_trace)
        refinement_summary = RefinementSummary(
            status="converged" if status == "converged" else "failed",
            iterations_attempted=iterations_attempted,
            initial_candidate_path=str(candidate_path),
            final_candidate_path=str(final_candidate_path),
            final_run_id=final_episode.run_id,
            failure_type=failure_type,
            patch_plan_summary=patch_plan.summary if patch_plan is not None else None,
            search_trace_path=str(search_trace_path),
        )
        summary_path = root_store.write_refinement_summary(refinement_summary)
        return FixtureRefinementResult(
            status=status,
            iterations_attempted=iterations_attempted,
            final_candidate_path=str(final_candidate_path),
            final_episode=final_episode,
            search_trace_path=str(search_trace_path),
            refinement_summary_path=str(summary_path),
        )


def _hash_source(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()
