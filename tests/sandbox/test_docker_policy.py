# Requirement coverage: REQ-001-bootstrap-001
import subprocess

from autoharness.sandbox.docker import DockerSandboxPolicy, docker_runtime_ready


def test_docker_policy_disables_network_and_mounts_output_only(tmp_path) -> None:
    policy = DockerSandboxPolicy(output_dir=tmp_path)
    args = policy.build_run_args(image="python:3.12-alpine")
    assert "--network=none" in args
    assert any(str(tmp_path) in arg for arg in args)


def test_docker_runtime_ready_returns_false_when_probe_run_fails(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(
        args: list[str], *, check: bool, capture_output: bool, text: bool
    ) -> subprocess.CompletedProcess[str]:
        del check, capture_output, text
        calls.append(args)
        if args[:3] == ["docker", "version"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[:4] == ["docker", "image", "inspect", "python:3.12-alpine"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        return subprocess.CompletedProcess(args, 1, "", "runc unavailable")

    monkeypatch.setattr("autoharness.sandbox.docker.subprocess.run", fake_run)

    assert docker_runtime_ready("python:3.12-alpine") is False
    assert calls[-1] == [
        "docker",
        "run",
        "--rm",
        "--network=none",
        "python:3.12-alpine",
        "true",
    ]


def test_docker_runtime_ready_returns_true_when_probe_run_succeeds(monkeypatch) -> None:
    def fake_run(
        args: list[str], *, check: bool, capture_output: bool, text: bool
    ) -> subprocess.CompletedProcess[str]:
        del check, capture_output, text
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr("autoharness.sandbox.docker.subprocess.run", fake_run)

    assert docker_runtime_ready("python:3.12-alpine") is True
