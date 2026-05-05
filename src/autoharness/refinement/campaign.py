# Requirement coverage:
# REQ-002-suite-refinement-002, REQ-002-suite-refinement-003, REQ-002-suite-refinement-004
from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel

from autoharness.artifacts.models import (
    CampaignStopReason,
    CampaignSummary,
    CandidateLineageRecord,
    FailureBundle,
    SuiteSummary,
)
from autoharness.artifacts.store import ArtifactStore
from autoharness.benchmarks.fixtures import FixtureCase
from autoharness.critics.deterministic import DeterministicCritic
from autoharness.providers.base import Provider
from autoharness.providers.candidate import CandidateModuleProvider
from autoharness.refinement.mutator import DeterministicPatchMutator
from autoharness.refinement.planner import LLMPatchRefiner
from autoharness.runtime.suites import run_fixture_suite
from autoharness.search.controller import BestFirstProgramSearchController
from autoharness.search.models import SearchNode


class SuiteRefinementCampaignResult(BaseModel):
    status: str
    stop_reason: CampaignStopReason
    iterations_attempted: int
    final_candidate_path: str
    final_candidate_hash: str
    final_suite_summary: SuiteSummary
    holdout_suite_summary: SuiteSummary | None = None
    candidate_lineage_path: str
    campaign_summary_path: str


