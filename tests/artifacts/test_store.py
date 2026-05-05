from autoharness.artifacts.models import RunSummary
from autoharness.artifacts.store import ArtifactStore


def test_store_writes_run_summary(tmp_path) -> None:
    store = ArtifactStore(tmp_path)
    summary = RunSummary(
        run_id="run-1",
        status="passed",
        steps=1,
        retry_count=0,
        provider="fixture",
        benchmark="fixture",
    )
    path = store.write_summary(summary)
    assert path.exists()
    assert "run-1" in path.read_text()
