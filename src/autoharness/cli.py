# Requirement coverage:
# REQ-001-bootstrap-003, REQ-001-bootstrap-005
# REQ-002-suite-refinement-002, REQ-002-suite-refinement-003
# REQ-003-toy-benchmarking-001, REQ-003-toy-benchmarking-002
# REQ-004-expanded-toy-benchmarking-artifact-policy-005
# REQ-004-expanded-toy-benchmarking-artifact-policy-008
# REQ-005-low-cost-textarena-smoke-expansion-003
# REQ-006-provider-backed-probe-cost-auth-policy-004
# REQ-006-provider-backed-probe-cost-auth-policy-006
# REQ-006-provider-backed-probe-cost-auth-policy-007
# REQ-006-provider-backed-probe-cost-auth-policy-008
# REQ-006-provider-backed-probe-cost-auth-policy-009
# REQ-006-provider-backed-probe-cost-auth-policy-010
# REQ-006-provider-backed-probe-cost-auth-policy-011
# REQ-006-provider-backed-probe-cost-auth-policy-013
# REQ-006-provider-backed-probe-cost-auth-policy-014
# REQ-006-provider-backed-probe-cost-auth-policy-016
from __future__ import annotations

import json
import os
import re
import shutil
from importlib import import_module
from importlib.util import find_spec
from pathlib import Path
from typing import Annotated, Any, Literal, cast

import typer
from pydantic import ValidationError

from autoharness.artifacts.models import (
    ProviderProbeBudgetReport,
    ProviderProbePreflightReport,
    ProviderProbeSummary,
    VerificationRunSummary,
    VerificationSummary,
)
from autoharness.artifacts.store import ArtifactStore
from autoharness.benchmarking import (
    load_benchmark_matrix,
    run_benchmark_matrix,
    write_benchmark_report,
)
from autoharness.benchmarking.models import BenchmarkArtifactConfig
from autoharness.benchmarks.fixtures import (
    FixtureBenchmark,
    FixtureCase,
    coerce_fixture_case,
)
from autoharness.benchmarks.textarena import TextArenaBenchmark
from autoharness.benchmarks.textarena import extract_available_actions as extract_textarena_actions
from autoharness.benchmarks.textarena import has_no_valid_moves as textarena_has_no_valid_moves
from autoharness.config.load import load_manifest, manifest_to_data
from autoharness.config.models import ArtifactConfig, Manifest
from autoharness.providers.base import Provider, ProviderResult
from autoharness.providers.candidate import CandidateModuleProvider, DockerCandidateProvider
from autoharness.providers.fixture import FixtureProvider
from autoharness.providers.gemini import GeminiProvider
from autoharness.providers.gemini_cli import GeminiCliProvider
from autoharness.providers.model_preflight import ModelPreflightProvider
from autoharness.providers.openrouter import OpenRouterProvider
from autoharness.refinement.campaign import SuiteRefinementCampaignRunner
from autoharness.runtime.loop import run_episode
from autoharness.runtime.models import EpisodeResult
from autoharness.runtime.verifiers import extract_action_text

app = typer.Typer(help="Package-first AutoHarness scaffold.", no_args_is_help=True)
ManifestOption = Annotated[
    Path,
    typer.Option(..., exists=True, dir_okay=False, readable=True),
]
CandidateOption = Annotated[
    Path,
    typer.Option(..., exists=True, dir_okay=False, readable=True),
]
ArtifactRootPathOption = Annotated[
    Path,
    typer.Option(..., file_okay=False, dir_okay=True),
]
ArtifactRootOverrideOption = Annotated[
    Path | None,
    typer.Option("--artifact-root", file_okay=False, dir_okay=True),
]
PatchTextOption = Annotated[
    str,
    typer.Option(...),
]
MaxIterationsOption = Annotated[
    int,
    typer.Option(..., min=1),
]
MaxSpendUsdOption = Annotated[
    float,
    typer.Option("--max-spend-usd", min=0.0),
]
ProviderProbeRunOption = Annotated[
    bool,
    typer.Option("--run/--dry-run"),
]
ProviderProbeUsagePolicyOption = Annotated[
    Literal["require-metadata", "allow-missing-once"],
    typer.Option("--usage-policy"),
]
ProviderProbeRootOption = Annotated[
    list[Path],
    typer.Option("--probe-root", exists=True, file_okay=False, dir_okay=True, readable=True),
]
ReportOutputRootOption = Annotated[
    Path,
    typer.Option("--output-root", file_okay=False, dir_okay=True),
]


@app.callback()
def main() -> None:
    """Package-first AutoHarness scaffold."""


