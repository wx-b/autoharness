from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from pydantic import BaseModel, Field


class SandboxPolicy(BaseModel):
    allowed_imports: set[str] = Field(default_factory=lambda: {"json", "math", "re"})
    timeout_seconds: float = 1.0
    output_limit_bytes: int = 8192
    memory_limit_bytes: int = 128 * 1024 * 1024


class SandboxExecutionResult(BaseModel):
    case_id: str
    status: str
    reason: str
    action: str | None = None
    returncode: int | None = None
    stdout_bytes: int = 0
    stderr: str = ""


class GeneratedCandidateSandbox:
    def __init__(
        self,
        *,
        audit_log_path: Path,
        policy: SandboxPolicy | None = None,
    ) -> None:
        self.audit_log_path = audit_log_path
        self.policy = policy or SandboxPolicy()
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)

    def run_candidate(
        self,
        *,
        candidate_path: Path,
        observation: str,
        case_id: str,
    ) -> SandboxExecutionResult:
        static_denial = self._static_denial(candidate_path.read_text())
        if static_denial is not None:
            result = SandboxExecutionResult(
                case_id=case_id,
                status="denied",
                reason=static_denial,
            )
            self._audit(result)
            return result

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            driver_path = tmp_path / "driver.py"
            observation_path = tmp_path / "observation.txt"
            observation_path.write_text(observation)
            driver_path.write_text(_driver_script())
            command = [
                sys.executable,
                "-I",
                str(driver_path),
                str(candidate_path),
                str(observation_path),
            ]
            try:
                completed = subprocess.run(
                    command,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=self.policy.timeout_seconds,
                    cwd=tmp_path,
                    env={},
                    preexec_fn=_limit_resources(self.policy.memory_limit_bytes)
                    if os.name == "posix"
                    else None,
                )
            except subprocess.TimeoutExpired as exc:
                result = SandboxExecutionResult(
                    case_id=case_id,
                    status="denied",
                    reason="timeout",
                    stdout_bytes=len(exc.stdout or b""),
                    stderr=str(exc.stderr or ""),
                )
                self._audit(result)
                return result

        stdout = completed.stdout or ""
        if len(stdout.encode()) > self.policy.output_limit_bytes:
            result = SandboxExecutionResult(
                case_id=case_id,
                status="denied",
                reason="output_limit",
                returncode=completed.returncode,
                stdout_bytes=len(stdout.encode()),
                stderr=(completed.stderr or "")[:512],
            )
            self._audit(result)
            return result
        if completed.returncode != 0:
            result = SandboxExecutionResult(
                case_id=case_id,
                status="denied",
                reason="runtime_error",
                returncode=completed.returncode,
                stdout_bytes=len(stdout.encode()),
                stderr=(completed.stderr or "")[:512],
            )
            self._audit(result)
            return result
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            result = SandboxExecutionResult(
                case_id=case_id,
                status="denied",
                reason="invalid_json_output",
                returncode=completed.returncode,
                stdout_bytes=len(stdout.encode()),
                stderr=(completed.stderr or "")[:512],
            )
            self._audit(result)
            return result

        result = SandboxExecutionResult(
            case_id=case_id,
            status="passed",
            reason="ok",
            action=str(payload.get("action", "")),
            returncode=completed.returncode,
            stdout_bytes=len(stdout.encode()),
            stderr=(completed.stderr or "")[:512],
        )
        self._audit(result)
        return result

    def run_adversarial_cases(self, root: Path) -> dict[str, SandboxExecutionResult]:
        root.mkdir(parents=True, exist_ok=True)
        cases = {
            "env_read": (
                "# ruff: noqa: I001\n"
                "import os\n\n"
                "def propose_action(board):\n"
                "    return os.environ.get('HOME', '')\n"
            ),
            "filesystem_write": (
                "# ruff: noqa: I001\n"
                "def propose_action(board):\n"
                "    open('/tmp/autoharness-outside-write', 'w').write('x')\n"
                "    return '[0]'\n"
            ),
            "subprocess": (
                "# ruff: noqa: I001\n"
                "import subprocess\n\ndef propose_action(board):\n"
                "    subprocess.run(['true'])\n    return '[0]'\n"
            ),
            "network": (
                "# ruff: noqa: I001\n"
                "import socket\n\ndef propose_action(board):\n"
                "    socket.socket()\n    return '[0]'\n"
            ),
            "infinite_loop": (
                "# ruff: noqa: I001\n"
                "def propose_action(board):\n    while True:\n        pass\n"
            ),
            "memory_output_abuse": (
                "# ruff: noqa: I001\n"
                "def propose_action(board):\n"
                "    return 'x' * 100000\n"
            ),
        }
        results: dict[str, SandboxExecutionResult] = {}
        for case_id, source in cases.items():
            path = root / f"{case_id}.py"
            path.write_text(source)
            results[case_id] = self.run_candidate(
                candidate_path=path,
                observation="Available Moves: '[0]'",
                case_id=case_id,
            )
        return results

    def _static_denial(self, source: str) -> str | None:
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            return f"syntax_error:{exc.msg}"
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                    continue
                names = [alias.name for alias in getattr(node, "names", [])]
                if isinstance(node, ast.ImportFrom) and node.module:
                    names.append(node.module)
                for name in names:
                    root = name.split(".", 1)[0]
                    if root not in self.policy.allowed_imports:
                        return f"denied_import:{root}"
            if isinstance(node, ast.Attribute) and node.attr in {"environ", "getenv"}:
                return f"denied_attribute:{node.attr}"
            if isinstance(node, ast.Call):
                called_name = _called_name(node.func)
                if called_name in {"open", "exec", "eval", "__import__"}:
                    if called_name == "open" and _open_is_read_only(node):
                        continue
                    return f"denied_call:{called_name}"
                if called_name.startswith(("subprocess.", "socket.", "requests.", "urllib.")):
                    return f"denied_call:{called_name}"
        return None

    def _audit(self, result: SandboxExecutionResult) -> None:
        with self.audit_log_path.open("a") as handle:
            handle.write(result.model_dump_json() + "\n")


def _called_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _called_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _open_is_read_only(node: ast.Call) -> bool:
    if len(node.args) < 2:
        return True
    mode = node.args[1]
    if not isinstance(mode, ast.Constant) or not isinstance(mode.value, str):
        return False
    return all(flag not in mode.value for flag in ["w", "a", "+", "x"])


def _limit_resources(memory_limit_bytes: int):
    def limit() -> None:
        try:
            import resource

            resource.setrlimit(resource.RLIMIT_AS, (memory_limit_bytes, memory_limit_bytes))
            resource.setrlimit(resource.RLIMIT_CPU, (1, 1))
        except Exception:
            return

    return limit


def _driver_script() -> str:
    return """
import importlib.util
import json
import pathlib
import sys

candidate_path = pathlib.Path(sys.argv[1])
observation = pathlib.Path(sys.argv[2]).read_text()
spec = importlib.util.spec_from_file_location("candidate", candidate_path)
if spec is None or spec.loader is None:
    raise RuntimeError("could not load candidate")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
action = module.propose_action(observation)
print(json.dumps({"action": action}), end="")
"""
