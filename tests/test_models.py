"""Tests for data models."""

from __future__ import annotations

from ftready.constants import STATUS_FAILED, STATUS_SUCCESS, STATUS_UNKNOWN
from ftready.models import PackageResult, compute_stats


class TestPackageResult:
    def test_defaults(self):
        r = PackageResult(name="numpy", requested=">=1.26")
        assert r.status_313t == STATUS_UNKNOWN
        assert r.status_314t == STATUS_UNKNOWN
        assert r.source == "not-found"
        assert r.checked_at == ""
        assert r.is_direct is True


class TestComputeStats:
    def test_empty(self):
        stats = compute_stats([])
        assert stats.total == 0

    def test_counts_direct_and_transitive(self):
        results = [
            PackageResult("a", "1.0", STATUS_SUCCESS, STATUS_SUCCESS, is_direct=True),
            PackageResult("b", "2.0", STATUS_FAILED, STATUS_SUCCESS, is_direct=False),
        ]
        stats = compute_stats(results)
        assert stats.total == 2
        assert stats.direct_total == 1
        assert stats.ok_313 == 1
        assert stats.ok_314 == 2
        assert stats.ok_313_direct == 1
        assert stats.ok_314_direct == 1