def _build_provider(manifest: Manifest) -> Provider:
    provider = manifest.provider
    if provider.kind == "candidate":
        if provider.path is None:
            raise typer.BadParameter("Candidate provider requires a path")
        if provider.use_docker:
            return DockerCandidateProvider(
                path=provider.path,
                image=provider.sandbox_image or "python:3.12-alpine",
                model=provider.model,
            )
        return CandidateModuleProvider(path=provider.path, model=provider.model)
    if provider.kind == "fixture":
        return FixtureProvider(
            response_text=provider.response_text,
            sequence=provider.sequence,
            model=provider.model,
        )
    if provider.kind == "openrouter":
        env_var = provider.auth.env_var or "OPENROUTER_API_KEY"
        return OpenRouterProvider(model=provider.model, env_var=env_var)
    if provider.kind == "gemini-cli":
        command = str(provider.options.get("command", "gemini"))
        timeout_seconds = provider.options.get("timeout_seconds", 120)
        timeout_value = None if timeout_seconds is None else float(timeout_seconds)
        return GeminiCliProvider(
            model=provider.model,
            command=command,
            timeout_seconds=timeout_value,
        )
    if provider.kind == "model-preflight":
        config_path = provider.options.get("config_path")
        return ModelPreflightProvider(
            group=provider.model,
            config_path=config_path if isinstance(config_path, Path) else None,
        )
    env_var = provider.auth.env_var or "GEMINI_API_KEY"
    return GeminiProvider(
        model=provider.model,
        auth_kind=provider.auth.kind,
        env_var=env_var,
        project=provider.auth.project,
        location=provider.auth.location,
    )


def _build_benchmark(manifest: Manifest) -> FixtureBenchmark | TextArenaBenchmark:
    benchmark = manifest.benchmark
    if benchmark.kind == "textarena":
        if benchmark.env_id is None:
            raise typer.BadParameter("TextArena benchmark requires an env_id")
        return TextArenaBenchmark(
            env_id=benchmark.env_id,
            num_players=benchmark.num_players,
            seed=benchmark.seed,
            strip_moves=benchmark.strip_available_moves,
            options=benchmark.options,
        )
    if benchmark.kind != "fixture":
        raise typer.BadParameter("Unsupported benchmark kind")
    return FixtureBenchmark(
        observation=benchmark.observation,
        valid_actions=benchmark.valid_actions,
        max_steps=benchmark.max_steps,
        script=[step.model_dump(mode="python") for step in benchmark.script],
    )


@app.command()
def verify(manifest: ManifestOption, artifact_root: ArtifactRootOverrideOption = None) -> None:
    """Run the offline deterministic verifier against a manifest."""
    loaded_manifest = load_manifest(manifest)
    if artifact_root is not None:
        loaded_manifest = loaded_manifest.model_copy(
            update={"artifacts": ArtifactConfig(root=artifact_root.resolve())}
        )
    store = ArtifactStore(loaded_manifest.artifacts.root)
    store.write_manifest(manifest_to_data(loaded_manifest))
    deterministic_runs = loaded_manifest.verification.deterministic_runs
    if deterministic_runs == 1:
        result = _run_manifest_once(loaded_manifest)
        missing_paths = [
            str(path) for path in store.required_paths().values() if not path.exists()
        ]
        if missing_paths:
            typer.echo(f"Missing required artifacts: {', '.join(missing_paths)}")
            raise typer.Exit(code=1)
        if result.status != "passed":
            raise typer.Exit(code=1)
        if (
            loaded_manifest.verification.min_legal_action_rate is not None
            and result.legal_action_rate < loaded_manifest.verification.min_legal_action_rate
        ):
            typer.echo(
                "Legal action rate below threshold: "
                f"{result.legal_action_rate:.3f} < "
                f"{loaded_manifest.verification.min_legal_action_rate:.3f}"
            )
            raise typer.Exit(code=1)
        typer.echo(f"Verification passed for run {result.run_id}")
        return

    run_summaries: list[VerificationRunSummary] = []
    signatures: list[tuple[object, ...]] = []
    for index in range(deterministic_runs):
        run_root = loaded_manifest.artifacts.root / f"run-{index + 1:02d}"
        run_manifest = loaded_manifest.model_copy(
            update={"artifacts": ArtifactConfig(root=run_root)}
        )
        run_store = ArtifactStore(run_root)
        run_store.write_manifest(manifest_to_data(run_manifest))
        run_result = _run_manifest_once(run_manifest)
        missing_paths = [
            str(path) for path in run_store.required_paths().values() if not path.exists()
        ]
        if missing_paths:
            typer.echo(f"Missing required artifacts: {', '.join(missing_paths)}")
            raise typer.Exit(code=1)
        signatures.append(run_result.determinism_signature())
        run_summaries.append(
            VerificationRunSummary(
                run_index=index + 1,
                run_id=run_result.run_id,
                status=cast(Literal["passed", "failed"], run_result.status),
                legal_action_rate=run_result.legal_action_rate,
                total_reward=run_result.total_reward,
                retry_count=run_result.retry_count,
                steps=run_result.steps,
                final_action=run_result.final_action,
                artifact_root=str(run_root),
                determinism_signature=list(run_result.determinism_signature()),
            )
        )

    deterministic = len({signature for signature in signatures}) == 1
    min_observed_legal_action_rate = min(
        run_summary.legal_action_rate for run_summary in run_summaries
    )
    verification_summary = VerificationSummary(
        manifest_path=str(manifest),
        deterministic_runs=deterministic_runs,
        deterministic=deterministic,
        min_legal_action_rate=loaded_manifest.verification.min_legal_action_rate,
        min_observed_legal_action_rate=min_observed_legal_action_rate,
        runs=run_summaries,
    )
    store.write_verification_summary(verification_summary)
    if any(run_summary.status != "passed" for run_summary in run_summaries):
        typer.echo("Verification failed: at least one deterministic run did not pass")
        raise typer.Exit(code=1)
    if not deterministic:
        typer.echo("Determinism check failed across repeated verification runs")
        raise typer.Exit(code=1)
    if (
        loaded_manifest.verification.min_legal_action_rate is not None
        and min_observed_legal_action_rate < loaded_manifest.verification.min_legal_action_rate
    ):
        typer.echo(
            "Legal action rate below threshold: "
            f"{min_observed_legal_action_rate:.3f} < "
            f"{loaded_manifest.verification.min_legal_action_rate:.3f}"
        )
        raise typer.Exit(code=1)
    typer.echo(
        "Verification passed for runs "
        + ", ".join(run_summary.run_id for run_summary in run_summaries)
    )


