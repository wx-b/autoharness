# Requirement coverage: REQ-004-expanded-toy-benchmarking-artifact-policy-002
# Requirement coverage: REQ-004-expanded-toy-benchmarking-artifact-policy-003
# Requirement coverage: REQ-004-expanded-toy-benchmarking-artifact-policy-009
from __future__ import annotations

from pathlib import Path

import yaml

from autoharness.config.load import load_manifest

EXPECTED_FAILURE_FAMILIES = {
    "alias-family",
    "exact-format",
    "retry-sensitive",
    "scripted",
    "stale-history",
    "whitespace-format",
}


def _load_case_ids(path: str) -> list[str]:
    manifest = load_manifest(Path(path))
    return [case.case_id for case in manifest.benchmark.cases]


def _case_family(case_id: str) -> str:
    for suite_marker in ("-dev-", "-holdout-"):
        if suite_marker in case_id:
            return case_id.split(suite_marker, 1)[0]
    raise AssertionError(f"case_id must include a suite marker: {case_id}")


def test_toy_benchmark_dev_manifest_loads_expected_fixture_suite() -> None:
    manifest = load_manifest(Path("manifests/toy_benchmark_dev.yaml"))

    assert manifest.provider.kind == "fixture"
    assert manifest.benchmark.kind == "fixture"
    assert len(manifest.benchmark.cases) == 36
    assert any(len(case.script) > 1 for case in manifest.benchmark.cases)


def test_toy_benchmark_holdout_manifest_loads_expected_fixture_suite() -> None:
    manifest = load_manifest(Path("manifests/toy_benchmark_holdout.yaml"))

    assert manifest.provider.kind == "fixture"
    assert manifest.benchmark.kind == "fixture"
    assert len(manifest.benchmark.cases) == 18
    assert any(len(case.script) > 1 for case in manifest.benchmark.cases)


def test_toy_benchmark_manifests_have_unique_disjoint_case_ids() -> None:
    dev_case_ids = _load_case_ids("manifests/toy_benchmark_dev.yaml")
    holdout_case_ids = _load_case_ids("manifests/toy_benchmark_holdout.yaml")

    assert len(dev_case_ids) == len(set(dev_case_ids))
    assert len(holdout_case_ids) == len(set(holdout_case_ids))
    assert set(dev_case_ids).isdisjoint(holdout_case_ids)


def test_toy_benchmark_manifests_cover_exactly_six_failure_families() -> None:
    case_ids = _load_case_ids("manifests/toy_benchmark_dev.yaml") + _load_case_ids(
        "manifests/toy_benchmark_holdout.yaml"
    )
    families = {_case_family(case_id) for case_id in case_ids}

    assert families == EXPECTED_FAILURE_FAMILIES
    assert any(case_id.startswith("alias-family-") for case_id in case_ids)


def test_toy_benchmark_matrix_includes_robust_and_control_candidates() -> None:
    matrix = yaml.safe_load(Path("manifests/toy_benchmark_matrix.yaml").read_text())

    assert [candidate["label"] for candidate in matrix["candidates"]] == [
        "robust",
        "latest",
        "historical",
        "fragile",
        "negative",
    ]
    assert {
        "REQ-004-expanded-toy-benchmarking-artifact-policy-003",
        "REQ-004-expanded-toy-benchmarking-artifact-policy-004",
    }.issubset(matrix["requirements"])
