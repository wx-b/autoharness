from __future__ import annotations

# Requirement coverage:
# REQ-006-provider-backed-probe-cost-auth-policy-016
from pathlib import Path
from typing import Any

import yaml

from .models import ArtifactConfig, Manifest


def load_manifest(path: Path) -> Manifest:
    data = yaml.safe_load(path.read_text()) or {}
    manifest = Manifest.model_validate(data)
    artifact_root = manifest.artifacts.root
    if not artifact_root.is_absolute():
        artifact_root = (path.parent / artifact_root).resolve()
        manifest = manifest.model_copy(
            update={"artifacts": ArtifactConfig(root=artifact_root)}
        )
    provider_path = manifest.provider.path
    if provider_path is not None and not provider_path.is_absolute():
        manifest = manifest.model_copy(
            update={
                "provider": manifest.provider.model_copy(
                    update={"path": (path.parent / provider_path).resolve()}
                )
            }
        )
    config_path = manifest.provider.options.get("config_path")
    if isinstance(config_path, str):
        resolved_config_path = Path(config_path).expanduser()
        if not resolved_config_path.is_absolute():
            resolved_config_path = (path.parent / resolved_config_path).resolve()
        manifest = manifest.model_copy(
            update={
                "provider": manifest.provider.model_copy(
                    update={
                        "options": {
                            **manifest.provider.options,
                            "config_path": resolved_config_path,
                        }
                    }
                )
            }
        )
    return manifest


def manifest_to_data(manifest: Manifest) -> dict[str, Any]:
    return manifest.model_dump(mode="json")
