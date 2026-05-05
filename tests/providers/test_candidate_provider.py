# Requirement coverage: REQ-001-bootstrap-001
from pathlib import Path

import pytest

from autoharness.providers.candidate import CandidateModuleProvider
from autoharness.sandbox.docker import (
    docker_binary_available,
    docker_image_present,
    docker_runtime_ready,
)


def test_candidate_module_provider_generates_action_from_candidate() -> None:
    provider = CandidateModuleProvider(
        path=Path("tests/fixtures/candidates/ttt_first_available.py")
    )
    result = provider.generate("Available Moves: '[4]', '[8]'")
    assert result.text == "[4]"
    assert result.provider == "candidate"
    assert result.metadata["candidate_legal"] is True


def test_candidate_module_provider_uses_latest_available_moves() -> None:
    provider = CandidateModuleProvider(
        path=Path("tests/fixtures/candidates/ttt_first_available.py")
    )
    prompt = "\n".join(
        [
            "Available Moves: '[0]', '[1]', '[2]'",
            "[Player 0] [0]",
            "Available Moves: '[1]', '[2]'",
        ]
    )
    result = provider.generate(prompt)
    assert result.text == "[1]"
    assert result.metadata["candidate_legal"] is True


def test_docker_candidate_provider_generates_action_when_image_is_present() -> None:
    if not docker_binary_available() or not docker_image_present("python:3.12-alpine"):
        pytest.skip("docker image python:3.12-alpine is not available locally")
    if not docker_runtime_ready("python:3.12-alpine"):
        pytest.skip("docker runtime is not ready for python:3.12-alpine")

    from autoharness.providers.candidate import DockerCandidateProvider

    provider = DockerCandidateProvider(
        path=Path("tests/fixtures/candidates/ttt_first_available.py"),
        image="python:3.12-alpine",
    )
    result = provider.generate("Available Moves: '[4]', '[8]'")
    assert result.text == "[4]"
    assert result.provider == "candidate-docker"
    assert result.metadata["candidate_legal"] is True