class SuiteRefinementCampaignRunner:
    def __init__(
        self,
        *,
        critic: DeterministicCritic | None = None,
        mutator: DeterministicPatchMutator | None = None,
        search_controller: BestFirstProgramSearchController | None = None,
    ) -> None:
        self.critic = critic or DeterministicCritic()
        self.mutator = mutator or DeterministicPatchMutator()
        self.search_controller = search_controller or BestFirstProgramSearchController()

    def run(
        self,
        *,
        suite_id: str,
        candidate_path: Path,
        cases: list[FixtureCase],
        patch_provider: Provider,
        artifact_root: Path,
        retry_limit: int,
        max_iterations: int = 1,
        prompt_prefix: str = "Return only the action.",
        holdout_cases: list[FixtureCase] | None = None,
        minimum_holdout_legal_action_rate: float | None = None,
    ) -> SuiteRefinementCampaignResult:
        root_store = ArtifactStore(artifact_root)
        refiner = LLMPatchRefiner(provider=patch_provider)
        lineage: list[CandidateLineageRecord] = []
        current_candidate_path = candidate_path
        best_score = float("-inf")
        parent_candidate_hash: str | None = None

        for iteration in range(max_iterations + 1):
            iteration_root = artifact_root / f"iteration-{iteration:02d}"
            candidate_provider_path = current_candidate_path

            def build_provider(
                case: FixtureCase,
                path: Path = candidate_provider_path,
            ) -> CandidateModuleProvider:
                del case
                return CandidateModuleProvider(path=path)

            suite_summary = run_fixture_suite(
                suite_id=suite_id,
                cases=cases,
                provider_factory=build_provider,
                retry_limit=retry_limit,
                artifact_root=iteration_root,
                prompt_prefix=prompt_prefix,
            )
            source = current_candidate_path.read_text()
            candidate_hash = _hash_source(source)
            ranking_score = self._score_candidate(
                iteration=iteration,
                parent_candidate_hash=parent_candidate_hash,
                candidate_hash=candidate_hash,
                suite_summary=suite_summary,
            )
            case_ids = [case.case_id for case in suite_summary.cases]
            failed_case_ids = [
                case.case_id for case in suite_summary.cases if case.status == "failed"
            ]

            if suite_summary.status == "passed":
                lineage.append(
                    CandidateLineageRecord(
                        iteration=iteration,
                        candidate_path=str(current_candidate_path),
                        candidate_hash=candidate_hash,
                        parent_candidate_hash=parent_candidate_hash,
                        suite_artifact_root=str(iteration_root),
                        suite_summary_path=suite_summary.summary_path,
                        status="passed",
                        ranking_score=ranking_score,
                        case_ids=case_ids,
                        failed_case_ids=failed_case_ids,
                        stop_reason="converged",
                        legal_action_rate=suite_summary.legal_action_rate,
                        total_reward=suite_summary.total_reward,
                    )
                )
                return self._finish_with_optional_holdout(
                    root_store=root_store,
                    suite_id=suite_id,
                    status="converged",
                    stop_reason="converged",
                    iterations_attempted=iteration,
                    initial_candidate_path=candidate_path,
                    final_candidate_path=current_candidate_path,
                    final_candidate_hash=candidate_hash,
                    final_suite_summary=suite_summary,
                    holdout_cases=holdout_cases,
                    minimum_holdout_legal_action_rate=minimum_holdout_legal_action_rate,
                    provider_builder=build_provider,
                    retry_limit=retry_limit,
                    prompt_prefix=prompt_prefix,
                    artifact_root=artifact_root,
                    lineage=lineage,
                )

            if iteration > 0 and ranking_score <= best_score:
                lineage.append(
                    CandidateLineageRecord(
                        iteration=iteration,
                        candidate_path=str(current_candidate_path),
                        candidate_hash=candidate_hash,
                        parent_candidate_hash=parent_candidate_hash,
                        suite_artifact_root=str(iteration_root),
                        suite_summary_path=suite_summary.summary_path,
                        status="failed",
                        ranking_score=ranking_score,
                        case_ids=case_ids,
                        failed_case_ids=failed_case_ids,
                        stop_reason="no_improvement",
                        legal_action_rate=suite_summary.legal_action_rate,
                        total_reward=suite_summary.total_reward,
                    )
                )
                return self._finish(
                    root_store=root_store,
                    status="failed",
                    stop_reason="no_improvement",
                    iterations_attempted=iteration,
                    initial_candidate_path=candidate_path,
                    final_candidate_path=current_candidate_path,
                    final_candidate_hash=candidate_hash,
                    final_suite_summary=suite_summary,
                    holdout_suite_summary=None,
                    holdout_gate_passed=None,
                    lineage=lineage,
                )

            if iteration == max_iterations:
                lineage.append(
                    CandidateLineageRecord(
                        iteration=iteration,
                        candidate_path=str(current_candidate_path),
                        candidate_hash=candidate_hash,
                        parent_candidate_hash=parent_candidate_hash,
                        suite_artifact_root=str(iteration_root),
                        suite_summary_path=suite_summary.summary_path,
                        status="failed",
                        ranking_score=ranking_score,
                        case_ids=case_ids,
                        failed_case_ids=failed_case_ids,
                        stop_reason="budget_exhausted",
                        legal_action_rate=suite_summary.legal_action_rate,
                        total_reward=suite_summary.total_reward,
                    )
                )
                return self._finish(
                    root_store=root_store,
                    status="failed",
                    stop_reason="budget_exhausted",
                    iterations_attempted=iteration,
                    initial_candidate_path=candidate_path,
                    final_candidate_path=current_candidate_path,
                    final_candidate_hash=candidate_hash,
                    final_suite_summary=suite_summary,
                    holdout_suite_summary=None,
                    holdout_gate_passed=None,
                    lineage=lineage,
                )

            selected_case_id = failed_case_ids[0]
            failure_bundle = FailureBundle.model_validate_json(
                (iteration_root / selected_case_id / "failure-bundle.json").read_text()
            )
            critic_summary = self.critic.summarize(failure_bundle)
            patch_plan = refiner.plan(
                bundle=failure_bundle,
                critic_summary=critic_summary,
            )

            try:
                mutation_family = self.mutator.select_rule_name(
                    critic_summary=critic_summary,
                    patch_plan_summary=patch_plan.summary,
                )
                mutated_source = self.mutator.mutate(
                    source=source,
                    critic_summary=critic_summary,
                    patch_plan_summary=patch_plan.summary,
                )
            except ValueError:
                lineage.append(
                    CandidateLineageRecord(
                        iteration=iteration,
                        candidate_path=str(current_candidate_path),
                        candidate_hash=candidate_hash,
                        parent_candidate_hash=parent_candidate_hash,
                        suite_artifact_root=str(iteration_root),
                        suite_summary_path=suite_summary.summary_path,
                        status="failed",
                        ranking_score=ranking_score,
                        case_ids=case_ids,
                        failed_case_ids=failed_case_ids,
                        selected_case_id=selected_case_id,
                        stop_reason="unsupported_mutation",
                        legal_action_rate=suite_summary.legal_action_rate,
                        total_reward=suite_summary.total_reward,
                    )
                )
                return self._finish(
                    root_store=root_store,
                    status="failed",
                    stop_reason="unsupported_mutation",
                    iterations_attempted=iteration,
                    initial_candidate_path=candidate_path,
                    final_candidate_path=current_candidate_path,
                    final_candidate_hash=candidate_hash,
                    final_suite_summary=suite_summary,
                    holdout_suite_summary=None,
                    holdout_gate_passed=None,
                    lineage=lineage,
                )

            mutated_hash = _hash_source(mutated_source)
            lineage.append(
                CandidateLineageRecord(
                    iteration=iteration,
                    candidate_path=str(current_candidate_path),
                    candidate_hash=candidate_hash,
                    parent_candidate_hash=parent_candidate_hash,
                    suite_artifact_root=str(iteration_root),
                    suite_summary_path=suite_summary.summary_path,
                    status="failed",
                    ranking_score=ranking_score,
                    case_ids=case_ids,
                    failed_case_ids=failed_case_ids,
                    selected_case_id=selected_case_id,
                    mutation_family=mutation_family,
                    promoted_for_refinement=mutated_hash != candidate_hash,
                    legal_action_rate=suite_summary.legal_action_rate,
                    total_reward=suite_summary.total_reward,
                )
            )
            if mutated_hash == candidate_hash:
                return self._finish(
                    root_store=root_store,
                    status="failed",
                    stop_reason="no_improvement",
                    iterations_attempted=iteration,
                    initial_candidate_path=candidate_path,
                    final_candidate_path=current_candidate_path,
                    final_candidate_hash=candidate_hash,
                    final_suite_summary=suite_summary,
                    holdout_suite_summary=None,
                    holdout_gate_passed=None,
                    lineage=_mark_last_record_stop_reason(lineage, "no_improvement"),
                )

            best_score = max(best_score, ranking_score)
            next_candidate_path = artifact_root / f"iteration-{iteration + 1:02d}" / "candidate.py"
            next_candidate_path.parent.mkdir(parents=True, exist_ok=True)
            next_candidate_path.write_text(mutated_source)
            parent_candidate_hash = candidate_hash
            current_candidate_path = next_candidate_path

        raise RuntimeError("campaign loop terminated without a final suite summary")

    def _finish_with_optional_holdout(
        self,
        *,
        root_store: ArtifactStore,
        suite_id: str,
        status: str,
        stop_reason: CampaignStopReason,
        iterations_attempted: int,
        initial_candidate_path: Path,
        final_candidate_path: Path,
        final_candidate_hash: str,
        final_suite_summary: SuiteSummary,
        holdout_cases: list[FixtureCase] | None,
        minimum_holdout_legal_action_rate: float | None,
        provider_builder: Callable[[FixtureCase], CandidateModuleProvider],
        retry_limit: int,
        prompt_prefix: str,
        artifact_root: Path,
        lineage: list[CandidateLineageRecord],
    ) -> SuiteRefinementCampaignResult:
        holdout_suite_summary: SuiteSummary | None = None
        holdout_gate_passed: bool | None = None
        if holdout_cases is not None:
            holdout_suite_summary = run_fixture_suite(
                suite_id=f"{suite_id}-holdout",
                cases=holdout_cases,
                provider_factory=provider_builder,
                retry_limit=retry_limit,
                artifact_root=artifact_root / "holdout",
                prompt_prefix=prompt_prefix,
            )
            holdout_gate_passed = _holdout_gate_passed(
                dev_suite_summary=final_suite_summary,
                holdout_suite_summary=holdout_suite_summary,
                minimum_legal_action_rate=minimum_holdout_legal_action_rate,
            )
            if not holdout_gate_passed:
                status = "failed"
                stop_reason = "holdout_regression"

        return self._finish(
            root_store=root_store,
            status=status,
            stop_reason=stop_reason,
            iterations_attempted=iterations_attempted,
            initial_candidate_path=initial_candidate_path,
            final_candidate_path=final_candidate_path,
            final_candidate_hash=final_candidate_hash,
            final_suite_summary=final_suite_summary,
            holdout_suite_summary=holdout_suite_summary,
            holdout_gate_passed=holdout_gate_passed,
            lineage=lineage,
        )

    def _finish(
        self,
        *,
        root_store: ArtifactStore,
        status: str,
        stop_reason: CampaignStopReason,
        iterations_attempted: int,
        initial_candidate_path: Path,
        final_candidate_path: Path,
        final_candidate_hash: str,
        final_suite_summary: SuiteSummary,
        holdout_suite_summary: SuiteSummary | None,
        holdout_gate_passed: bool | None,
        lineage: list[CandidateLineageRecord],
    ) -> SuiteRefinementCampaignResult:
        lineage_path = root_store.write_candidate_lineage(lineage)
        summary = CampaignSummary(
            status="converged" if status == "converged" else "failed",
            stop_reason=stop_reason,
            iterations_attempted=iterations_attempted,
            initial_candidate_path=str(initial_candidate_path),
            final_candidate_path=str(final_candidate_path),
            final_candidate_hash=final_candidate_hash,
            candidate_lineage_path=str(lineage_path),
            final_suite_summary_path=final_suite_summary.summary_path,
            holdout_suite_summary_path=(
                holdout_suite_summary.summary_path if holdout_suite_summary is not None else None
            ),
            holdout_gate_passed=holdout_gate_passed,
        )
        summary_path = root_store.write_campaign_summary(summary)
        validate_campaign_artifacts(summary)
        return SuiteRefinementCampaignResult(
            status=status,
            stop_reason=stop_reason,
            iterations_attempted=iterations_attempted,
            final_candidate_path=str(final_candidate_path),
            final_candidate_hash=final_candidate_hash,
            final_suite_summary=final_suite_summary,
            holdout_suite_summary=holdout_suite_summary,
            candidate_lineage_path=str(lineage_path),
            campaign_summary_path=str(summary_path),
        )

    def _score_candidate(
        self,
        *,
        iteration: int,
        parent_candidate_hash: str | None,
        candidate_hash: str,
        suite_summary: SuiteSummary,
    ) -> float:
        node = self.search_controller.record_result(
            node=SearchNode(
                node_id=f"candidate-{iteration:02d}",
                candidate_hash=candidate_hash,
                parent_id=parent_candidate_hash,
            ),
            legal_actions=suite_summary.legal_attempts,
            illegal_actions=suite_summary.illegal_attempts,
            reward_total=suite_summary.total_reward,
        )
        return self.search_controller.score(node)


