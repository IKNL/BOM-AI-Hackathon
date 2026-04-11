"""Shared filesystem path helpers for backend runtime code."""

from __future__ import annotations

from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent
TEAM_DIR = BACKEND_DIR.parent
REPO_ROOT = TEAM_DIR.parent.parent
DATA_DIR = REPO_ROOT / "data"


def resolve_repo_path(path_value: str) -> str:
    """Resolve relative storage paths from the repo root.

    Runtime code is often executed from `teams/team5/backend`, while persisted
    data lives under the repository root `data/` directory. Resolving relative
    paths from the repo root keeps ingestion and query-time code aligned.
    """
    path = Path(path_value)
    if path.is_absolute():
        return str(path)
    return str(REPO_ROOT / path)
