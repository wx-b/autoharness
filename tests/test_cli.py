# Requirement coverage:
# REQ-001-bootstrap-003, REQ-001-bootstrap-005
# REQ-002-suite-refinement-002, REQ-002-suite-refinement-003
# REQ-003-toy-benchmarking-002, REQ-003-toy-benchmarking-004
# REQ-004-expanded-toy-benchmarking-artifact-policy-005
# REQ-004-expanded-toy-benchmarking-artifact-policy-008
# REQ-005-low-cost-textarena-smoke-expansion-004
# REQ-006-provider-backed-probe-cost-auth-policy-004
# REQ-006-provider-backed-probe-cost-auth-policy-006
# REQ-006-provider-backed-probe-cost-auth-policy-007
# REQ-006-provider-backed-probe-cost-auth-policy-008
# REQ-006-provider-backed-probe-cost-auth-policy-009
# REQ-006-provider-backed-probe-cost-auth-policy-010
# REQ-006-provider-backed-probe-cost-auth-policy-011
# REQ-006-provider-backed-probe-cost-auth-policy-013
# REQ-006-provider-backed-probe-cost-auth-policy-014
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import autoharness.cli as cli_module
from autoharness.cli import app
from autoharness.runtime.models import EpisodeResult

runner = CliRunner()


def test_cli_help_exits_zero() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "verify" in result.output
    assert "benchmark" in result.output


def test_verify_command_runs_offline_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "offline_smoke.yaml"
    manifest.write_text(
        "\n".join(
            [
                'version: "1"',
                "provider:",
                "  kind: fixture",
                "  model: fixture-model",
                "  sequence:",
                "    - right",
                "    - left",
                "benchmark:",
                "  kind: fixture",
                '  observation: "Choose a legal action: left"',
                "  valid_actions:",
                "    - left",
                "  max_steps: 1",
                "runtime:",
                "  retry_limit: 2",
                '  prompt_prefix: "Return only the action."',
                "artifacts:",
                f"  root: {tmp_path / 'artifacts'}",
            ]
        )
    )
    result = runner.invoke(app, ["verify", "--manifest", str(manifest)])
    assert result.exit_code == 0
    assert "verification passed" in result.output.lower()
    assert (tmp_path / "artifacts" / "resolved-manifest.json").exists()
    assert (tmp_path / "artifacts" / "run-summary.json").exists()
    assert (tmp_path / "artifacts" / "trace.json").exists()


def test_provider_probe_dry_run_writes_preflight_without_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "demo-project")
    artifact_root = tmp_path / "provider-probe"

    result = runner.invoke(
        app,
        [
            "provider-probe",
            "--manifest",
            "manifests/provider_probe_gemini_othello.yaml",
            "--artifact-root",
            str(artifact_root),
            "--max-spend-usd",
            "3.00",
        ],
    )

    assert result.exit_code == 0
    assert "dry-run passed" in result.output.lower()
    assert (artifact_root / "resolved-manifest.json").exists()
    assert (artifact_root / "provider-probe-preflight.json").exists()
    assert (artifact_root / "provider-probe-budget.json").exists()
    assert (artifact_root / "provider-probe-summary.json").exists()
    assert not (artifact_root / "run-summary.json").exists()
    preflight = json.loads((artifact_root / "provider-probe-preflight.json").read_text())
    summary = json.loads((artifact_root / "provider-probe-summary.json").read_text())
    assert preflight["auth_ready"] is True
    assert preflight["codex_oauth_supported"] is False
    assert summary["status"] == "dry-run"
    assert summary["dry_run"] is True


def test_provider_probe_rejects_fixture_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "fixture_probe.yaml"
    manifest.write_text(
        "\n".join(
            [
                'version: "1"',
                "provider:",
                "  kind: fixture",
                "benchmark:",
                "  kind: fixture",
                '  observation: "Legal Actions: left"',
                "  valid_actions:",
                "    - left",
                "runtime:",
                "  retry_limit: 0",
                "artifacts:",
                f"  root: {tmp_path / 'ignored'}",
            ]
        )
    )

    result = runner.invoke(
        app,
        [
            "provider-probe",
            "--manifest",
            str(manifest),
            "--artifact-root",
            str(tmp_path / "probe"),
        ],
    )

    assert result.exit_code == 1
    assert "blocked" in result.output.lower()
    preflight = json.loads(
        (tmp_path / "probe" / "provider-probe-preflight.json").read_text()
    )
    assert preflight["auth_ready"] is False
    assert any("live provider" in message for message in preflight["messages"])


