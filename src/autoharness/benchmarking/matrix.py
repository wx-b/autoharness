# Requirement coverage:
# REQ-003-toy-benchmarking-001, REQ-003-toy-benchmarking-004
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from autoharness.config.load import load_manifest

from .models import BenchmarkMatrix


def load_benchmark_matrix(path: Path) -> BenchmarkMatrix:
    resolved_path = path.resolve()
    raw_data = yaml.safe_load(resolved_path.read_text()) or {}
    _validate_duplicate_labels(raw_data)
    matrix = BenchmarkMatrix.model_validate(
        {
            **raw_data,
            "path": resolved_path,
            "suites": [
                {
                    **suite,
                    "manifest": _resolve_relative(resolved_path, suite["manifest"]),
                }
                for suite in raw_data.get("suites", [])
            ],
            "candidates": [
                {
                    **candidate,
                    "path": _resolve_relative(resolved_path, candidate["path"]),
                }
                for candidate in raw_data.get("candidates", [])
            ],
            "artifacts": {
                **raw_data.get("artifacts", {}),
                "root": _resolve_relative(resolved_path, raw_data["artifacts"]["root"]),
            }
            if "artifacts" in raw_data and "root" in raw_data["artifacts"]
            else raw_data.get("artifacts", {}),
        }
    )
    _validate_paths(matrix)
    _validate_fixture_suites(matrix)
    return matrix


def _resolve_relative(base_path: Path, raw_path: Any) -> Path:
    path = Path(str(raw_path))
    if path.is_absolute():
        return path
    return (base_path.parent / path).resolve()


def _validate_paths(matrix: BenchmarkMatrix) -> None:
    for suite in matrix.suites:
        _ensure_readable_file(
            suite.manifest,
            description=f"Suite manifest path is not readable for suite '{suite.label}'",
        )
    for candidate in matrix.candidates:
        _ensure_readable_file(
            candidate.path,
            description=f"Candidate path is not readable for candidate '{candidate.label}'",
        )


def _ensure_readable_file(path: Path, *, description: str) -> None:
    if not path.exists():
        raise ValueError(f"{description}: {path}")
    if not path.is_file():
        raise ValueError(f"{description}: {path}")
    try:
        with path.open("rb") as handle:
            handle.read(1)
    except OSError as exc:
        raise ValueError(f"{description}: {path}") from exc


def _validate_fixture_suites(matrix: BenchmarkMatrix) -> None:
    for suite in matrix.suites:
        manifest = load_manifest(suite.manifest)
        if manifest.benchmark.kind != "fixture" or not manifest.benchmark.cases:
            raise ValueError(
                f"Suite manifest must define a fixture suite with cases: {suite.manifest}"
            )


def _validate_duplicate_labels(raw_data: dict[str, Any]) -> None:
    _ensure_unique_labels(
        labels=[
            str(suite.get("label", "")).strip()
            for suite in raw_data.get("suites", [])
            if isinstance(suite, dict)
        ],
        kind="suite",
    )
    _ensure_unique_labels(
        labels=[
            str(candidate.get("label", "")).strip()
            for candidate in raw_data.get("candidates", [])
            if isinstance(candidate, dict)
        ],
        kind="candidate",
    )


def _ensure_unique_labels(*, labels: list[str], kind: str) -> None:
    seen: set[str] = set()
    for label in labels:
        if not label:
            continue
        if label in seen:
            raise ValueError(f"Duplicate {kind} label: {label}")
        seen.add(label)
