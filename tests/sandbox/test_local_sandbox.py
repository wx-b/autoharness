from __future__ import annotations

from pathlib import Path

from autoharness.sandbox.local import GeneratedCandidateSandbox, SandboxPolicy


def test_local_sandbox_executes_allowed_candidate_and_writes_audit(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.py"
    candidate.write_text("def propose_action(board):\n    return '[0]'\n")
    sandbox = GeneratedCandidateSandbox(audit_log_path=tmp_path / "audit.jsonl")

    result = sandbox.run_candidate(
        candidate_path=candidate,
        observation="Available Moves: '[0]'",
        case_id="allowed",
    )

    assert result.status == "passed"
    assert result.action == "[0]"
    assert "allowed" in (tmp_path / "audit.jsonl").read_text()


def test_local_sandbox_denies_adversarial_cases(tmp_path: Path) -> None:
    sandbox = GeneratedCandidateSandbox(
        audit_log_path=tmp_path / "audit.jsonl",
        policy=SandboxPolicy(timeout_seconds=0.2, output_limit_bytes=1024),
    )

    results = sandbox.run_adversarial_cases(tmp_path / "cases")

    assert results["env_read"].status == "denied"
    assert results["filesystem_write"].status == "denied"
    assert results["subprocess"].status == "denied"
    assert results["network"].status == "denied"
    assert results["infinite_loop"].reason == "timeout"
    assert results["memory_output_abuse"].reason == "output_limit"