@app.command()
def campaign(
    candidate: CandidateOption,
    dev_manifest: ManifestOption,
    holdout_manifest: ManifestOption,
    artifact_root: ArtifactRootPathOption,
    patch_text: PatchTextOption,
    max_iterations: MaxIterationsOption = 1,
) -> None:
    """Run a deterministic toy-suite refinement campaign."""
    if not patch_text.strip():
        raise typer.BadParameter("patch_text must not be empty", param_hint="--patch-text")
    candidate_path = candidate.resolve()
    campaign_root = artifact_root.resolve()
    loaded_dev_manifest = load_manifest(dev_manifest)
    loaded_holdout_manifest = load_manifest(holdout_manifest)
    _validate_campaign_manifests(
        dev_manifest=loaded_dev_manifest,
        holdout_manifest=loaded_holdout_manifest,
    )
    dev_cases = _load_fixture_cases(
        loaded_dev_manifest,
        default_case_prefix=f"{dev_manifest.stem}-case",
    )
    holdout_cases = _load_fixture_cases(
        loaded_holdout_manifest,
        default_case_prefix=f"{holdout_manifest.stem}-case",
    )
    store = ArtifactStore(campaign_root)
    store.write_manifest(
        {
            "candidate_path": str(candidate_path),
            "dev_manifest_path": str(dev_manifest),
            "dev_manifest": manifest_to_data(loaded_dev_manifest),
            "holdout_manifest_path": str(holdout_manifest),
            "holdout_manifest": manifest_to_data(loaded_holdout_manifest),
            "max_iterations": max_iterations,
            "patch_text": patch_text,
        }
    )
    result = SuiteRefinementCampaignRunner().run(
        suite_id=dev_manifest.stem,
        candidate_path=candidate_path,
        cases=dev_cases,
        patch_provider=FixtureProvider(response_text=patch_text),
        artifact_root=campaign_root,
        retry_limit=loaded_dev_manifest.runtime.retry_limit,
        max_iterations=max_iterations,
        prompt_prefix=loaded_dev_manifest.runtime.prompt_prefix,
        holdout_cases=holdout_cases,
        minimum_holdout_legal_action_rate=(
            loaded_holdout_manifest.verification.min_legal_action_rate
        ),
    )
    if result.status != "converged":
        typer.echo(
            "Campaign failed: "
            f"{result.stop_reason} "
            f"({result.campaign_summary_path})"
        )
        raise typer.Exit(code=1)
    typer.echo(
        "Campaign converged: "
        f"{result.final_candidate_path} "
        f"({result.campaign_summary_path})"
    )


@app.command()
def benchmark(matrix: ManifestOption, artifact_root: ArtifactRootOverrideOption = None) -> None:
    """Run the deterministic toy benchmark matrix and write comparison reports."""
    try:
        benchmark_matrix = load_benchmark_matrix(matrix)
    except (ValidationError, ValueError) as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1) from exc
    if artifact_root is not None:
        benchmark_matrix = benchmark_matrix.model_copy(
            update={"artifacts": BenchmarkArtifactConfig(root=artifact_root.resolve())}
        )

    store = ArtifactStore(benchmark_matrix.artifacts.root)
    store.write_manifest(benchmark_matrix.model_dump(mode="json"))
    summary = run_benchmark_matrix(benchmark_matrix)
    summary_path, leaderboard_path = write_benchmark_report(summary)
    top_candidate = summary.candidates[0]
    typer.echo(
        "Top candidate: "
        f"{top_candidate.candidate_label} "
        f"({summary_path}, {leaderboard_path})"
    )


