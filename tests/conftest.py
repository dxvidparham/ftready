"""Shared fixtures for ftready tests."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from ftready.constants import FTDb

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_pyproject(tmp_path: Path) -> Path:
    """Create a minimal pyproject.toml with PEP 621 dependencies."""
    content = """\
[project]
name = "example"
version = "1.0.0"
dependencies = [
    "numpy>=1.26",
    "requests>=2.31",
    "click>=8.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]
"""
    p = tmp_path / "pyproject.toml"
    p.write_text(content)
    return p


@pytest.fixture
def poetry_pyproject(tmp_path: Path) -> Path:
    """Create a minimal pyproject.toml with Poetry-style dependencies."""
    content = """\
[tool.poetry.dependencies]
python = "^3.11"
numpy = "^1.26"
requests = "^2.31"
local-pkg = {path = "../local-pkg"}
wheel-pkg = {path = "lib/pkg.whl"}
git-pkg = {git = "https://github.com/org/repo.git"}

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
ruff = "^0.4"
"""
    p = tmp_path / "pyproject.toml"
    p.write_text(content)
    return p


@pytest.fixture
def sample_lockfile(tmp_path: Path) -> Path:
    """Create a minimal poetry.lock file."""
    content = """\
[[package]]
name = "numpy"
version = "1.26.4"

[[package]]
name = "requests"
version = "2.31.0"

[[package]]
name = "urllib3"
version = "2.2.1"

[[package]]
name = "charset-normalizer"
version = "3.3.2"
"""
    p = tmp_path / "poetry.lock"
    p.write_text(content)
    return p


@pytest.fixture
def sample_ft_db() -> FTDb:
    """Return a small ft-checker.com database for testing."""
    return {
        "numpy": {"3.13t": "Success", "3.14t": "Success", "checked_at": "2026-01-15"},
        "requests": {"3.13t": "Success", "3.14t": "Unknown", "checked_at": "2026-01-15"},
        "click": {"3.13t": "Failed", "3.14t": "Failed", "checked_at": "2026-01-15"},
    }


@pytest.fixture
def empty_ft_db() -> FTDb:
    """Return an empty ft-checker database."""
    return {}


@pytest.fixture
def cache_file(tmp_path: Path) -> Path:
    """Return a path for a temporary cache file."""
    return tmp_path / ".ft_cache.json"
