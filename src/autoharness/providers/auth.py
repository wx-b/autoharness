from __future__ import annotations

import os


class AuthenticationError(RuntimeError):
    """Raised when provider authentication is unavailable."""


def read_api_key(env_var: str) -> str:
    value = os.getenv(env_var)
    if not value:
        raise AuthenticationError(f"Missing required API key in environment variable {env_var}")
    return value


def read_google_project(default: str | None = None) -> str | None:
    return (
        os.getenv("GOOGLE_CLOUD_PROJECT")
        or os.getenv("GCLOUD_PROJECT")
        or default
    )