@app.command("provider-probe")
def provider_probe(
    manifest: ManifestOption,
    artifact_root: ArtifactRootPathOption,
    max_spend_usd: MaxSpendUsdOption = 3.0,
    usage_policy: ProviderProbeUsagePolicyOption = "require-metadata",
    run: ProviderProbeRunOption = False,
) -> None:
    """Preflight or run one guarded provider-backed probe."""
    loaded_manifest = load_manifest(manifest)
    loaded_manifest = loaded_manifest.model_copy(
        update={"artifacts": ArtifactConfig(root=artifact_root.resolve())}
    )
    store = ArtifactStore(loaded_manifest.artifacts.root)
    store.write_manifest(manifest_to_data(loaded_manifest))
    preflight = _build_provider_probe_preflight(
        manifest_path=manifest,
        manifest=loaded_manifest,
        max_spend_usd=max_spend_usd,
    )
    preflight_path = store.write_provider_probe_preflight(preflight)
    budget = ProviderProbeBudgetReport(
        max_spend_usd=max_spend_usd,
        status="planned" if preflight.auth_ready else "blocked",
        messages=[
            "Dry-run writes budget evidence without making a provider call.",
            "Live provider execution is opt-in with --run.",
        ],
    )
    if max_spend_usd <= 0:
        budget.status = "blocked"
        budget.messages.append("max_spend_usd must be greater than 0 for a live probe.")
    budget_path = store.write_provider_probe_budget(budget)
    summary = ProviderProbeSummary(
        status="dry-run" if preflight.auth_ready and not run else "blocked",
        dry_run=not run,
        provider=loaded_manifest.provider.kind,
        model=loaded_manifest.provider.model,
        auth_kind=loaded_manifest.provider.auth.kind,
        artifact_root=str(loaded_manifest.artifacts.root),
        max_spend_usd=max_spend_usd,
        preflight_report_path=str(preflight_path),
        budget_report_path=str(budget_path),
        messages=list(preflight.messages) + list(budget.messages),
    )

    if not preflight.auth_ready or max_spend_usd <= 0:
        store.write_provider_probe_summary(summary)
        typer.echo("Provider probe blocked by preflight")
        raise typer.Exit(code=1)

    if run and not _provider_client_dependency_ready(loaded_manifest):
        message = _provider_dependency_message(loaded_manifest)
        budget.status = "blocked"
        budget.messages.append(message)
        budget_path = store.write_provider_probe_budget(budget)
        summary.status = "blocked"
        summary.budget_report_path = str(budget_path)
        summary.messages.append(message)
        store.write_provider_probe_summary(summary)
        typer.echo("Provider probe blocked by missing provider dependency")
        raise typer.Exit(code=1)

    if not run:
        store.write_provider_probe_summary(summary)
        typer.echo(f"Provider probe dry-run passed ({preflight_path}, {budget_path})")
        return

    try:
        result = _run_manifest_once(loaded_manifest)
    except RuntimeError as exc:
        message = f"Provider runtime error: {exc}"
        budget.status = "partial"
        budget.messages.append(message)
        budget_path = store.write_provider_probe_budget(budget)
        summary.status = "failed"
        summary.dry_run = False
        summary.budget_report_path = str(budget_path)
        summary.messages.append(message)
        store.write_provider_probe_summary(summary)
        typer.echo("Provider probe failed with provider runtime error")
        raise typer.Exit(code=1) from exc
    usage = _extract_provider_usage(loaded_manifest.artifacts.root / "trace.json")
    run_summary_path = loaded_manifest.artifacts.root / "run-summary.json"
    usage_metadata_present = bool(usage)
    budget.usage_metadata_present = usage_metadata_present
    budget.actual_spend_usd = 0.0
    if usage_metadata_present:
        budget.status = "complete"
        budget.messages.append(
            "Token usage metadata was captured; dollar spend is not estimated locally."
        )
    else:
        budget.status = "partial"
        budget.messages.append(
            "Provider usage metadata was missing; stop before additional provider calls."
        )
        if usage_policy == "allow-missing-once":
            budget.messages.append(
                "Missing usage metadata was explicitly allowed for this one probe."
            )
    budget_path = store.write_provider_probe_budget(budget)
    summary.status = "passed" if result.status == "passed" else "failed"
    summary.dry_run = False
    summary.usage = usage
    summary.usage_metadata_status = "complete" if usage_metadata_present else "partial"
    summary.run_summary_path = str(run_summary_path)
    summary.budget_report_path = str(budget_path)
    if not usage_metadata_present and usage_policy == "allow-missing-once":
        summary.messages.append(
            "Missing usage metadata was explicitly allowed for this one probe."
        )
    if not usage_metadata_present and usage_policy == "require-metadata":
        summary.status = "blocked"
    store.write_provider_probe_summary(summary)
    if not usage_metadata_present and usage_policy == "require-metadata":
        typer.echo("Provider probe stopped after one call: missing usage metadata")
        raise typer.Exit(code=1)
    if result.status != "passed":
        typer.echo("Provider probe failed")
        raise typer.Exit(code=1)
    if not usage_metadata_present:
        typer.echo(f"Provider probe passed with partial usage metadata for run {result.run_id}")
        return
    typer.echo(f"Provider probe passed for run {result.run_id}")


@app.command("provider-report")
def provider_report(
    probe_root: ProviderProbeRootOption,
    output_root: ReportOutputRootOption,
) -> None:
    """Summarize completed provider-probe artifact roots."""
    if not probe_root:
        typer.echo("At least one --probe-root is required.")
        raise typer.Exit(code=1)
    runs = [_load_provider_report_run(root) for root in probe_root]
    aggregate = _build_provider_report_aggregate(runs)
    report = {"aggregate": aggregate, "runs": runs}
    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "provider-evidence-report.json"
    markdown_path = output_root / "provider-evidence-report.md"
    json_path.write_text(json.dumps(report, indent=2))
    markdown_path.write_text(_render_provider_report_markdown(report))
    typer.echo(f"Provider evidence report written to {json_path} and {markdown_path}")


