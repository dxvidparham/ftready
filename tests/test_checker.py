"""Tests for the checker module — building results from deps + ft_db."""

from __future__ import annotations

from ftready.checker import build_results
from ftready.constants import STATUS_FAILED, STATUS_SUCCESS, STATUS_UNKNOWN


class TestBuildResults:
    def test_matches_from_ft_db(self, sample_ft_db):
        deps = {"numpy": ">=1.26", "requests": ">=2.31"}
        results = build_results(deps, sample_ft_db, pypi_fallback=False)

        by_name = {r.name: r for r in results}
        assert by_name["numpy"].status_313t == STATUS_SUCCESS
        assert by_name["numpy"].source == "ft-checker.com"
        assert by_name["requests"].status_313t == STATUS_SUCCESS

    def test_unknown_without_any_source(self):
        deps = {"unknown-pkg": ">=1.0"}
        results = build_results(deps, None, pypi_fallback=False)

        assert len(results) == 1
        assert results[0].status_313t == STATUS_UNKNOWN
        assert results[0].source == "not-found"

    def test_pypi_primary(self, mocker):
        mock_batch = mocker.patch(
            "ftready.checker.check_pypi_batch",
            autospec=True,
            return_value={"some-pkg": {"3.13t": STATUS_SUCCESS, "3.14t": STATUS_FAILED}},
        )
        deps = {"some-pkg": ">=1.0"}
        results = build_results(deps, None, pypi_fallback=True)

        assert len(results) == 1
        assert results[0].source == "pypi"
        assert results[0].status_313t == STATUS_SUCCESS
        assert results[0].status_314t == STATUS_FAILED
        mock_batch.assert_called_once()

    def test_ftchecker_enrichment_overrides_pypi(self, mocker, sample_ft_db):
        """ft-checker data takes priority when both sources have data."""
        mocker.patch(
            "ftready.checker.check_pypi_batch",
            autospec=True,
            return_value={"click": {"3.13t": STATUS_SUCCESS, "3.14t": STATUS_SUCCESS}},
        )
        deps = {"click": ">=8.0"}
        results = build_results(deps, sample_ft_db, pypi_fallback=True)

        assert len(results) == 1
        assert results[0].source == "ft-checker.com"
        # ft-checker says Failed (actual test result) despite PyPI having cp313t wheels
        assert results[0].status_313t == STATUS_FAILED

    def test_pypi_used_when_not_in_ftchecker(self, mocker, sample_ft_db):
        """Packages not in ft-checker should fall back to PyPI data."""
        mocker.patch(
            "ftready.checker.check_pypi_batch",
            autospec=True,
            return_value={"new-pkg": {"3.13t": STATUS_SUCCESS, "3.14t": STATUS_SUCCESS}},
        )
        deps = {"new-pkg": ">=1.0"}
        results = build_results(deps, sample_ft_db, pypi_fallback=True)

        assert len(results) == 1
        assert results[0].source == "pypi"
        assert results[0].status_313t == STATUS_SUCCESS

    def test_direct_deps_sorted_first(self, sample_ft_db):
        deps = {"numpy": ">=1.26", "requests": ">=2.31", "click": ">=8.0"}
        results = build_results(
            deps,
            sample_ft_db,
            direct_names={"numpy"},
            pypi_fallback=False,
        )

        assert results[0].name == "numpy"
        assert results[0].is_direct is True
        assert all(not r.is_direct for r in results[1:])

    def test_results_alphabetically_sorted(self, sample_ft_db):
        deps = {"requests": ">=2.31", "click": ">=8.0", "numpy": ">=1.26"}
        results = build_results(deps, sample_ft_db, pypi_fallback=False)

        names = [r.name for r in results]
        assert names == sorted(names)
