"""Merge dependency data with compatibility results."""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime

from ftready.constants import _DEFAULT_MAX_WORKERS, STATUS_UNKNOWN, FTDb
from ftready.models import PackageResult
from ftready.scraper import check_pypi_freethreaded


def build_results(
    deps: dict[str, str],
    ft_db: FTDb,
    *,
    direct_names: set[str] | None = None,
    pypi_fallback: bool = True,
    verbose: bool = False,
) -> list[PackageResult]:
    """
    Merge project dependencies with compatibility data.

    Packages present in *ft_db* are resolved immediately. Those absent are
    queried against the PyPI JSON API in parallel.

    :param deps: Mapping from :func:`~ftready.parser.load_dependencies`.
    :param ft_db: Mapping from :func:`~ftready.scraper.fetch_ftchecker_db`.
    :param direct_names: Names not in this set are marked as transitive.
    :param pypi_fallback: Fall back to PyPI API for packages absent from ft-checker.
    :param verbose: Print progress to stderr.
    :return: Sorted list of :class:`PackageResult` — direct deps first.
    """
    results: list[PackageResult] = []
    fallback: list[tuple[str, str, bool]] = []

    for name, requested in deps.items():
        is_direct = direct_names is None or name in direct_names
        if entry := ft_db.get(name):
            results.append(
                PackageResult(
                    name=name,
                    requested=requested,
                    status_313t=entry.get("3.13t", STATUS_UNKNOWN),
                    status_314t=entry.get("3.14t", STATUS_UNKNOWN),
                    source="ft-checker.com",
                    checked_at=entry.get("checked_at", ""),
                    is_direct=is_direct,
                )
            )
        elif pypi_fallback:
            fallback.append((name, requested, is_direct))
        else:
            results.append(PackageResult(name=name, requested=requested, is_direct=is_direct))

    if fallback:
        if verbose:
            sample = ", ".join(n for n, _, _ in fallback[:8])
            ellipsis = f", … ({len(fallback) - 8} more)" if len(fallback) > 8 else ""
            print(f"[pypi-fallback] Querying PyPI for {len(fallback)} packages: {sample}{ellipsis}", file=sys.stderr)
        today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
        with ThreadPoolExecutor(max_workers=_DEFAULT_MAX_WORKERS) as pool:
            future_map = {pool.submit(check_pypi_freethreaded, n): (n, req, d) for n, req, d in fallback}
            for future in as_completed(future_map):
                name, requested, is_direct = future_map[future]
                p = future.result()
                results.append(
                    PackageResult(
                        name=name,
                        requested=requested,
                        status_313t=p["3.13t"],
                        status_314t=p["3.14t"],
                        source="pypi-fallback",
                        checked_at=today,
                        is_direct=is_direct,
                    )
                )

    results.sort(key=lambda r: (not r.is_direct, r.name))
    return results
