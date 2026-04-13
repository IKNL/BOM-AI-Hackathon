"""Tests for shared backend path resolution."""

from pathlib import Path

from paths import DATA_DIR, resolve_repo_path


def test_resolve_repo_path_makes_data_paths_repo_relative():
    assert Path(resolve_repo_path("data/chromadb")) == DATA_DIR / "chromadb"


def test_resolve_repo_path_keeps_absolute_paths_unchanged():
    absolute = "/tmp/custom.db"
    assert resolve_repo_path(absolute) == absolute