def test_provider_probe_oauth_adc_fails_closed_without_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GCLOUD_PROJECT", raising=False)
    manifest = tmp_path / "missing_project_probe.yaml"
    manifest.write_text(
        "\n".join(
            [
                'version: "1"',
                "provider:",
                "  kind: gemini",
                "  model: gemini-2.5-flash",
                "  auth:",
                "    kind: oauth-adc",
                "    location: us-central1",
                "benchmark:",
                "  kind: fixture",
                '  observation: "Legal Actions: left"',
                "  valid_actions:",
                "    - left",
                "runtime:",
                "  retry_limit: 0",
                "artifacts:",
                f"  root: {tmp_path / 'ignored'}",
            ]
        )
    )

    result = runner.invoke(
        app,
        [
            "provider-probe",
            "--manifest",
            str(manifest),
            "--artifact-root",
            str(tmp_path / "probe"),
        ],
    )

    assert result.exit_code == 1
    preflight = json.loads(
        (tmp_path / "probe" / "provider-probe-preflight.json").read_text()
    )
    assert preflight["auth_ready"] is False
    assert any("GOOGLE_CLOUD_PROJECT" in message for message in preflight["messages"])


def test_provider_probe_does_not_silently_use_api_key_fallback(tmp_path: Path) -> None:
    manifest = tmp_path / "api_key_probe.yaml"
    manifest.write_text(
        "\n".join(
            [
                'version: "1"',
                "provider:",
                "  kind: gemini",
                "  model: gemini-2.5-flash",
                "  auth:",
                "    kind: api-key",
                "    env_var: GEMINI_API_KEY",
                "benchmark:",
                "  kind: fixture",
                '  observation: "Legal Actions: left"',
                "  valid_actions:",
                "    - left",
                "runtime:",
                "  retry_limit: 0",
                "artifacts:",
                f"  root: {tmp_path / 'ignored'}",
            ]
        )
    )

    result = runner.invoke(
        app,
        [
            "provider-probe",
            "--manifest",
            str(manifest),
            "--artifact-root",
            str(tmp_path / "probe"),
        ],
    )

    assert result.exit_code == 1
    preflight = json.loads(
        (tmp_path / "probe" / "provider-probe-preflight.json").read_text()
    )
    assert any("auth.kind: oauth-adc" in message for message in preflight["messages"])


def test_provider_probe_accepts_gemini_cli_oauth_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli_module, "_gemini_cli_command_ready", lambda command: True)
    artifact_root = tmp_path / "provider-probe"

    result = runner.invoke(
        app,
        [
            "provider-probe",
            "--manifest",
            "manifests/provider_probe_gemini_othello.yaml",
            "--artifact-root",
            str(artifact_root),
            "--max-spend-usd",
            "1.00",
        ],
    )

    assert result.exit_code == 0
    preflight = json.loads((artifact_root / "provider-probe-preflight.json").read_text())
    summary = json.loads((artifact_root / "provider-probe-summary.json").read_text())
    assert preflight["auth_ready"] is True
    assert preflight["provider"] == "gemini-cli"
    assert preflight["auth_kind"] == "oauth-cli"
    assert summary["auth_kind"] == "oauth-cli"


def test_provider_probe_run_stops_when_usage_metadata_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "demo-project")
    monkeypatch.setattr(cli_module, "_provider_client_dependency_ready", lambda manifest: True)
    artifact_root = tmp_path / "probe"

    def fake_run_manifest_once(manifest) -> EpisodeResult:
        artifact_root.mkdir(parents=True, exist_ok=True)
        (artifact_root / "trace.json").write_text(
            json.dumps(
                [
                    {
                        "step_index": 0,
                        "attempt_index": 0,
                        "observation": "Available actions: '[roll]'",
                        "action": "[roll]",
                        "legal": True,
                        "provider": "gemini",
                        "metadata": {
                            "candidate_assessments": [
                                {"provider_metadata": {"candidate_index": 0}}
                            ]
                        },
                    }
                ]
            )
        )
        (artifact_root / "run-summary.json").write_text("{}")
        return EpisodeResult(
            run_id="fake-run",
            status="passed",
            retry_count=0,
            steps=1,
            final_action="[roll]",
            provider="gemini",
            benchmark="textarena",
            legal_attempts=1,
            illegal_attempts=0,
            legal_action_rate=1.0,
            total_reward=0.0,
        )

    monkeypatch.setattr(cli_module, "_run_manifest_once", fake_run_manifest_once)

    result = runner.invoke(
        app,
        [
            "provider-probe",
            "--manifest",
            "manifests/provider_probe_gemini_othello.yaml",
            "--artifact-root",
            str(artifact_root),
            "--run",
        ],
    )

    assert result.exit_code == 1
    assert "missing usage metadata" in result.output.lower()
    budget = json.loads((artifact_root / "provider-probe-budget.json").read_text())
    summary = json.loads((artifact_root / "provider-probe-summary.json").read_text())
    assert budget["status"] == "partial"
    assert budget["usage_metadata_present"] is False
    assert summary["status"] == "blocked"
    assert summary["usage_metadata_status"] == "partial"


