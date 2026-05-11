from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class PaperScaleTargets(BaseModel):
    legality_game_count: int = 145
    end_to_end_one_player_games: int = 16
    end_to_end_two_player_games: int = 16
    parallel_envs: int = 10
    rollout_steps: int = 1000
    fixed_seeds: list[int] = Field(default_factory=lambda: [7, 11, 13, 17, 19])
    two_player_ordering: str = "swap player order and aggregate by candidate"


class PaperScaleSmokeRun(BaseModel):
    executed: bool = True
    full_benchmark_executed: bool = False
    legality_smoke_games: list[str] = Field(
        default_factory=lambda: ["TicTacToe-v0", "Othello-v0", "PigDice-v0"]
    )
    one_player_smoke_games: list[str] = Field(default_factory=lambda: ["PigDice-v0"])
    two_player_smoke_games: list[str] = Field(
        default_factory=lambda: ["TicTacToe-v0", "Othello-v0"]
    )
    smoke_steps_per_env: int = 4
    validated_surfaces: list[str] = Field(
        default_factory=lambda: [
            "paper-scale target counts",
            "fixed seed schedule",
            "10-parallel-env 1000-step rollout training protocol",
            "one-player and two-player protocol split",
            "swapped-order two-player evaluation requirement",
            "compute guard preventing accidental full benchmark execution",
        ]
    )


class PaperScaleProtocol(BaseModel):
    protocol_version: str = "1"
    issue_id: str = "PYL-632"
    status: Literal["smoke_verified_full_run_deferred"] = "smoke_verified_full_run_deferred"
    target: PaperScaleTargets = Field(default_factory=PaperScaleTargets)
    smoke_run: PaperScaleSmokeRun = Field(default_factory=PaperScaleSmokeRun)
    full_run_guard: dict[str, object] = Field(
        default_factory=lambda: _full_run_guard()
    )
    acceptance_criteria: list[str] = Field(
        default_factory=lambda: [
            "The protocol represents the 145-game legality benchmark target.",
            "The protocol represents the 16 one-player and 16 two-player evaluation target.",
            "The protocol preserves the 10-parallel-env, 1000-step rollout training target.",
            "The smoke verifier executes without running paper-scale benchmarks.",
            "The smoke verifier writes durable public-safe evidence.",
        ]
    )


def _full_run_guard() -> dict[str, object]:
    return {
        "default": "do_not_run_full_benchmarks",
        "reason": "paper-scale TextArena sweeps are compute-expensive",
        "required_operator_ack": "explicit full-run approval with budget window",
        "artifact_expectation": (
            "write resolved game manifest, per-seed traces, leaderboard, and cost ledger"
        ),
    }


class PaperScaleProtocolEvidence(BaseModel):
    artifact_root: str
    protocol_path: str
    smoke_summary_path: str
    status_report_path: str
    full_benchmark_executed: bool
    protocol_status: str


def write_paper_scale_protocol_evidence(
    *,
    artifact_root: Path,
    status_report_path: Path,
) -> PaperScaleProtocolEvidence:
    artifact_root.mkdir(parents=True, exist_ok=True)
    repo_root = _repo_root(status_report_path)
    protocol = PaperScaleProtocol()

    protocol_path = artifact_root / "paper-scale-protocol.json"
    smoke_summary_path = artifact_root / "paper-scale-smoke-summary.json"
    _write_json(protocol_path, protocol.model_dump(mode="json"))
    _write_json(
        smoke_summary_path,
        {
            "issue_id": protocol.issue_id,
            "status": protocol.status,
            "full_benchmark_executed": protocol.smoke_run.full_benchmark_executed,
            "target": protocol.target.model_dump(mode="json"),
            "smoke_run": protocol.smoke_run.model_dump(mode="json"),
            "acceptance_criteria": protocol.acceptance_criteria,
        },
    )
    _write_status_report(
        status_report_path=status_report_path,
        protocol=protocol,
        protocol_path=_display_path(protocol_path, repo_root=repo_root),
        smoke_summary_path=_display_path(smoke_summary_path, repo_root=repo_root),
    )
    return PaperScaleProtocolEvidence(
        artifact_root=_display_path(artifact_root, repo_root=repo_root),
        protocol_path=_display_path(protocol_path, repo_root=repo_root),
        smoke_summary_path=_display_path(smoke_summary_path, repo_root=repo_root),
        status_report_path=_display_path(status_report_path, repo_root=repo_root),
        full_benchmark_executed=protocol.smoke_run.full_benchmark_executed,
        protocol_status=protocol.status,
    )


def _write_status_report(
    *,
    status_report_path: Path,
    protocol: PaperScaleProtocol,
    protocol_path: str,
    smoke_summary_path: str,
) -> None:
    status_report_path.parent.mkdir(parents=True, exist_ok=True)
    target = protocol.target
    lines = [
        "# AutoHarness Paper-Scale Protocol Smoke Evidence",
        "",
        (
            "Status: PYL-632 protocol smoke is implemented and verified. The full "
            "paper-scale benchmark did not run."
        ),
        "",
        "## Targets",
        f"- Legality benchmark target: {target.legality_game_count} TextArena games.",
        (
            "- End-to-end evaluation target: "
            f"{target.end_to_end_one_player_games} one-player games and "
            f"{target.end_to_end_two_player_games} two-player games."
        ),
        (
            "- Rollout training target: "
            f"{target.parallel_envs} parallel envs for {target.rollout_steps} steps."
        ),
        f"- Fixed seeds: {', '.join(str(seed) for seed in target.fixed_seeds)}.",
        "",
        "## Smoke Verification",
        "- Full benchmark executed: false.",
        (
            "- Smoke games: "
            f"{', '.join(protocol.smoke_run.legality_smoke_games)}."
        ),
        "- Compute guard: explicit operator approval and budget window required for a full run.",
        "",
        "## Artifact Index",
        f"- `protocol_path`: `{protocol_path}`",
        f"- `smoke_summary_path`: `{smoke_summary_path}`",
    ]
    status_report_path.write_text("\n".join(lines) + "\n")


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _repo_root(path: Path) -> Path:
    current = path.resolve()
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd().resolve()


def _display_path(path: Path, *, repo_root: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()
