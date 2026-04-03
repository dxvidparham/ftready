"""Tests for pyproject.toml and poetry.lock parsing."""

from __future__ import annotations

from pathlib import Path

from ftready.parser import (
    _normalise_name,
    _strip_version_specifier,
    load_dependencies,
    load_lockfile_dependencies,
)


class TestNormaliseName:
    def test_lowercase(self):
        assert _normalise_name("NumPy") == "numpy"

    def test_underscores_to_hyphens(self):
        assert _normalise_name("scikit_learn") == "scikit-learn"

    def test_dots_to_hyphens(self):
        assert _normalise_name("zope.interface") == "zope-interface"

    def test_multiple_separators(self):
        assert _normalise_name("My..Package__Name") == "my-package-name"


class TestStripVersionSpecifier:
    def test_simple_version(self):
        assert _strip_version_specifier("numpy>=1.26") == "numpy"

    def test_complex_specifier(self):
        assert _strip_version_specifier("numpy>=1.26,<2 ; platform_system=='Linux'") == "numpy"

    def test_extras(self):
        assert _strip_version_specifier("package[extra1,extra2]>=1.0") == "package"

    def test_bare_name(self):
        assert _strip_version_specifier("requests") == "requests"


class TestLoadDependencies:
    def test_pep621_dependencies(self, sample_pyproject: Path):
        deps = load_dependencies(sample_pyproject)
        assert "numpy" in deps
        assert "requests" in deps
        assert "click" in deps

    def test_pep621_includes_optional_deps(self, sample_pyproject: Path):
        """PEP 621 optional-dependencies are always included (they are extras, not dev deps)."""
        deps = load_dependencies(sample_pyproject)
        assert "pytest" in deps

    def test_poetry_dependencies(self, poetry_pyproject: Path):
        deps = load_dependencies(poetry_pyproject)
        assert "numpy" in deps
        assert "requests" in deps
        assert "local-pkg" in deps
        assert deps["local-pkg"] == "(local path)"
        assert deps["wheel-pkg"] == "(local wheel)"
        assert "git-pkg" in deps

    def test_poetry_excludes_python(self, poetry_pyproject: Path):
        deps = load_dependencies(poetry_pyproject)
        assert "python" not in deps

    def test_poetry_include_dev(self, poetry_pyproject: Path):
        deps = load_dependencies(poetry_pyproject, include_dev=True)
        assert "pytest" in deps
        assert "ruff" in deps

    def test_poetry_exclude_dev_by_default(self, poetry_pyproject: Path):
        deps = load_dependencies(poetry_pyproject, include_dev=False)
        assert "pytest" not in deps


class TestLoadLockfileDependencies:
    def test_loads_all_packages(self, sample_lockfile: Path):
        direct = {"numpy", "requests"}
        deps = load_lockfile_dependencies(sample_lockfile, direct)
        assert "numpy" in deps
        assert "requests" in deps
        assert "urllib3" in deps
        assert "charset-normalizer" in deps

    def test_marks_transitive_with_prefix(self, sample_lockfile: Path):
        direct = {"numpy", "requests"}
        deps = load_lockfile_dependencies(sample_lockfile, direct)
        assert deps["numpy"] == "1.26.4"
        assert deps["requests"] == "2.31.0"
        assert deps["urllib3"].startswith("↳")
        assert deps["charset-normalizer"].startswith("↳")

    def test_empty_lockfile(self, tmp_path: Path):
        lock = tmp_path / "poetry.lock"
        lock.write_text("")
        deps = load_lockfile_dependencies(lock, set())
        assert deps == {}