def test_provider_probe_run_can_explicitly_allow_missing_usage_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli_module, "_provider_client_dependency_ready", lambda manifest: True)
    artifact_root = tmp_path / "probe"

    def fake_run_manifest_once(manifest) -> EpisodeResult:
        artifact_root.mkdir(parents=True, exist_ok=True)
        (artifact_root / "trace.json").write_text(
            json.dumps(
                [
                    {
                        "step_index": 0,
                        "attempt_index": 0,
                        "observation": "Available actions: '[roll]'",
                        "action": "[roll]",
                        "legal": True,
                        "provider": "gemini-cli",
                        "metadata": {
                            "candidate_assessments": [
                                {
                                    "provider_metadata": {
                                        "auth_kind": "oauth-cli",
                                        "candidate_index": 0,
                                    }
                                }
                            ]
                        },
                    }
                ]
            )
        )
        (artifact_root / "run-summary.json").write_text("{}")
        return EpisodeResult(
            run_id="fake-run",
            status="passed",
            retry_count=0,
            steps=1,
            final_action="[roll]",
            provider="gemini-cli",
            benchmark="textarena",
            legal_attempts=1,
            illegal_attempts=0,
            legal_action_rate=1.0,
            total_reward=0.0,
        )

    monkeypatch.setattr(cli_module, "_run_manifest_once", fake_run_manifest_once)

    result = runner.invoke(
        app,
        [
            "provider-probe",
            "--manifest",
            "manifests/provider_probe_gemini_othello.yaml",
            "--artifact-root",
            str(artifact_root),
            "--usage-policy",
            "allow-missing-once",
            "--run",
        ],
    )

    assert result.exit_code == 0
    assert "passed with partial usage metadata" in result.output.lower()
    budget = json.loads((artifact_root / "provider-probe-budget.json").read_text())
    summary = json.loads((artifact_root / "provider-probe-summary.json").read_text())
    assert budget["status"] == "partial"
    assert budget["usage_metadata_present"] is False
    assert summary["status"] == "passed"
    assert summary["usage_metadata_status"] == "partial"
    assert any("explicitly allowed" in message for message in summary["messages"])


