from __future__ import annotations

# Requirement coverage:
# REQ-006-provider-backed-probe-cost-auth-policy-016
import json
from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner

import autoharness.cli as cli_module
from autoharness.cli import app

runner = CliRunner()


def test_model_preflight_manifest_loads_group_and_config_path(tmp_path: Path) -> None:
    config_path = tmp_path / "model-preflight.yaml"
    manifest_path = tmp_path / "model_preflight_probe.yaml"
    manifest_path.write_text(
        "\n".join(
            [
                'version: "1"',
                "provider:",
                "  kind: model-preflight",
                "  model: local_fast",
                "  auth:",
                "    kind: none",
                "  options:",
                f"    config_path: {config_path}",
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

    from autoharness.config.load import load_manifest

    manifest = load_manifest(manifest_path)

    assert manifest.provider.kind == "model-preflight"
    assert manifest.provider.model == "local_fast"
    assert manifest.provider.options["config_path"] == config_path


def test_provider_probe_accepts_model_preflight_dry_run(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        cli_module,
        "_model_preflight_config_ready",
        lambda config_path, group: (True, [f"ModelPreflight group is ready: {group}."]),
    )
    manifest_path = tmp_path / "model_preflight_probe.yaml"
    manifest_path.write_text(
        "\n".join(
            [
                'version: "1"',
                "provider:",
                "  kind: model-preflight",
                "  model: local_fast",
                "  auth:",
                "    kind: none",
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
    artifact_root = tmp_path / "probe"

    result = runner.invoke(
        app,
        [
            "provider-probe",
            "--manifest",
            str(manifest_path),
            "--artifact-root",
            str(artifact_root),
            "--max-spend-usd",
            "1.00",
        ],
    )

    assert result.exit_code == 0
    summary = json.loads((artifact_root / "provider-probe-summary.json").read_text())
    preflight = json.loads((artifact_root / "provider-probe-preflight.json").read_text())
    assert preflight["auth_ready"] is True
    assert preflight["provider"] == "model-preflight"
    assert summary["status"] == "dry-run"
    assert summary["provider"] == "model-preflight"


def test_committed_model_preflight_manifests_load() -> None:
    from autoharness.config.load import load_manifest

    free_manifest = load_manifest(Path("manifests/provider_probe_model_preflight_free.yaml"))
    local_manifest = load_manifest(Path("manifests/provider_probe_model_preflight_local.yaml"))

    assert free_manifest.provider.kind == "model-preflight"
    assert free_manifest.provider.model == "free_reasoning"
    assert local_manifest.provider.kind == "model-preflight"
    assert local_manifest.provider.model == "local_fast"
    assert free_manifest.benchmark.kind == "textarena"
    assert local_manifest.benchmark.kind == "textarena"


def test_model_preflight_preflight_checks_manifest_group(monkeypatch) -> None:
    class FakeConfigModule:
        @staticmethod
        def load_config(config_path):  # type: ignore[no-untyped-def]
            return SimpleNamespace(
                deployments=[
                    SimpleNamespace(
                        name="default",
                        group="free_reasoning",
                        enabled=True,
                        required=True,
                        api_key_env="DEFAULT_GROUP_KEY",
                    ),
                    SimpleNamespace(
                        name="local-llm",
                        group="local_fast",
                        enabled=True,
                        required=True,
                        api_key_env=None,
                    ),
                ]
            )

    monkeypatch.setattr(cli_module, "import_module", lambda name: FakeConfigModule)

    ready, messages = cli_module._model_preflight_config_ready(None, group="local_fast")

    assert ready is True
    assert any("local_fast" in message for message in messages)


def test_model_preflight_preflight_blocks_missing_selected_group_env(monkeypatch) -> None:
    class FakeConfigModule:
        @staticmethod
        def load_config(config_path):  # type: ignore[no-untyped-def]
            return SimpleNamespace(
                deployments=[
                    SimpleNamespace(
                        name="free-provider",
                        group="free_fast",
                        enabled=True,
                        required=True,
                        api_key_env="FREE_FAST_KEY",
                    ),
                ]
            )

    monkeypatch.setattr(cli_module, "import_module", lambda name: FakeConfigModule)
    monkeypatch.delenv("FREE_FAST_KEY", raising=False)

    ready, messages = cli_module._model_preflight_config_ready(None, group="free_fast")

    assert ready is False
    assert any("FREE_FAST_KEY" in message for message in messages)


def test_model_preflight_preflight_uses_doctor_diagnostic_when_available(monkeypatch) -> None:
    class FakeConfigModule:
        @staticmethod
        def load_config(config_path):  # type: ignore[no-untyped-def]
            return SimpleNamespace(deployments=[])

    class FakeCliModule:
        @staticmethod
        def _doctor_diagnostic(config, *, group, provider=None):  # type: ignore[no-untyped-def]
            return {
                "status": "error",
                "error_code": "GROUP_NOT_FOUND",
                "selected_group": group,
                "enabled_groups": ["free_reasoning"],
                "missing_env_vars": [],
                "disabled_matching_providers": [],
                "next_commands": ["mpf models"],
            }

    def fake_import_module(name: str):  # type: ignore[no-untyped-def]
        if name == "model_preflight.cli":
            return FakeCliModule
        return FakeConfigModule

    monkeypatch.setattr(cli_module, "import_module", fake_import_module)

    ready, messages = cli_module._model_preflight_config_ready(None, group="local_fast")

    assert ready is False
    assert any("GROUP_NOT_FOUND" in message for message in messages)
    assert any("Enabled ModelPreflight groups: free_reasoning." in message for message in messages)
    assert any("Next commands: mpf models" in message for message in messages)
