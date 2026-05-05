# Requirement coverage: REQ-001-bootstrap-001
from __future__ import annotations

import subprocess
from pathlib import Path


def docker_binary_available() -> bool:
    completed = subprocess.run(
        ["docker", "version"],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def docker_image_present(image: str) -> bool:
    completed = subprocess.run(
        ["docker", "image", "inspect", image],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def docker_runtime_ready(image: str) -> bool:
    if not docker_binary_available() or not docker_image_present(image):
        return False
    completed = subprocess.run(
        ["docker", "run", "--rm", "--network=none", image, "true"],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


class DockerSandboxPolicy:
    def __init__(
        self,
        *,
        output_dir: Path,
        memory_limit: str = "256m",
        cpu_limit: str = "1.0",
    ) -> None:
        self.output_dir = output_dir
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit

    def build_run_args(
        self,
        *,
        image: str,
        command: list[str] | None = None,
        input_dir: Path | None = None,
    ) -> list[str]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        args = [
            "docker",
            "run",
            "--rm",
            "--network=none",
            "--memory",
            self.memory_limit,
            "--cpus",
            self.cpu_limit,
            "-v",
            f"{self.output_dir}:/sandbox-output",
        ]
        if input_dir is not None:
            args.extend(["-v", f"{input_dir}:/sandbox-input:ro"])
        args.append(image)
        if command:
            args.extend(command)
        return args


class DockerSandboxRunner:
    def __init__(self, policy: DockerSandboxPolicy) -> None:
        self.policy = policy

    def run(
        self,
        *,
        image: str,
        command: list[str],
        input_dir: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        args = self.policy.build_run_args(image=image, command=command, input_dir=input_dir)
        completed = subprocess.run(args, check=False, capture_output=True, text=True)
        return completed