def test_provider_report_summarizes_probe_roots(tmp_path: Path) -> None:
    probe_root = tmp_path / "live-001"
    probe_root.mkdir()
    (probe_root / "provider-probe-summary.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "dry_run": False,
                "provider": "gemini-cli",
                "model": "gemini-2.5-flash",
                "auth_kind": "oauth-cli",
                "artifact_root": str(probe_root),
                "max_spend_usd": 1.0,
                "actual_spend_usd": 0.0,
                "usage": {},
                "usage_metadata_status": "partial",
                "messages": ["Missing usage metadata was explicitly allowed."],
            }
        )
    )
    (probe_root / "provider-probe-budget.json").write_text(
        json.dumps(
            {
                "max_spend_usd": 1.0,
                "estimated_spend_usd": 0.0,
                "actual_spend_usd": 0.0,
                "status": "partial",
                "usage_metadata_present": False,
                "messages": [],
            }
        )
    )
    (probe_root / "run-summary.json").write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "status": "passed",
                "steps": 2,
                "retry_count": 0,
                "provider": "gemini-cli",
                "benchmark": "textarena",
                "legal_attempts": 2,
                "illegal_attempts": 0,
                "legal_action_rate": 1.0,
                "total_reward": 1.0,
            }
        )
    )
    (probe_root / "trace.json").write_text(
        json.dumps(
            [
                {
                    "step_index": 0,
                    "attempt_index": 0,
                    "observation": "Valid moves: '[0, 1]'",
                    "action": "[0, 1]",
                    "legal": True,
                    "provider": "gemini-cli",
                    "metadata": {},
                },
                {
                    "step_index": 1,
                    "attempt_index": 0,
                    "observation": "Valid moves: '[1, 0]'",
                    "action": "[1, 0]",
                    "legal": True,
                    "provider": "gemini-cli",
            "metadata": {},
        },
        {
            "step_index": 2,
            "attempt_index": 0,
            "observation": "\n".join(
                [
                    "Valid moves: '[1, 0]'",
                    "Scores - Black: 8, White: 5",
                    "No valid moves - you may have to skip.",
                    "Scores - Black: 9, White: 6",
                ]
            ),
            "action": "No valid moves for White. Skipping turn.",
            "legal": False,
            "provider": "gemini-cli",
            "metadata": {},
        },
    ]
        )
    )
    output_root = tmp_path / "report"

    result = runner.invoke(
        app,
        [
            "provider-report",
            "--probe-root",
            str(probe_root),
            "--output-root",
            str(output_root),
        ],
    )

    assert result.exit_code == 0
    assert "provider evidence report written" in result.output.lower()
    report = json.loads((output_root / "provider-evidence-report.json").read_text())
    markdown = (output_root / "provider-evidence-report.md").read_text()
    assert report["aggregate"]["total_runs"] == 1
    assert report["aggregate"]["probe_passed_runs"] == 1
    assert report["aggregate"]["episode_passed_runs"] == 1
    assert report["aggregate"]["mean_legal_action_rate"] == 1.0
    assert report["aggregate"]["usage_metadata_partial_runs"] == 1
    assert report["aggregate"]["current_verifier_illegal_attempts"] == 0
    assert report["aggregate"]["current_verifier_legal_attempts"] == 3
    assert report["runs"][0]["qualitative"]["illegal_steps"] == [
        {
            "step_index": 2,
            "attempt_index": 0,
            "action": "No valid moves for White. Skipping turn.",
            "recorded_legal": False,
            "current_verifier_action": "No valid moves for White. Skipping turn.",
            "current_verifier_legal": True,
            "valid_moves": [],
            "verifier_scores": {},
            "context": [
                "Scores - Black: 8, White: 5",
                "No valid moves - you may have to skip.",
                "Scores - Black: 9, White: 6",
            ],
        }
    ]
    assert report["runs"][0]["qualitative"]["step_history"] == [
        {
            "step_index": 0,
            "attempt_index": 0,
            "action": "[0, 1]",
            "recorded_legal": True,
            "current_verifier_legal": True,
            "current_verifier_action": "[0, 1]",
            "valid_moves": ["[0, 1]"],
            "scores": [],
            "board_tail": [],
            "verifier_scores": {},
        },
        {
            "step_index": 1,
            "attempt_index": 0,
            "action": "[1, 0]",
            "recorded_legal": True,
            "current_verifier_legal": True,
            "current_verifier_action": "[1, 0]",
            "valid_moves": ["[1, 0]"],
            "scores": [],
            "board_tail": [],
            "verifier_scores": {},
        },
        {
            "step_index": 2,
            "attempt_index": 0,
            "action": "No valid moves for White. Skipping turn.",
            "recorded_legal": False,
            "current_verifier_legal": True,
            "current_verifier_action": "No valid moves for White. Skipping turn.",
            "valid_moves": [],
            "scores": ["Scores - Black: 8, White: 5", "Scores - Black: 9, White: 6"],
            "board_tail": [],
            "verifier_scores": {},
        },
    ]
    assert "| live-001 | passed | passed | 1.000 | 0 | 0 | partial |" in markdown
    assert "### Step History - live-001" in markdown
    assert "| 0 | 0 | yes | yes | `[0, 1]` | `[0, 1]` |" in markdown
    assert "| 2 | 0 | no | yes | `No valid moves for White. Skipping turn.` | `none` |" in markdown


def test_provider_report_regrades_fixture_legal_actions() -> None:
    record = {
        "observation": "Toy step. Legal Actions: 'north'",
        "action": "north",
        "legal": True,
        "provider": "model-preflight",
        "metadata": {},
    }

    assert cli_module._extract_report_valid_moves(record["observation"]) == ["north"]
    assert cli_module._regrade_report_record(record) == {
        "action": "north",
        "legal": True,
    }
    assert cli_module._extract_report_valid_moves(
        "Toy step. Legal Actions: north. Return exactly one action."
    ) == ["north"]


def test_provider_probe_run_blocks_when_provider_dependency_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "demo-project")
    monkeypatch.setattr(cli_module, "_provider_client_dependency_ready", lambda manifest: False)
    artifact_root = tmp_path / "probe"

    result = runner.invoke(
        app,
        [
            "provider-probe",
            "--manifest",
            "manifests/provider_probe_gemini_othello.yaml",
            "--artifact-root",
            str(artifact_root),
            "--run",
        ],
    )

    assert result.exit_code == 1
    assert "missing provider dependency" in result.output.lower()
    budget = json.loads((artifact_root / "provider-probe-budget.json").read_text())
    summary = json.loads((artifact_root / "provider-probe-summary.json").read_text())
    assert budget["status"] == "blocked"
    assert summary["status"] == "blocked"
    assert any("Gemini CLI command" in message for message in summary["messages"])


