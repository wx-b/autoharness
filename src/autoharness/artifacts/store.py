# Requirement coverage:
# REQ-001-bootstrap-003, REQ-001-bootstrap-005
# REQ-002-suite-refinement-001, REQ-003-toy-benchmarking-005
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from pydantic import BaseModel

from .models import (
    CampaignSummary,
    CandidateLineageRecord,
    CriticSummary,
    FailureBundle,
    ProviderProbeBudgetReport,
    ProviderProbePreflightReport,
    ProviderProbeSummary,
    RefinementSummary,
    RunSummary,
    SearchTraceRecord,
    StepRecord,
    SuiteSummary,
    VerificationSummary,
)


class ArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def write_summary(self, summary: RunSummary) -> Path:
        path = self.root / "run-summary.json"
        path.write_text(summary.model_dump_json(indent=2))
        return path

    def write_trace(self, trace: Sequence[StepRecord]) -> Path:
        path = self.root / "trace.json"
        path.write_text(json.dumps([record.model_dump(mode="json") for record in trace], indent=2))
        return path

    def write_manifest(self, manifest: Mapping[str, object]) -> Path:
        path = self.root / "resolved-manifest.json"
        path.write_text(json.dumps(manifest, indent=2, default=str))
        return path

    def write_failure_bundle(self, bundle: FailureBundle) -> Path:
        path = self.root / "failure-bundle.json"
        path.write_text(bundle.model_dump_json(indent=2))
        return path

    def write_critic_summary(self, summary: CriticSummary) -> Path:
        path = self.root / "critic-summary.json"
        path.write_text(summary.model_dump_json(indent=2))
        return path

    def write_verification_summary(self, summary: VerificationSummary) -> Path:
        path = self.root / "verification-summary.json"
        path.write_text(summary.model_dump_json(indent=2))
        return path

    def write_provider_probe_preflight(
        self,
        report: ProviderProbePreflightReport,
    ) -> Path:
        path = self.root / "provider-probe-preflight.json"
        path.write_text(report.model_dump_json(indent=2))
        return path

    def write_provider_probe_budget(
        self,
        report: ProviderProbeBudgetReport,
    ) -> Path:
        path = self.root / "provider-probe-budget.json"
        path.write_text(report.model_dump_json(indent=2))
        return path

    def write_provider_probe_summary(
        self,
        summary: ProviderProbeSummary,
    ) -> Path:
        path = self.root / "provider-probe-summary.json"
        path.write_text(summary.model_dump_json(indent=2))
        return path

    def write_search_trace(self, records: Sequence[SearchTraceRecord]) -> Path:
        path = self.root / "search-trace.jsonl"
        path.write_text(
            "\n".join(record.model_dump_json() for record in records) + ("\n" if records else "")
        )
        return path

    def write_refinement_summary(self, summary: RefinementSummary) -> Path:
        path = self.root / "refinement-summary.json"
        path.write_text(summary.model_dump_json(indent=2))
        return path

    def write_candidate_lineage(self, records: Sequence[CandidateLineageRecord]) -> Path:
        path = self.root / "candidate-lineage.jsonl"
        path.write_text(
            "\n".join(record.model_dump_json() for record in records) + ("\n" if records else "")
        )
        return path

    def write_campaign_summary(self, summary: CampaignSummary) -> Path:
        path = self.root / "campaign-summary.json"
        path.write_text(summary.model_dump_json(indent=2))
        return path

    def write_benchmark_summary(self, summary: BaseModel) -> Path:
        path = self.root / "benchmark-summary.json"
        path.write_text(summary.model_dump_json(indent=2))
        return path

    def write_benchmark_leaderboard(self, leaderboard: str) -> Path:
        path = self.root / "leaderboard.md"
        path.write_text(leaderboard)
        return path

    def write_suite_summary(self, summary: SuiteSummary) -> Path:
        path = self.root / "suite-summary.json"
        path.write_text(summary.model_dump_json(indent=2))
        return path

    def required_paths(self) -> dict[str, Path]:
        return {
            "manifest": self.root / "resolved-manifest.json",
            "summary": self.root / "run-summary.json",
            "trace": self.root / "trace.json",
        }
