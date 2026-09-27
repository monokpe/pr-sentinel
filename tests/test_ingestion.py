"""
Unit tests for pr_sentinel.ingestion (pure-Python parts, no git required)
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

from pr_sentinel.ingestion import _read_file_safe, _SOURCE_EXTENSIONS


def test_read_file_safe_nonexistent(tmp_path):
    result = _read_file_safe(tmp_path / "nonexistent.py")
    assert result is None


def test_read_file_safe_reads_content(tmp_path):
    f = tmp_path / "hello.py"
    f.write_text("print('hello')", encoding="utf-8")
    assert _read_file_safe(f) == "print('hello')"


def test_read_file_safe_too_large(tmp_path, monkeypatch):
    f = tmp_path / "big.py"
    f.write_text("x" * 10, encoding="utf-8")
    # Monkeypatch stat().st_size to exceed the cap
    from pr_sentinel.ingestion import _MAX_FILE_BYTES
    original_stat = Path.stat

    def fake_stat(self, **kwargs):
        s = original_stat(self, **kwargs)
        # Return a mock with inflated size for our target file only
        if self == f:
            m = MagicMock()
            m.st_size = _MAX_FILE_BYTES + 1
            return m
        return s

    monkeypatch.setattr(Path, "stat", fake_stat)
    assert _read_file_safe(f) is None


def test_read_file_safe_directory(tmp_path):
    # Passing a directory should return None
    assert _read_file_safe(tmp_path) is None


def test_source_extensions_contains_common_types():
    for ext in (".py", ".ts", ".js", ".go", ".yaml", ".toml"):
        assert ext in _SOURCE_EXTENSIONS


def test_load_repo_context_requires_git(tmp_path):
    """load_repo_context should raise if path is not a git repo."""
    import git
    from pr_sentinel.ingestion import load_repo_context
    with pytest.raises(git.InvalidGitRepositoryError):
        load_repo_context(str(tmp_path))