def test_provider_probe_run_records_provider_runtime_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli_module, "_provider_client_dependency_ready", lambda manifest: True)
    artifact_root = tmp_path / "probe"

    def fail_run_manifest_once(manifest) -> EpisodeResult:
        raise RuntimeError("Gemini CLI provider failed: login required")

    monkeypatch.setattr(cli_module, "_run_manifest_once", fail_run_manifest_once)

    result = runner.invoke(
        app,
        [
            "provider-probe",
            "--manifest",
            "manifests/provider_probe_gemini_othello.yaml",
            "--artifact-root",
            str(artifact_root),
            "--run",
        ],
    )

    assert result.exit_code == 1
    assert "provider runtime error" in result.output.lower()
    summary = json.loads((artifact_root / "provider-probe-summary.json").read_text())
    budget = json.loads((artifact_root / "provider-probe-budget.json").read_text())
    assert summary["status"] == "failed"
    assert budget["status"] == "partial"
    assert any("login required" in message for message in summary["messages"])


@pytest.mark.parametrize(
    ("manifest", "artifact_name"),
    [
        ("manifests/textarena_tictactoe_smoke.yaml", "textarena-tictactoe-smoke"),
        ("manifests/textarena_othello_smoke.yaml", "textarena-othello-smoke"),
        ("manifests/textarena_pigdice_smoke.yaml", "textarena-pigdice-smoke"),
    ],
)
def test_verify_command_runs_textarena_manifest(
    tmp_path: Path,
    manifest: str,
    artifact_name: str,
) -> None:
    pytest.importorskip("textarena")
    result = runner.invoke(
        app,
        [
            "verify",
            "--manifest",
            manifest,
            "--artifact-root",
            str(tmp_path / artifact_name),
        ],
    )
    assert result.exit_code == 0
    assert "verification passed" in result.output.lower()


def test_verify_command_repeats_deterministic_runs_and_writes_summary(tmp_path: Path) -> None:
    manifest = tmp_path / "toy_verify.yaml"
    manifest.write_text(
        "\n".join(
            [
                'version: "1"',
                "provider:",
                "  kind: fixture",
                "  sequence:",
                "    - wrong",
                "    - north",
                "benchmark:",
                "  kind: fixture",
                "  script:",
                '    - observation: "Legal Actions: \'north\'"',
                "      valid_actions:",
                "        - north",
                "runtime:",
                "  retry_limit: 1",
                "verification:",
                "  deterministic_runs: 2",
                "  min_legal_action_rate: 0.5",
                "artifacts:",
                f"  root: {tmp_path / 'artifacts'}",
            ]
        )
    )

    result = runner.invoke(app, ["verify", "--manifest", str(manifest)])

    assert result.exit_code == 0
    assert "verification passed" in result.output.lower()
    assert (tmp_path / "artifacts" / "verification-summary.json").exists()


def test_verify_command_artifact_root_override_writes_only_under_override(
    tmp_path: Path,
) -> None:
    configured_root = tmp_path / "configured-artifacts"
    override_root = tmp_path / "override-artifacts"
    manifest = tmp_path / "toy_verify_override.yaml"
    manifest.write_text(
        "\n".join(
            [
                'version: "1"',
                "provider:",
                "  kind: fixture",
                "  sequence:",
                "    - wrong",
                "    - north",
                "benchmark:",
                "  kind: fixture",
                "  script:",
                '    - observation: "Legal Actions: \'north\'"',
                "      valid_actions:",
                "        - north",
                "runtime:",
                "  retry_limit: 1",
                "verification:",
                "  deterministic_runs: 2",
                "artifacts:",
                f"  root: {configured_root}",
            ]
        )
    )

    result = runner.invoke(
        app,
        ["verify", "--manifest", str(manifest), "--artifact-root", str(override_root)],
    )

    assert result.exit_code == 0
    assert "verification passed" in result.output.lower()
    assert not configured_root.exists()
    assert (override_root / "resolved-manifest.json").exists()
    assert (override_root / "verification-summary.json").exists()
    for run_id in ("run-01", "run-02"):
        assert (override_root / run_id / "resolved-manifest.json").exists()
        assert (override_root / run_id / "run-summary.json").exists()
        assert (override_root / run_id / "trace.json").exists()
    verification_summary = json.loads(
        (override_root / "verification-summary.json").read_text()
    )
    assert {
        Path(run["artifact_root"]) for run in verification_summary["runs"]
    } == {override_root / "run-01", override_root / "run-02"}
    resolved_manifest = json.loads((override_root / "resolved-manifest.json").read_text())
    assert Path(resolved_manifest["artifacts"]["root"]) == override_root
    assert f"root: {configured_root}" in manifest.read_text()


