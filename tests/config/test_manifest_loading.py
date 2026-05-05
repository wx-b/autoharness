from pathlib import Path

from autoharness.config.load import load_manifest


def test_load_manifest_reads_provider_and_benchmark() -> None:
    manifest = load_manifest(Path("manifests/offline_smoke.yaml"))
    assert manifest.provider.kind == "fixture"
    assert manifest.benchmark.kind == "fixture"
    assert manifest.runtime.retry_limit == 2
    assert manifest.artifacts.root.is_absolute()


def test_load_manifest_reads_script_and_verification_fields(tmp_path: Path) -> None:
    manifest_path = tmp_path / "toy.yaml"
    manifest_path.write_text(
        "\n".join(
            [
                'version: "1"',
                "provider:",
                "  kind: fixture",
                "  sequence:",
                "    - north",
                "benchmark:",
                "  kind: fixture",
                "  script:",
                '    - observation: "Legal Actions: \'north\'"',
                "      valid_actions:",
                "        - north",
                "runtime:",
                "  retry_limit: 0",
                "verification:",
                "  deterministic_runs: 2",
                "  min_legal_action_rate: 1.0",
                "artifacts:",
                "  root: artifacts/toy",
            ]
        )
    )

    manifest = load_manifest(manifest_path)

    assert manifest.benchmark.script
    assert manifest.benchmark.script[0].valid_actions == ["north"]
    assert manifest.verification.deterministic_runs == 2
    assert manifest.verification.min_legal_action_rate == 1.0


def test_load_manifest_reads_fixture_suite_cases(tmp_path: Path) -> None:
    manifest_path = tmp_path / "suite.yaml"
    manifest_path.write_text(
        "\n".join(
            [
                'version: "1"',
                "provider:",
                "  kind: fixture",
                "  response_text: north",
                "benchmark:",
                "  kind: fixture",
                "  cases:",
                "    - case_id: case-north",
                '      observation: "Legal Actions: \'north\'"',
                "      valid_actions:",
                "        - north",
                "    - case_id: case-east",
                '      observation: "Legal Actions: \'east\'"',
                "      valid_actions:",
                "        - east",
                "runtime:",
                "  retry_limit: 0",
                "artifacts:",
                "  root: artifacts/suite",
            ]
        )
    )

    manifest = load_manifest(manifest_path)

    assert len(manifest.benchmark.cases) == 2
    assert manifest.benchmark.cases[0].case_id == "case-north"
    assert manifest.benchmark.cases[1].valid_actions == ["east"]