def _load_provider_report_run(root: Path) -> dict[str, Any]:
    probe_summary = _read_json_file(root / "provider-probe-summary.json")
    budget_summary = _read_json_file(root / "provider-probe-budget.json")
    run_summary_path = root / "run-summary.json"
    run_summary = _read_json_file(run_summary_path) if run_summary_path.exists() else {}
    trace_path = root / "trace.json"
    trace = _read_json_file(trace_path) if trace_path.exists() else []
    if not isinstance(trace, list):
        trace = []
    illegal_steps = [
        _qualitative_step(record)
        for record in trace
        if isinstance(record, dict) and record.get("legal") is False
    ]
    step_history = [
        _history_step(record)
        for record in trace
        if isinstance(record, dict)
    ]
    failure_bundle_path = root / "failure-bundle.json"
    critic_summary_path = root / "critic-summary.json"
    failure_bundle = (
        _read_json_file(failure_bundle_path) if failure_bundle_path.exists() else None
    )
    critic_summary = (
        _read_json_file(critic_summary_path) if critic_summary_path.exists() else None
    )
    first_action = trace[0].get("action") if trace and isinstance(trace[0], dict) else None
    last_action = trace[-1].get("action") if trace and isinstance(trace[-1], dict) else None
    return {
        "name": root.name,
        "artifact_root": str(root),
        "provider": probe_summary.get("provider"),
        "model": probe_summary.get("model"),
        "auth_kind": probe_summary.get("auth_kind"),
        "probe_status": probe_summary.get("status"),
        "episode_status": run_summary.get("status"),
        "run_id": run_summary.get("run_id"),
        "steps": run_summary.get("steps", 0),
        "retry_count": run_summary.get("retry_count", 0),
        "legal_attempts": run_summary.get("legal_attempts", 0),
        "illegal_attempts": run_summary.get("illegal_attempts", 0),
        "legal_action_rate": run_summary.get("legal_action_rate", 0.0),
        "total_reward": run_summary.get("total_reward", 0.0),
        "usage_metadata_status": probe_summary.get("usage_metadata_status"),
        "budget_status": budget_summary.get("status"),
        "max_spend_usd": budget_summary.get("max_spend_usd", 0.0),
        "actual_spend_usd": budget_summary.get("actual_spend_usd", 0.0),
        "qualitative": {
            "illegal_steps": illegal_steps,
            "step_history": step_history,
            "failure_bundle": failure_bundle,
            "critic_summary": critic_summary,
            "first_action": first_action,
            "last_action": last_action,
        },
    }


def _read_json_file(path: Path) -> Any:
    if not path.exists():
        typer.echo(f"Missing provider report artifact: {path}")
        raise typer.Exit(code=1)
    return json.loads(path.read_text())


def _qualitative_step(record: dict[str, Any]) -> dict[str, Any]:
    observation = str(record.get("observation", ""))
    regrade = _regrade_report_record(record)
    context_lines = [
        line
        for line in observation.splitlines()
        if line.startswith(
            ("Valid moves", "Available actions", "Available Moves", "No valid moves", "Scores")
        )
    ]
    return {
        "step_index": record.get("step_index"),
        "attempt_index": record.get("attempt_index"),
        "action": record.get("action"),
        "recorded_legal": record.get("legal"),
        "current_verifier_action": regrade["action"],
        "current_verifier_legal": regrade["legal"],
        "valid_moves": _extract_report_valid_moves(observation),
        "verifier_scores": _extract_report_verifier_scores(record),
        "context": context_lines[-3:],
    }


def _history_step(record: dict[str, Any]) -> dict[str, Any]:
    observation = str(record.get("observation", ""))
    regrade = _regrade_report_record(record)
    return {
        "step_index": record.get("step_index"),
        "attempt_index": record.get("attempt_index"),
        "action": record.get("action"),
        "recorded_legal": record.get("legal"),
        "current_verifier_action": regrade["action"],
        "current_verifier_legal": regrade["legal"],
        "valid_moves": _extract_report_valid_moves(observation),
        "scores": _extract_report_scores(observation),
        "board_tail": _extract_report_board_tail(observation),
        "verifier_scores": _extract_report_verifier_scores(record),
    }


def _regrade_report_record(record: dict[str, Any]) -> dict[str, Any]:
    observation = str(record.get("observation", ""))
    legal_actions = _extract_report_valid_moves(observation)
    raw_action = str(record.get("action", ""))
    provider = str(record.get("provider", "unknown"))
    action = extract_action_text(
        ProviderResult(text=raw_action, provider=provider, model="unknown"),
        legal_actions,
    )
    legal = action in legal_actions
    if textarena_has_no_valid_moves(observation):
        legal = bool(action.strip())
    return {"action": action, "legal": legal}


def _extract_report_valid_moves(observation: str) -> list[str]:
    actions = extract_textarena_actions(observation)
    if actions:
        return actions
    fixture_lines = [
        line
        for line in observation.splitlines()
        if "Legal Actions:" in line or "Available Actions:" in line
    ]
    if not fixture_lines:
        return []
    latest = fixture_lines[-1]
    quoted = re.findall(r"'([^']+)'", latest)
    if quoted:
        return quoted
    payload_match = re.search(r"(?:Legal Actions|Available Actions):\s*([^.\n]+)", latest)
    if payload_match is not None:
        payload = payload_match.group(1)
    else:
        _, _, payload = latest.partition(":")
    return [item.strip() for item in payload.split(",") if item.strip()]