def test_verify_command_fails_when_legal_action_rate_is_below_threshold(tmp_path: Path) -> None:
    manifest = tmp_path / "toy_threshold.yaml"
    manifest.write_text(
        "\n".join(
            [
                'version: "1"',
                "provider:",
                "  kind: fixture",
                "  sequence:",
                "    - wrong",
                "    - north",
                "benchmark:",
                "  kind: fixture",
                "  script:",
                '    - observation: "Legal Actions: \'north\'"',
                "      valid_actions:",
                "        - north",
                "runtime:",
                "  retry_limit: 1",
                "verification:",
                "  deterministic_runs: 2",
                "  min_legal_action_rate: 0.75",
                "artifacts:",
                f"  root: {tmp_path / 'artifacts'}",
            ]
        )
    )

    result = runner.invoke(app, ["verify", "--manifest", str(manifest)])

    assert result.exit_code == 1
    assert "legal action rate" in result.output.lower()


def test_verify_command_fails_when_determinism_signature_changes(tmp_path: Path) -> None:
    candidate = tmp_path / "toggle_candidate.py"
    candidate.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "",
                "COUNTER = Path(__file__).with_suffix('.count')",
                "",
                "def propose_action(board: str) -> str:",
                "    del board",
                "    count = int(COUNTER.read_text()) if COUNTER.exists() else 0",
                "    COUNTER.write_text(str(count + 1))",
                "    return 'left' if count % 2 == 0 else 'right'",
                "",
                "def is_legal_action(board: str, action: str) -> bool:",
                "    del board",
                "    return action in {'left', 'right'}",
            ]
        )
    )
    manifest = tmp_path / "nondeterministic.yaml"
    manifest.write_text(
        "\n".join(
            [
                'version: "1"',
                "provider:",
                "  kind: candidate",
                f"  path: {candidate}",
                "benchmark:",
                "  kind: fixture",
                '  observation: "Legal Actions: left, right"',
                "  valid_actions:",
                "    - left",
                "    - right",
                "runtime:",
                "  retry_limit: 0",
                "verification:",
                "  deterministic_runs: 2",
                "artifacts:",
                f"  root: {tmp_path / 'artifacts'}",
            ]
        )
    )

    result = runner.invoke(app, ["verify", "--manifest", str(manifest)])

    assert result.exit_code == 1
    assert "determinism" in result.output.lower()


def test_campaign_command_runs_dev_and_holdout_manifests(tmp_path: Path) -> None:
    dev_manifest = tmp_path / "dev.yaml"
    dev_manifest.write_text(
        "\n".join(
            [
                'version: "1"',
                "provider:",
                "  kind: fixture",
                "benchmark:",
                "  kind: fixture",
                "  cases:",
                "    - case_id: dev-a",
                "      observation: |",
                "        [GAME]",
                "        Available Moves: '[0]', '[1]'",
                "        [GAME]",
                "        Available Moves: '[1]'",
                "      valid_actions:",
                "        - '[1]'",
                "runtime:",
                "  retry_limit: 1",
                "artifacts:",
                f"  root: {tmp_path / 'ignored-dev'}",
            ]
        )
    )
    holdout_manifest = tmp_path / "holdout.yaml"
    holdout_manifest.write_text(
        "\n".join(
            [
                'version: "1"',
                "provider:",
                "  kind: fixture",
                "benchmark:",
                "  kind: fixture",
                "  cases:",
                "    - case_id: holdout-a",
                "      observation: |",
                "        [GAME]",
                "        Available Moves: '[0]', '[1]'",
                "        [GAME]",
                "        Available Moves: '[1]'",
                "      valid_actions:",
                "        - '[1]'",
                "runtime:",
                "  retry_limit: 1",
                "artifacts:",
                f"  root: {tmp_path / 'ignored-holdout'}",
            ]
        )
    )

    result = runner.invoke(
        app,
        [
            "campaign",
            "--candidate",
            "tests/fixtures/candidates/ttt_first_historical_move.py",
            "--dev-manifest",
            str(dev_manifest),
            "--holdout-manifest",
            str(holdout_manifest),
            "--artifact-root",
            str(tmp_path / "campaign"),
            "--patch-text",
            "Parse the final Available Moves block and emit exactly one move.",
            "--max-iterations",
            "1",
        ],
    )

    assert result.exit_code == 0
    assert "campaign converged" in result.output.lower()
    assert (tmp_path / "campaign" / "campaign-summary.json").exists()
    assert (tmp_path / "campaign" / "candidate-lineage.jsonl").exists()


