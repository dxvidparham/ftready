"""Tests for the scraper module — PyPI primary and ft-checker.com enrichment."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ftready.constants import STATUS_NOT_TESTED, STATUS_SUCCESS
from ftready.scraper import (
    _FTPageParser,
    _load_cache,
    _save_cache,
    check_pypi_batch,
    check_pypi_freethreaded,
    fetch_ftchecker_db,
)


class TestFTPageParser:
    def test_parses_313t_section(self):
        html = """
        <h2>Python 3.13t Compatibility Results</h2>
        <table>
        <tr><td>numpy</td><td>1.26.4</td><td>Success</td><td>details</td><td>2026-01-15</td></tr>
        <tr><td>click</td><td>8.1.7</td><td>Failed</td><td>details</td><td>2026-01-15</td></tr>
        </table>
        """
        parser = _FTPageParser()
        parser.feed(html)
        assert "numpy" in parser.entries
        assert parser.entries["numpy"]["3.13t"] == "Success"
        assert parser.entries["click"]["3.13t"] == "Failed"

    def test_parses_314t_section(self):
        html = """
        <h2>Python 3.14t Compatibility Results</h2>
        <table>
        <tr><td>requests</td><td>2.31.0</td><td>Success</td><td>details</td><td>2026-01-15</td></tr>
        </table>
        """
        parser = _FTPageParser()
        parser.feed(html)
        assert parser.entries["requests"]["3.14t"] == "Success"

    def test_ignores_non_success_failed_status(self):
        html = """
        <h2>Python 3.13t Compatibility Results</h2>
        <table>
        <tr><td>pkg</td><td>1.0</td><td>Pending</td><td>details</td><td>2026-01-15</td></tr>
        </table>
        """
        parser = _FTPageParser()
        parser.feed(html)
        assert "pkg" not in parser.entries

    def test_normalises_package_names(self):
        html = """
        <h2>Python 3.13t Compatibility Results</h2>
        <table>
        <tr><td>Scikit_Learn</td><td>1.4</td><td>Success</td><td></td><td>2026-01-15</td></tr>
        </table>
        """
        parser = _FTPageParser()
        parser.feed(html)
        assert "scikit-learn" in parser.entries


class TestCache:
    def test_save_and_load(self, cache_file: Path):
        entries = {"numpy": {"3.13t": "Success", "3.14t": "Success", "checked_at": "2026-01-15"}}
        _save_cache(cache_file, entries)
        loaded, fetched_at = _load_cache(cache_file)
        assert loaded == entries
        assert fetched_at != ""

    def test_load_missing_file(self, tmp_path: Path):
        entries, fetched_at = _load_cache(tmp_path / "nonexistent.json")
        assert entries == {}
        assert fetched_at == ""

    def test_load_corrupt_file(self, tmp_path: Path):
        bad = tmp_path / "bad.json"
        bad.write_text("not json")
        entries, fetched_at = _load_cache(bad)
        assert entries == {}
        assert fetched_at == ""

    def test_atomic_write(self, cache_file: Path):
        """Verify the temp file is cleaned up after save."""
        _save_cache(cache_file, {"a": {}})
        assert cache_file.exists()
        assert not cache_file.with_suffix(".tmp").exists()


class TestPyPIFallback:
    def test_detects_cp313t_wheel(self, mocker):
        mock_data = {
            "urls": [
                {"filename": "pkg-1.0-cp313-cp313t-manylinux_2_17_x86_64.whl"},
                {"filename": "pkg-1.0.tar.gz"},
            ]
        }
        mocker.patch(
            "ftready.scraper.urllib.request.urlopen",
            autospec=True,
            return_value=mocker.MagicMock(
                __enter__=mocker.MagicMock(
                    return_value=mocker.MagicMock(read=mocker.MagicMock(return_value=json.dumps(mock_data).encode()))
                ),
                __exit__=mocker.MagicMock(return_value=False),
            ),
        )
        result = check_pypi_freethreaded("pkg")
        assert result["3.13t"] == STATUS_SUCCESS
        assert result["3.14t"] == STATUS_NOT_TESTED

    def test_no_freethreaded_wheels(self, mocker):
        mock_data = {"urls": [{"filename": "pkg-1.0-cp312-cp312-manylinux_2_17_x86_64.whl"}]}
        mocker.patch(
            "ftready.scraper.urllib.request.urlopen",
            autospec=True,
            return_value=mocker.MagicMock(
                __enter__=mocker.MagicMock(
                    return_value=mocker.MagicMock(read=mocker.MagicMock(return_value=json.dumps(mock_data).encode()))
                ),
                __exit__=mocker.MagicMock(return_value=False),
            ),
        )
        result = check_pypi_freethreaded("pkg")
        assert result["3.13t"] == STATUS_NOT_TESTED
        assert result["3.14t"] == STATUS_NOT_TESTED

    def test_batch_queries_multiple_packages(self, mocker):
        mocker.patch(
            "ftready.scraper.check_pypi_freethreaded",
            autospec=True,
            side_effect=lambda pkg: {"3.13t": STATUS_SUCCESS, "3.14t": STATUS_NOT_TESTED}
            if pkg == "numpy"
            else {"3.13t": STATUS_NOT_TESTED, "3.14t": STATUS_NOT_TESTED},
        )
        results = check_pypi_batch(["numpy", "some-pkg"])
        assert results["numpy"]["3.13t"] == STATUS_SUCCESS
        assert results["some-pkg"]["3.13t"] == STATUS_NOT_TESTED


class TestCacheTTL:
    """Test cache TTL boundary conditions in fetch_ftchecker_db."""

    def _write_cache(self, path: Path, entries: dict, fetched_at: str) -> None:
        payload = json.dumps({"fetched_at": fetched_at, "entries": entries}, indent=2)
        path.write_text(payload, encoding="utf-8")

    def test_fresh_cache_is_used(self, cache_file: Path, mocker):
        """Cache within TTL should be returned without scraping."""
        entries = {"numpy": {"3.13t": "Success", "3.14t": "Success", "checked_at": "2026-01-15"}}
        recent = (datetime.now(tz=UTC) - timedelta(hours=1)).isoformat()
        self._write_cache(cache_file, entries, recent)

        mock_get = mocker.patch("ftready.scraper._http_get", autospec=True)
        result = fetch_ftchecker_db(cache_file, ttl_hours=24)
        assert result == entries
        mock_get.assert_not_called()

    def test_expired_cache_triggers_scrape(self, cache_file: Path, mocker):
        """Cache beyond TTL should trigger a fresh scrape."""
        old_entries = {"old-pkg": {"3.13t": "Failed", "3.14t": "Failed", "checked_at": "2024-01-01"}}
        expired = (datetime.now(tz=UTC) - timedelta(hours=25)).isoformat()
        self._write_cache(cache_file, old_entries, expired)

        page_html = """
        <h2>Python 3.13t Compatibility Results</h2>
        <table>
        <tr><td>fresh-pkg</td><td>1.0</td><td>Success</td><td></td><td>2026-01-15</td></tr>
        </table>
        """
        mocker.patch("ftready.scraper._http_get", autospec=True, return_value=page_html)
        result = fetch_ftchecker_db(cache_file, ttl_hours=24)
        assert "fresh-pkg" in result
        assert "old-pkg" not in result

    def test_missing_cache_triggers_scrape(self, tmp_path: Path, mocker):
        """No cache file should trigger a fresh scrape."""
        missing = tmp_path / "missing_cache.json"
        page_html = """
        <h2>Python 3.13t Compatibility Results</h2>
        <table>
        <tr><td>new-pkg</td><td>2.0</td><td>Success</td><td></td><td>2026-06-01</td></tr>
        </table>
        """
        mocker.patch("ftready.scraper._http_get", autospec=True, return_value=page_html)
        result = fetch_ftchecker_db(missing, ttl_hours=24)
        assert "new-pkg" in result
