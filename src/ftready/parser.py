"""Parse ``pyproject.toml`` and ``poetry.lock`` for dependency information."""

from __future__ import annotations

import re
import tomllib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def _normalise_name(name: str) -> str:
    """Normalise a package name to its PyPI canonical form (lowercase, hyphens)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _strip_version_specifier(dep: str) -> str:
    """
    Strip PEP 508 version specifiers and extras from a dependency string.

    :param dep: Raw PEP 508 dependency string, e.g. ``"numpy>=1.26,<2 ; platform=..."``
    :return: Bare package name.
    """
    dep = dep.split(";", maxsplit=1)[0].strip()
    return re.split(r"[\[>=<!~^]", dep)[0].strip()


def _summarise_poetry_spec(spec: object) -> str:
    """
    Return a concise human-readable version string from a Poetry dependency spec.

    :param spec: The raw value from ``[tool.poetry.dependencies]`` — either a
                 version string or a dict with keys like ``path``, ``version``, etc.
    :return: A short string such as ``"^1.2"`` or ``"(local path)"`` or ``"(local wheel)"``.
    """
    if isinstance(spec, str):
        return spec
    if isinstance(spec, dict):
        spec_dict = dict(spec)
        if "path" in spec_dict:
            path = str(spec_dict["path"])
            return "(local wheel)" if path.endswith(".whl") else "(local path)"
        if "version" in spec_dict:
            return str(spec_dict["version"])
        if "git" in spec_dict:
            return f"(git: {spec_dict['git']})"
    return str(spec)


def load_lockfile_dependencies(
    lock_path: Path,
    direct_names: set[str],
) -> dict[str, str]:
    """
    Parse ``poetry.lock`` and return a mapping of every resolved package to its pinned version.

    :param lock_path: Path to the ``poetry.lock`` file.
    :param direct_names: Set of normalised direct-dependency names.
    :return: ``{normalised_package_name: resolved_version}`` for every package in the lock file.
    """
    with lock_path.open("rb") as fh:
        data = tomllib.load(fh)

    result: dict[str, str] = {}
    for pkg in data.get("package", []):
        raw_name = pkg.get("name", "")
        if not raw_name:
            continue
        name = _normalise_name(raw_name)
        version = pkg.get("version", "")
        prefix = "" if name in direct_names else "↳ "
        result[name] = f"{prefix}{version}"

    return result


def load_requirements(path: Path) -> dict[str, str]:
    """
    Parse a ``requirements.txt``-style file and return a dependency mapping.

    Handles inline comments, version specifiers, extras, environment markers,
    and skips directives (``-r``, ``-c``, ``-e``, ``--index-url``, etc.).

    :param path: Path to the requirements file.
    :return: ``{normalised_package_name: raw_line}`` dict.
    """
    result: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", "-")):
            continue
        # Strip inline comment (safe here: package lines don't embed bare #)
        line_no_comment = line.split("#", maxsplit=1)[0].strip()
        if not line_no_comment:
            continue
        name = _normalise_name(_strip_version_specifier(line_no_comment))
        if name:
            result[name] = line_no_comment
    return result


def load_dependencies(pyproject_path: Path, *, include_dev: bool = False) -> dict[str, str]:
    """
    Parse ``pyproject.toml`` and return a mapping of normalised package name to version spec.

    :param pyproject_path: Path to the ``pyproject.toml`` file.
    :param include_dev: When ``True``, also include ``[tool.poetry.group.*.dependencies]``.
    :return: ``{normalised_package_name: version_spec}`` dict.
    """
    with pyproject_path.open("rb") as fh:
        data = tomllib.load(fh)

    result: dict[str, str] = {}

    # [project.dependencies] (PEP 621 style)
    for dep in data.get("project", {}).get("dependencies", []):
        name = _normalise_name(_strip_version_specifier(dep))
        result[name] = dep

    # [project.optional-dependencies]
    for group_deps in data.get("project", {}).get("optional-dependencies", {}).values():
        for dep in group_deps:
            name = _normalise_name(_strip_version_specifier(dep))
            result[name] = dep

    # [tool.poetry.dependencies] (Poetry-specific)
    for pkg, spec in data.get("tool", {}).get("poetry", {}).get("dependencies", {}).items():
        if pkg.lower() == "python":
            continue
        name = _normalise_name(pkg)
        result[name] = _summarise_poetry_spec(spec)

    if include_dev:
        groups = data.get("tool", {}).get("poetry", {}).get("group", {})
        for group_data in groups.values():
            for pkg, spec in group_data.get("dependencies", {}).items():
                name = _normalise_name(pkg)
                result.setdefault(name, _summarise_poetry_spec(spec))

    return result
