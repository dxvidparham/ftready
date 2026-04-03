"""Data models for ftready."""

from __future__ import annotations

from dataclasses import dataclass

from ftready.constants import STATUS_SUCCESS, STATUS_UNKNOWN


@dataclass
class PackageResult:
    """
    Compatibility result for a single dependency.

    :param name: Canonical (normalised) package name.
    :param requested: Version constraint / resolved version string.
    :param status_313t: ft-checker.com / PyPI status for Python 3.13t.
    :param status_314t: ft-checker.com / PyPI status for Python 3.14t.
    :param source: Data source (``"ft-checker.com"``, ``"pypi-fallback"``, or ``"not-found"``).
    :param checked_at: ISO-8601 timestamp or date of last verification.
    :param is_direct: ``True`` for direct project dependencies; ``False`` for transitive.
    """

    name: str
    requested: str
    status_313t: str = STATUS_UNKNOWN
    status_314t: str = STATUS_UNKNOWN
    source: str = "not-found"
    checked_at: str = ""
    is_direct: bool = True


@dataclass(frozen=True)
class Stats:
    """Pre-computed summary counters for the report footer."""

    total: int
    direct_total: int
    ok_313: int
    ok_314: int
    ok_313_direct: int
    ok_314_direct: int


def compute_stats(results: list[PackageResult]) -> Stats:
    """Compute all report counters in a single pass over *results*."""
    total = direct_total = ok_313 = ok_314 = ok_313_direct = ok_314_direct = 0
    for r in results:
        total += 1
        s13, s14 = r.status_313t == STATUS_SUCCESS, r.status_314t == STATUS_SUCCESS
        ok_313 += s13
        ok_314 += s14
        if r.is_direct:
            direct_total += 1
            ok_313_direct += s13
            ok_314_direct += s14
    return Stats(total, direct_total, ok_313, ok_314, ok_313_direct, ok_314_direct)
