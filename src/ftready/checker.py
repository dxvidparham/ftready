"""Merge dependency data with compatibility results (PyPI-first, ft-checker enrichment)."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime

from ftready.constants import _DEFAULT_MAX_WORKERS, STATUS_UNKNOWN, FTDb
from ftready.models import PackageResult
from ftready.scraper import check_pypi_batch

_logger = logging.getLogger(__name__)

_VERSION_RE = re.compile(r"^(?:↳ )?(\d[\d.]*(?:\.?\w+)*)$")


def _extract_pinned_version(requested: str) -> str:
    """Extract an exact version from a lock-file version string (e.g. ``"↳ 1.26.4"`` → ``"1.26.4"``)."""
    m = _VERSION_RE.match(requested.strip())
    return m.group(1) if m else ""


def build_results(
    deps: dict[str, str],
    ft_db: FTDb | None = None,
    *,
    direct_names: set[str] | None = None,
    pypi_fallback: bool = True,
) -> list[PackageResult]:
    """
    Build compatibility results — PyPI-first, ft-checker as enrichment.

    1. Query the PyPI JSON API for all packages in parallel (primary).
    2. Overlay ft-checker.com data when available (enrichment).
       ft-checker can downgrade a PyPI "Success" to "Failed" if tests
       actually fail, or upgrade a "Not tested" to "Success" for
       pure-Python packages that pass tests without shipping ``cp313t`` wheels.

    :param deps: Mapping from :func:`~ftready.parser.load_dependencies`.
    :param ft_db: Optional mapping from :func:`~ftready.scraper.fetch_ftchecker_db`.
    :param direct_names: Names not in this set are marked as transitive.
    :param pypi_fallback: Query PyPI API for wheel tag detection (default ``True``).
    :return: Sorted list of :class:`PackageResult` -- direct deps first.
    """
    names = list(deps.keys())
    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")

    # Only query PyPI for packages NOT already in ft-checker
    ft_covered = set(ft_db.keys()) if ft_db else set()
    pypi_needed = [n for n in names if n not in ft_covered] if pypi_fallback else []

    # Extract pinned versions from lock-file deps for version-specific queries
    pinned_versions: dict[str, str] = {}
    for name in pypi_needed:
        ver = _extract_pinned_version(deps[name])
        if ver:
            pinned_versions[name] = ver

    if pypi_needed:
        sample = ", ".join(pypi_needed[:8])
        ellipsis = f", … ({len(pypi_needed) - 8} more)" if len(pypi_needed) > 8 else ""
        _logger.info("[pypi] Querying PyPI for %d packages: %s%s", len(pypi_needed), sample, ellipsis)
        pypi_results = check_pypi_batch(pypi_needed, versions=pinned_versions, max_workers=_DEFAULT_MAX_WORKERS)
    else:
        pypi_results = {}

    # Step 2 — Build results, enriching with ft-checker when available
    results: list[PackageResult] = []
    for name, requested in deps.items():
        is_direct = direct_names is None or name in direct_names
        pypi = pypi_results.get(name)
        ft_entry = ft_db.get(name) if ft_db else None

        if ft_entry is not None:
            # ft-checker data wins: it has actual test results
            # still use PyPI pure-python info if available
            pure = bool(pypi.get("is_pure_python")) if pypi else False
            results.append(
                PackageResult(
                    name=name,
                    requested=requested,
                    status_313t=ft_entry.get("3.13t", STATUS_UNKNOWN),
                    status_314t=ft_entry.get("3.14t", STATUS_UNKNOWN),
                    source="ft-checker.com",
                    checked_at=ft_entry.get("checked_at", ""),
                    is_direct=is_direct,
                    is_pure_python=pure,
                )
            )
        elif pypi is not None:
            results.append(
                PackageResult(
                    name=name,
                    requested=requested,
                    status_313t=str(pypi["3.13t"]),
                    status_314t=str(pypi["3.14t"]),
                    source="pypi",
                    checked_at=today,
                    is_direct=is_direct,
                    is_pure_python=bool(pypi.get("is_pure_python")),
                )
            )
        else:
            results.append(PackageResult(name=name, requested=requested, is_direct=is_direct))

    results.sort(key=lambda r: (not r.is_direct, r.name))
    return results
