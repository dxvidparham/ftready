"""Merge dependency data with compatibility results (PyPI-first, ft-checker enrichment)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from ftready.constants import _DEFAULT_MAX_WORKERS, STATUS_UNKNOWN, FTDb
from ftready.models import PackageResult
from ftready.scraper import check_pypi_batch

_logger = logging.getLogger(__name__)


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

    # Step 1 — PyPI as primary source
    if pypi_fallback and names:
        sample = ", ".join(names[:8])
        ellipsis = f", … ({len(names) - 8} more)" if len(names) > 8 else ""
        _logger.info("[pypi] Querying PyPI for %d packages: %s%s", len(names), sample, ellipsis)
        pypi_results = check_pypi_batch(names, max_workers=_DEFAULT_MAX_WORKERS)
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
            results.append(
                PackageResult(
                    name=name,
                    requested=requested,
                    status_313t=ft_entry.get("3.13t", STATUS_UNKNOWN),
                    status_314t=ft_entry.get("3.14t", STATUS_UNKNOWN),
                    source="ft-checker.com",
                    checked_at=ft_entry.get("checked_at", ""),
                    is_direct=is_direct,
                )
            )
        elif pypi is not None:
            results.append(
                PackageResult(
                    name=name,
                    requested=requested,
                    status_313t=pypi["3.13t"],
                    status_314t=pypi["3.14t"],
                    source="pypi",
                    checked_at=today,
                    is_direct=is_direct,
                )
            )
        else:
            results.append(PackageResult(name=name, requested=requested, is_direct=is_direct))

    results.sort(key=lambda r: (not r.is_direct, r.name))
    return results
