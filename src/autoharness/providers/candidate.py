# Requirement coverage: REQ-001-bootstrap-001
from __future__ import annotations

import json
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import cast

from autoharness.candidates.contracts import load_candidate_module, validate_action_verifier_module
from autoharness.sandbox.docker import DockerSandboxPolicy, DockerSandboxRunner

from .base import Provider, ProviderResult


class CandidateModuleProvider(Provider):
    def __init__(self, *, path: Path, model: str = "candidate-module") -> None:
        self.path = path
        self.model = model
        self._module = self._load_module(path)

    def _load_module(self, path: Path) -> ModuleType:
        module = load_candidate_module(path)
        validate_action_verifier_module(module)
        return module

    def generate(self, prompt: str) -> ProviderResult:
        propose_action = cast(Callable[[str], str], self._module.propose_action)
        is_legal_action = cast(
            Callable[[str, str], bool], self._module.is_legal_action
        )
        action = propose_action(prompt)
        candidate_legal = is_legal_action(prompt, action)
        return ProviderResult(
            text=action,
            provider="candidate",
            model=self.model,
            metadata={
                "candidate_path": str(self.path),
                "candidate_legal": candidate_legal,
            },
        )


class DockerCandidateProvider(Provider):
    def __init__(
        self,
        *,
        path: Path,
        image: str = "python:3.12-alpine",
        model: str = "candidate-docker",
    ) -> None:
        self.path = path
        self.image = image
        self.model = model

    def generate(self, prompt: str) -> ProviderResult:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            input_dir = tmp_path / "input"
            output_dir = tmp_path / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            shutil.copy2(self.path, input_dir / "candidate.py")
            (input_dir / "prompt.txt").write_text(prompt)
            (input_dir / "driver.py").write_text(_docker_driver_script())

            policy = DockerSandboxPolicy(output_dir=output_dir)
            runner = DockerSandboxRunner(policy)
            completed = runner.run(
                image=self.image,
                command=[
                    "python3",
                    "/sandbox-input/driver.py",
                    "/sandbox-input/candidate.py",
                    "/sandbox-input/prompt.txt",
                    "/sandbox-output/result.json",
                ],
                input_dir=input_dir,
            )
            if completed.returncode != 0:
                raise RuntimeError(
                    f"Docker candidate execution failed with exit code {completed.returncode}: "
                    f"{completed.stderr.strip()}"
                )

            result_path = output_dir / "result.json"
            payload = json.loads(result_path.read_text())
            return ProviderResult(
                text=payload["action"],
                provider="candidate-docker",
                model=self.model,
                metadata={
                    "candidate_path": str(self.path),
                    "candidate_legal": payload["candidate_legal"],
                    "image": self.image,
                },
            )


def _docker_driver_script() -> str:
    return """
import importlib.util
import inspect
import json
import pathlib
import sys


def load_module(path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate(module):
    expected = {
        "propose_action": ["board"],
        "is_legal_action": ["board", "action"],
    }
    for name, args in expected.items():
        fn = getattr(module, name, None)
        if fn is None:
            raise RuntimeError(f"Missing required function: {name}")
        signature = inspect.signature(fn)
        if list(signature.parameters.keys()) != args:
            raise RuntimeError(f"Invalid signature for {name}")


candidate_path = pathlib.Path(sys.argv[1])
prompt_path = pathlib.Path(sys.argv[2])
output_path = pathlib.Path(sys.argv[3])
prompt = prompt_path.read_text()
module = load_module(candidate_path)
validate(module)
action = module.propose_action(prompt)
candidate_legal = module.is_legal_action(prompt, action)
output_path.write_text(json.dumps({"action": action, "candidate_legal": candidate_legal}))
"""