def test_campaign_command_fails_on_holdout_regression(tmp_path: Path) -> None:
    dev_manifest = tmp_path / "dev.yaml"
    dev_manifest.write_text(
        "\n".join(
            [
                'version: "1"',
                "provider:",
                "  kind: fixture",
                "benchmark:",
                "  kind: fixture",
                "  cases:",
                "    - case_id: dev-a",
                "      observation: |",
                "        [GAME]",
                "        Available Moves: '[0]', '[1]'",
                "        [GAME]",
                "        Available Moves: '[1]'",
                "      valid_actions:",
                "        - '[1]'",
                "runtime:",
                "  retry_limit: 1",
                "artifacts:",
                f"  root: {tmp_path / 'ignored-dev'}",
            ]
        )
    )
    holdout_manifest = tmp_path / "holdout.yaml"
    holdout_manifest.write_text(
        "\n".join(
            [
                'version: "1"',
                "provider:",
                "  kind: fixture",
                "benchmark:",
                "  kind: fixture",
                "  cases:",
                "    - case_id: holdout-a",
                "      observation: |",
                "        [GAME]",
                "        Available Moves: '[0]', '[1]'",
                "        [GAME]",
                "        Available Moves: '[1]'",
                "      valid_actions:",
                "        - '[2]'",
                "runtime:",
                "  retry_limit: 1",
                "artifacts:",
                f"  root: {tmp_path / 'ignored-holdout'}",
            ]
        )
    )

    result = runner.invoke(
        app,
        [
            "campaign",
            "--candidate",
            "tests/fixtures/candidates/ttt_first_historical_move.py",
            "--dev-manifest",
            str(dev_manifest),
            "--holdout-manifest",
            str(holdout_manifest),
            "--artifact-root",
            str(tmp_path / "campaign"),
            "--patch-text",
            "Parse the final Available Moves block and emit exactly one move.",
            "--max-iterations",
            "1",
        ],
    )

    assert result.exit_code == 1
    assert "holdout_regression" in result.output.lower()


def test_benchmark_command_runs_matrix_and_writes_reports(tmp_path: Path) -> None:
    latest_candidate = Path("tests/fixtures/candidates/ttt_first_available.py").resolve()
    historical_candidate = Path(
        "tests/fixtures/candidates/ttt_first_historical_move.py"
    ).resolve()
    dev_manifest = tmp_path / "dev.yaml"
    dev_manifest.write_text(
        "\n".join(
            [
                'version: "1"',
                "provider:",
                "  kind: fixture",
                "benchmark:",
                "  kind: fixture",
                "  cases:",
                "    - case_id: dev-a",
                "      observation: |",
                "        [GAME]",
                "        Available Moves: '[0]', '[1]'",
                "        [GAME]",
                "        Available Moves: '[1]'",
                "      valid_actions:",
                "        - '[1]'",
                "runtime:",
                "  retry_limit: 0",
                "artifacts:",
                f"  root: {tmp_path / 'ignored-dev'}",
            ]
        )
    )
    holdout_manifest = tmp_path / "holdout.yaml"
    holdout_manifest.write_text(
        "\n".join(
            [
                'version: "1"',
                "provider:",
                "  kind: fixture",
                "benchmark:",
                "  kind: fixture",
                "  cases:",
                "    - case_id: holdout-a",
                "      observation: |",
                "        [GAME]",
                "        Available Moves: '[0]', '[1]'",
                "        [GAME]",
                "        Available Moves: '[1]'",
                "      valid_actions:",
                "        - '[1]'",
                "runtime:",
                "  retry_limit: 0",
                "artifacts:",
                f"  root: {tmp_path / 'ignored-holdout'}",
            ]
        )
    )
    matrix = tmp_path / "matrix.yaml"
    matrix.write_text(
        "\n".join(
            [
                'version: "1"',
                "suites:",
                "  - label: dev",
                f"    manifest: {dev_manifest}",
                "  - label: holdout",
                f"    manifest: {holdout_manifest}",
                "candidates:",
                "  - label: latest",
                f"    path: {latest_candidate}",
                "  - label: historical",
                f"    path: {historical_candidate}",
                "ranking:",
                "  primary_metric: legal_action_rate",
                "  tie_breakers:",
                "    - total_reward",
                "    - retry_count",
                "artifacts:",
                f"  root: {tmp_path / 'benchmark-artifacts'}",
            ]
        )
    )

    result = runner.invoke(app, ["benchmark", "--matrix", str(matrix)])

    assert result.exit_code == 0
    assert "top candidate: latest" in result.output.lower()
    assert (tmp_path / "benchmark-artifacts" / "benchmark-summary.json").exists()
    assert (tmp_path / "benchmark-artifacts" / "leaderboard.md").exists()