def _extract_report_scores(observation: str) -> list[str]:
    return [
        line
        for line in observation.splitlines()
        if line.startswith(("Scores", "Curren Scores"))
    ][-3:]


def _extract_report_board_tail(observation: str) -> list[str]:
    board_lines = [
        line
        for line in observation.splitlines()
        if re.match(r"^\d+\|", line)
    ]
    return board_lines[-4:]


def _extract_report_verifier_scores(record: dict[str, Any]) -> dict[str, Any]:
    metadata = record.get("metadata")
    if not isinstance(metadata, dict):
        return {}
    scores = metadata.get("verifier_scores")
    return scores if isinstance(scores, dict) else {}


def _build_provider_report_aggregate(runs: list[dict[str, Any]]) -> dict[str, Any]:
    total_runs = len(runs)
    legal_rates = [
        float(run.get("legal_action_rate", 0.0))
        for run in runs
        if isinstance(run.get("legal_action_rate"), (int, float))
    ]
    return {
        "total_runs": total_runs,
        "probe_passed_runs": sum(1 for run in runs if run.get("probe_status") == "passed"),
        "probe_failed_runs": sum(1 for run in runs if run.get("probe_status") == "failed"),
        "probe_blocked_runs": sum(1 for run in runs if run.get("probe_status") == "blocked"),
        "episode_passed_runs": sum(1 for run in runs if run.get("episode_status") == "passed"),
        "episode_failed_runs": sum(1 for run in runs if run.get("episode_status") == "failed"),
        "mean_legal_action_rate": (
            sum(legal_rates) / len(legal_rates) if legal_rates else 0.0
        ),
        "min_legal_action_rate": min(legal_rates) if legal_rates else 0.0,
        "total_legal_attempts": sum(int(run.get("legal_attempts", 0)) for run in runs),
        "total_illegal_attempts": sum(int(run.get("illegal_attempts", 0)) for run in runs),
        "total_retries": sum(int(run.get("retry_count", 0)) for run in runs),
        "current_verifier_illegal_attempts": sum(
            1
            for run in runs
            for step in run.get("qualitative", {}).get("step_history", [])
            if step.get("current_verifier_legal") is False
        ),
        "current_verifier_legal_attempts": sum(
            1
            for run in runs
            for step in run.get("qualitative", {}).get("step_history", [])
            if step.get("current_verifier_legal") is True
        ),
        "usage_metadata_complete_runs": sum(
            1 for run in runs if run.get("usage_metadata_status") == "complete"
        ),
        "usage_metadata_partial_runs": sum(
            1 for run in runs if run.get("usage_metadata_status") == "partial"
        ),
        "total_actual_spend_usd": sum(float(run.get("actual_spend_usd", 0.0)) for run in runs),
        "total_max_spend_usd": sum(float(run.get("max_spend_usd", 0.0)) for run in runs),
    }


