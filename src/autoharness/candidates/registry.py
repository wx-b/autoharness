from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType

from pydantic import BaseModel, Field

from autoharness.candidates.contracts import (
    CandidateContractError,
    build_candidate_signature,
    load_candidate_module,
    validate_candidate_contract,
)


class CandidateRegistryRecord(BaseModel):
    registry_version: str = "1"
    candidate_id: str
    path: str
    source_sha256: str
    promoted_from: str
    provenance: dict[str, object] = Field(default_factory=dict)
    minimum_metrics: dict[str, float] = Field(default_factory=dict)


class CandidateRegistry:
    def __init__(self, root: Path, *, version: str = "1") -> None:
        self.root = root
        self.version = version
        self.candidates_root = self.root / "candidates"
        self.manifest_path = self.root / "candidate-registry.json"
        self.candidates_root.mkdir(parents=True, exist_ok=True)

    def promote(
        self,
        source_path: Path,
        *,
        candidate_id: str | None = None,
        provenance: dict[str, object] | None = None,
        minimum_metrics: dict[str, float] | None = None,
    ) -> CandidateRegistryRecord:
        if not source_path.exists():
            raise CandidateContractError(f"Candidate source does not exist: {source_path}")
        source_hash = self.hash(source_path)
        resolved_id = candidate_id or f"candidate-{source_hash[:12]}"
        module = load_candidate_module(source_path)
        validate_candidate_contract(module)

        existing = self.show(resolved_id)
        destination = self.candidates_root / f"{resolved_id}.py"
        if existing is not None:
            if existing.source_sha256 != source_hash:
                raise CandidateContractError(
                    f"Candidate id {resolved_id} already exists with a different hash"
                )
            return existing

        shutil.copy2(source_path, destination)
        record = CandidateRegistryRecord(
            registry_version=self.version,
            candidate_id=resolved_id,
            path=destination.name,
            source_sha256=source_hash,
            promoted_from=_portable_path(source_path),
            provenance=provenance or {},
            minimum_metrics=minimum_metrics or {},
        )
        records = self.list()
        records.append(record)
        self._write(records)
        return record

    def list(self) -> list[CandidateRegistryRecord]:
        if not self.manifest_path.exists():
            return []
        payload = json.loads(self.manifest_path.read_text())
        return [CandidateRegistryRecord.model_validate(item) for item in payload["candidates"]]

    def show(self, candidate_id: str) -> CandidateRegistryRecord | None:
        for record in self.list():
            if record.candidate_id == candidate_id:
                return record
        return None

    def load(self, candidate_id: str) -> ModuleType:
        record = self.show(candidate_id)
        if record is None:
            raise CandidateContractError(f"Unknown candidate id: {candidate_id}")
        return load_candidate_module(self.path_for(record))

    def export(self, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(self.model_dump(), indent=2) + "\n")
        return output_path

    def hash(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def provenance(self, candidate_id: str) -> dict[str, object]:
        record = self.show(candidate_id)
        if record is None:
            raise CandidateContractError(f"Unknown candidate id: {candidate_id}")
        return dict(record.provenance)

    def signature(self, candidate_id: str) -> dict[str, object]:
        record = self.show(candidate_id)
        if record is None:
            raise CandidateContractError(f"Unknown candidate id: {candidate_id}")
        module = self.load(candidate_id)
        return build_candidate_signature(
            module=module,
            candidate_id=candidate_id,
            path=self.path_for(record),
            source_sha256=record.source_sha256,
        ).model_dump(mode="json")

    def path_for(self, record: CandidateRegistryRecord) -> Path:
        return self.candidates_root / record.path

    def model_dump(self) -> dict[str, object]:
        return {
            "registry_version": self.version,
            "candidates": [record.model_dump(mode="json") for record in self.list()],
        }

    def _write(self, records: Sequence[CandidateRegistryRecord]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        payload = {
            "registry_version": self.version,
            "candidates": [record.model_dump(mode="json") for record in records],
        }
        self.manifest_path.write_text(json.dumps(payload, indent=2) + "\n")


def _portable_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.name