def test_benchmark_command_artifact_root_override_writes_only_under_override(
    tmp_path: Path,
) -> None:
    latest_candidate = Path("tests/fixtures/candidates/ttt_first_available.py").resolve()
    configured_benchmark_root = tmp_path / "configured-benchmark-artifacts"
    configured_dev_root = tmp_path / "configured-dev-artifacts"
    configured_holdout_root = tmp_path / "configured-holdout-artifacts"
    override_root = tmp_path / "override-benchmark-artifacts"
    dev_manifest = tmp_path / "dev.yaml"
    dev_manifest.write_text(
        "\n".join(
            [
                'version: "1"',
                "provider:",
                "  kind: fixture",
                "benchmark:",
                "  kind: fixture",
                "  cases:",
                "    - case_id: dev-a",
                "      observation: |",
                "        [GAME]",
                "        Available Moves: '[0]', '[1]'",
                "        [GAME]",
                "        Available Moves: '[1]'",
                "      valid_actions:",
                "        - '[1]'",
                "runtime:",
                "  retry_limit: 0",
                "artifacts:",
                f"  root: {configured_dev_root}",
            ]
        )
    )
    holdout_manifest = tmp_path / "holdout.yaml"
    holdout_manifest.write_text(
        "\n".join(
            [
                'version: "1"',
                "provider:",
                "  kind: fixture",
                "benchmark:",
                "  kind: fixture",
                "  cases:",
                "    - case_id: holdout-a",
                "      observation: |",
                "        [GAME]",
                "        Available Moves: '[0]', '[1]'",
                "        [GAME]",
                "        Available Moves: '[1]'",
                "      valid_actions:",
                "        - '[1]'",
                "runtime:",
                "  retry_limit: 0",
                "artifacts:",
                f"  root: {configured_holdout_root}",
            ]
        )
    )
    matrix = tmp_path / "matrix.yaml"
    matrix.write_text(
        "\n".join(
            [
                'version: "1"',
                "suites:",
                "  - label: dev",
                f"    manifest: {dev_manifest}",
                "  - label: holdout",
                f"    manifest: {holdout_manifest}",
                "candidates:",
                "  - label: latest",
                f"    path: {latest_candidate}",
                "artifacts:",
                f"  root: {configured_benchmark_root}",
            ]
        )
    )

    result = runner.invoke(
        app,
        ["benchmark", "--matrix", str(matrix), "--artifact-root", str(override_root)],
    )

    assert result.exit_code == 0
    assert "top candidate: latest" in result.output.lower()
    assert not configured_benchmark_root.exists()
    assert not configured_dev_root.exists()
    assert not configured_holdout_root.exists()
    assert (override_root / "resolved-manifest.json").exists()
    assert (override_root / "benchmark-summary.json").exists()
    assert (override_root / "leaderboard.md").exists()
    assert (override_root / "latest" / "dev" / "suite-summary.json").exists()
    assert (override_root / "latest" / "dev" / "dev-a" / "run-summary.json").exists()
    assert (override_root / "latest" / "holdout" / "suite-summary.json").exists()
    assert (
        override_root / "latest" / "holdout" / "holdout-a" / "trace.json"
    ).exists()
    benchmark_summary = json.loads((override_root / "benchmark-summary.json").read_text())
    assert Path(benchmark_summary["artifact_root"]) == override_root
    assert benchmark_summary["candidates"][0]["artifact_root"] == str(
        override_root / "latest"
    )
    assert {
        Path(result["artifact_root"])
        for result in benchmark_summary["candidates"][0]["suite_results"]
    } == {override_root / "latest" / "dev", override_root / "latest" / "holdout"}
    assert f"root: {configured_benchmark_root}" in matrix.read_text()


def test_benchmark_command_fails_on_duplicate_candidate_labels(tmp_path: Path) -> None:
    first_available = Path("tests/fixtures/candidates/ttt_first_available.py").resolve()
    first_historical = Path(
        "tests/fixtures/candidates/ttt_first_historical_move.py"
    ).resolve()
    dev_manifest = tmp_path / "dev.yaml"
    dev_manifest.write_text(
        "\n".join(
            [
                'version: "1"',
                "provider:",
                "  kind: fixture",
                "benchmark:",
                "  kind: fixture",
                '  observation: "Legal Actions: north"',
                "  valid_actions:",
                "    - north",
                "runtime:",
                "  retry_limit: 0",
                "artifacts:",
                f"  root: {tmp_path / 'ignored-dev'}",
            ]
        )
    )
    matrix = tmp_path / "matrix.yaml"
    matrix.write_text(
        "\n".join(
            [
                'version: "1"',
                "suites:",
                "  - label: dev",
                f"    manifest: {dev_manifest}",
                "candidates:",
                "  - label: duplicate",
                f"    path: {first_available}",
                "  - label: duplicate",
                f"    path: {first_historical}",
                "artifacts:",
                f"  root: {tmp_path / 'benchmark-artifacts'}",
            ]
        )
    )

    result = runner.invoke(app, ["benchmark", "--matrix", str(matrix)])

    assert result.exit_code == 1
    assert "duplicate" in result.output.lower()