def _render_provider_report_markdown(report: dict[str, Any]) -> str:
    aggregate = cast(dict[str, Any], report["aggregate"])
    runs = cast(list[dict[str, Any]], report["runs"])
    lines = [
        "# Provider Evidence Report",
        "",
        "## Aggregate",
        "",
        f"- total_runs: `{aggregate['total_runs']}`",
        f"- episode_passed_runs: `{aggregate['episode_passed_runs']}`",
        f"- mean_legal_action_rate: `{aggregate['mean_legal_action_rate']:.3f}`",
        f"- total_illegal_attempts: `{aggregate['total_illegal_attempts']}`",
        f"- current_verifier_illegal_attempts: `{aggregate['current_verifier_illegal_attempts']}`",
        f"- usage_metadata_partial_runs: `{aggregate['usage_metadata_partial_runs']}`",
        "",
        "## Runs",
        "",
        "| run | probe | episode | legal_action_rate | retries | illegal | usage |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for run in runs:
        lines.append(
            "| "
            f"{run['name']} | {run['probe_status']} | {run['episode_status']} | "
            f"{float(run['legal_action_rate']):.3f} | {run['retry_count']} | "
            f"{run['illegal_attempts']} | {run['usage_metadata_status']} |"
        )
    illegal_runs = [
        run for run in runs if run.get("qualitative", {}).get("illegal_steps")
    ]
    lines.extend(["", "## Qualitative Notes", ""])
    if not illegal_runs:
        lines.append("- No illegal steps were recorded in the supplied probe roots.")
    else:
        for run in illegal_runs:
            lines.append(f"### {run['name']}")
            for step in run["qualitative"]["illegal_steps"]:
                lines.append(
                    "- "
                    f"step `{step['step_index']}` attempt `{step['attempt_index']}` "
                    f"action `{step['action']}`; valid moves: "
                    f"`{', '.join(step['valid_moves']) or 'none'}`; "
                    f"current verifier legal: `{step['current_verifier_legal']}`"
                )
            critic_summary = run["qualitative"].get("critic_summary")
            if isinstance(critic_summary, dict):
                lines.append(f"- critic root cause: {critic_summary.get('root_cause')}")
                lines.append(
                    f"- recommended change: {critic_summary.get('recommended_change')}"
                )
    for run in runs:
        lines.extend(["", f"### Step History - {run['name']}", ""])
        lines.extend(
            [
                "| step | attempt | recorded | current | action | valid_moves | scores |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for step in run.get("qualitative", {}).get("step_history", []):
            valid_moves = ", ".join(step["valid_moves"]) or "none"
            scores = "; ".join(step["scores"]) or "none"
            recorded = "yes" if step["recorded_legal"] is True else "no"
            current = "yes" if step["current_verifier_legal"] is True else "no"
            lines.append(
                f"| {step['step_index']} | {step['attempt_index']} | "
                f"{recorded} | {current} | "
                f"`{step['action']}` | `{valid_moves}` | {scores} |"
            )
            if step["board_tail"]:
                lines.append("")
                lines.append("```text")
                lines.extend(step["board_tail"])
                lines.append("```")
                lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _run_manifest_once(manifest: Manifest) -> EpisodeResult:
    provider = _build_provider(manifest)
    benchmark = _build_benchmark(manifest)
    return run_episode(
        benchmark=benchmark,
        provider=provider,
        retry_limit=manifest.runtime.retry_limit,
        artifact_root=manifest.artifacts.root,
        prompt_prefix=manifest.runtime.prompt_prefix,
        candidate_count=manifest.provider.candidate_count,
        temperature=manifest.provider.temperature,
        top_p=manifest.provider.top_p,
    )


def _provider_client_dependency_ready(manifest: Manifest) -> bool:
    if manifest.provider.kind == "gemini-cli":
        command = str(manifest.provider.options.get("command", "gemini"))
        return _gemini_cli_command_ready(command)
    if manifest.provider.kind == "model-preflight":
        config_path = manifest.provider.options.get("config_path")
        ready, _messages = _model_preflight_config_ready(
            config_path if isinstance(config_path, Path) else None,
            group=manifest.provider.model,
        )
        return ready
    if manifest.provider.kind != "gemini":
        return True
    try:
        return find_spec("google.genai") is not None
    except ModuleNotFoundError:
        return False


def _gemini_cli_command_ready(command: str) -> bool:
    return shutil.which(command) is not None


def _provider_dependency_message(manifest: Manifest) -> str:
    if manifest.provider.kind == "gemini-cli":
        command = str(manifest.provider.options.get("command", "gemini"))
        return (
            "Gemini CLI OAuth probe requires the Gemini CLI command on PATH; "
            f"missing command: {command}."
        )
    if manifest.provider.kind == "model-preflight":
        return (
            "ModelPreflight probe requires the published model-preflight package "
            "and a valid model-preflight config; rerun with `--extra preflight` "
            "and check `mpf doctor`."
        )
    return (
        "Gemini OAuth/ADC probe requires the google-genai client library; "
        "rerun with `uv run --extra dev --extra textarena --extra providers ...`."
    )


def _build_provider_probe_preflight(
    *,
    manifest_path: Path,
    manifest: Manifest,
    max_spend_usd: float,
) -> ProviderProbePreflightReport:
    provider = manifest.provider
    messages = [
        "Codex OAuth is not currently supported as an autoharness provider credential.",
        "API-key fallback is configurable but not selected silently for this probe.",
    ]
    auth_ready = True
    if provider.kind in {"fixture", "candidate"}:
        auth_ready = False
        messages.append("Provider probe requires a live provider manifest.")
    if provider.kind not in {"gemini", "gemini-cli", "model-preflight"}:
        auth_ready = False
        messages.append("Provider probe supports Gemini OAuth or ModelPreflight routes.")
    if provider.kind == "model-preflight":
        config_path = provider.options.get("config_path")
        ready, config_messages = _model_preflight_config_ready(
            config_path if isinstance(config_path, Path) else None,
            group=provider.model,
        )
        auth_ready = auth_ready and ready
        messages.extend(config_messages)
    if provider.kind == "gemini-cli" and provider.auth.kind != "oauth-cli":
        auth_ready = False
        messages.append("Gemini CLI provider probe requires auth.kind: oauth-cli.")
    if provider.kind == "gemini-cli":
        command = str(provider.options.get("command", "gemini"))
        if not _gemini_cli_command_ready(command):
            auth_ready = False
            messages.append(f"Gemini CLI command was not found on PATH: {command}.")
    if provider.kind == "gemini" and provider.auth.kind != "oauth-adc":
        auth_ready = False
        messages.append("Gemini SDK provider probe requires auth.kind: oauth-adc.")
    if provider.kind == "gemini" and not provider.auth.project:
        env_project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCLOUD_PROJECT")
        if not env_project:
            auth_ready = False
            messages.append("Gemini OAuth/ADC probe requires auth.project or GOOGLE_CLOUD_PROJECT.")
    if provider.kind == "gemini" and not provider.auth.location:
        env_location = os.getenv("GOOGLE_CLOUD_LOCATION") or os.getenv("GOOGLE_CLOUD_REGION")
        if not env_location:
            auth_ready = False
            messages.append(
                "Gemini OAuth/ADC probe requires auth.location or GOOGLE_CLOUD_LOCATION."
            )
    if max_spend_usd <= 0:
        auth_ready = False
        messages.append("max_spend_usd must be greater than 0.")
    return ProviderProbePreflightReport(
        manifest_path=str(manifest_path),
        artifact_root=str(manifest.artifacts.root),
        provider=provider.kind,
        model=provider.model,
        auth_kind=provider.auth.kind,
        auth_ready=auth_ready,
        codex_oauth_supported=False,
        messages=messages,
    )


def _model_preflight_config_ready(
    config_path: Path | None,
    *,
    group: str,
) -> tuple[bool, list[str]]:
    try:
        config_module = import_module("model_preflight.config")
    except ImportError:
        return (
            False,
            [
                "model-preflight is not installed; rerun with "
                "`uv run --extra preflight ...`."
            ],
        )
    try:
        config = config_module.load_config(config_path)
    except FileNotFoundError as exc:
        return False, [str(exc)]
    try:
        cli_module = import_module("model_preflight.cli")
        diagnostic_fn = getattr(cli_module, "_doctor_diagnostic", None)
    except ImportError:
        diagnostic_fn = None
    if callable(diagnostic_fn):
        diagnostic = diagnostic_fn(config, group=group)
        status = diagnostic.get("status")
        error_code = diagnostic.get("error_code")
        if status == "ok":
            return True, [f"ModelPreflight group is ready: {group}."]
        messages = [
            f"ModelPreflight doctor failed for group {group!r}: {error_code or 'UNKNOWN'}."
        ]
        missing = diagnostic.get("missing_env_vars")
        if isinstance(missing, list) and missing:
            messages.append("Missing required env vars: " + ", ".join(map(str, missing)) + ".")
        enabled_groups = diagnostic.get("enabled_groups")
        if isinstance(enabled_groups, list):
            messages.append(
                "Enabled ModelPreflight groups: " + ", ".join(map(str, enabled_groups)) + "."
            )
        disabled = diagnostic.get("disabled_matching_providers")
        if isinstance(disabled, list) and disabled:
            messages.append(
                "Disabled matching ModelPreflight providers: " + ", ".join(map(str, disabled)) + "."
            )
        next_commands = diagnostic.get("next_commands")
        if isinstance(next_commands, list) and next_commands:
            messages.append("Next commands: " + "; ".join(map(str, next_commands)))
        return False, messages
    deployments = getattr(config, "deployments", [])
    selected = [
        deployment
        for deployment in deployments
        if getattr(deployment, "enabled", True) and getattr(deployment, "group", None) == group
    ]
    if not selected:
        return False, [f"ModelPreflight config has no enabled deployments for group: {group}."]
    missing = sorted(
        {
            env_var
            for deployment in selected
            if getattr(deployment, "required", True)
            for env_var in [getattr(deployment, "api_key_env", None)]
            if isinstance(env_var, str) and env_var and not os.getenv(env_var)
        }
    )
    if missing:
        return (
            False,
            [
                f"ModelPreflight group {group!r} is missing required env vars: "
                + ", ".join(missing)
                + ".",
            ],
        )
    return True, [f"ModelPreflight group is ready: {group}."]


def _extract_provider_usage(trace_path: Path) -> dict[str, object]:
    if not trace_path.exists():
        return {}
    payload = json.loads(trace_path.read_text())
    if not isinstance(payload, list):
        return {}
    for record in payload:
        if not isinstance(record, dict):
            continue
        metadata = record.get("metadata")
        if not isinstance(metadata, dict):
            continue
        assessments = metadata.get("candidate_assessments")
        if not isinstance(assessments, list):
            continue
        for assessment in assessments:
            if not isinstance(assessment, dict):
                continue
            provider_metadata = assessment.get("provider_metadata")
            if not isinstance(provider_metadata, dict):
                continue
            usage = provider_metadata.get("usage")
            if isinstance(usage, dict) and usage:
                return usage
    return {}


def _load_fixture_cases(manifest: Manifest, *, default_case_prefix: str) -> list[FixtureCase]:
    benchmark = manifest.benchmark
    if benchmark.kind != "fixture":
        raise typer.BadParameter("Campaign manifests must use fixture benchmarks")
    if benchmark.cases:
        return [
            coerce_fixture_case(case.model_dump(mode="python"))
            for case in benchmark.cases
        ]
    return [
        coerce_fixture_case(
            {
                "case_id": default_case_prefix,
                "observation": benchmark.observation,
                "valid_actions": list(benchmark.valid_actions),
                "max_steps": benchmark.max_steps,
                "script": [
                    step.model_dump(mode="python") for step in benchmark.script
                ],
            }
        )
    ]


def _validate_campaign_manifests(
    *,
    dev_manifest: Manifest,
    holdout_manifest: Manifest,
) -> None:
    if dev_manifest.benchmark.kind != "fixture":
        raise typer.BadParameter(
            "Dev campaign manifest must use a fixture benchmark",
            param_hint="--dev-manifest",
        )
    if holdout_manifest.benchmark.kind != "fixture":
        raise typer.BadParameter(
            "Holdout campaign manifest must use a fixture benchmark",
            param_hint="--holdout-manifest",
        )
    if holdout_manifest.runtime.retry_limit != dev_manifest.runtime.retry_limit:
        raise typer.BadParameter(
            "Holdout manifest retry_limit must match the dev manifest",
            param_hint="--holdout-manifest",
        )
    if holdout_manifest.runtime.prompt_prefix != dev_manifest.runtime.prompt_prefix:
        raise typer.BadParameter(
            "Holdout manifest prompt_prefix must match the dev manifest",
            param_hint="--holdout-manifest",
        )