def _hash_source(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _holdout_gate_passed(
    *,
    dev_suite_summary: SuiteSummary,
    holdout_suite_summary: SuiteSummary,
    minimum_legal_action_rate: float | None,
) -> bool:
    if holdout_suite_summary.status != "passed":
        return False
    if (
        minimum_legal_action_rate is not None
        and holdout_suite_summary.legal_action_rate < minimum_legal_action_rate
    ):
        return False
    return holdout_suite_summary.legal_action_rate >= dev_suite_summary.legal_action_rate


def _mark_last_record_stop_reason(
    lineage: list[CandidateLineageRecord],
    stop_reason: CampaignStopReason,
) -> list[CandidateLineageRecord]:
    updated = list(lineage)
    updated[-1] = updated[-1].model_copy(update={"stop_reason": stop_reason})
    return updated


def validate_campaign_artifacts(summary: CampaignSummary) -> None:
    artifact_paths = {
        "candidate_lineage": summary.candidate_lineage_path,
        "final_suite_summary": summary.final_suite_summary_path,
    }
    if summary.holdout_suite_summary_path is not None:
        artifact_paths["holdout_suite_summary"] = summary.holdout_suite_summary_path
    missing = [
        name
        for name, raw_path in artifact_paths.items()
        if raw_path is None or not Path(raw_path).exists()
    ]
    if missing:
        raise RuntimeError(f"Missing campaign artifacts: {', '.join(missing)}")
