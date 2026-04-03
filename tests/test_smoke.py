"""Integration smoke tests that hit real network endpoints.

These tests are excluded by default (``-m "not network"`` in pytest config).
Run explicitly with: ``uv run pytest -m network -v``
"""

from __future__ import annotations

import pytest

from ftready.constants import STATUS_NOT_TESTED, STATUS_SUCCESS, STATUS_UNKNOWN
from ftready.scraper import check_pypi_freethreaded


@pytest.mark.network
class TestPyPISmoke:
    """Verify the real PyPI JSON API returns sensible results."""

    def test_known_package_returns_valid_status(self):
        """Query a well-known package (requests) and verify the response shape."""
        result = check_pypi_freethreaded("requests")
        assert result["3.13t"] in {STATUS_SUCCESS, STATUS_NOT_TESTED, STATUS_UNKNOWN}
        assert result["3.14t"] in {STATUS_SUCCESS, STATUS_NOT_TESTED, STATUS_UNKNOWN}
        assert isinstance(result["is_pure_python"], bool)

    def test_nonexistent_package_returns_unknown(self):
        """A package that doesn't exist should gracefully return Unknown."""
        result = check_pypi_freethreaded("this-package-definitely-does-not-exist-12345")
        assert result["3.13t"] == STATUS_UNKNOWN
        assert result["3.14t"] == STATUS_UNKNOWN

    def test_pinned_version_query(self):
        """Query a specific version of a package."""
        result = check_pypi_freethreaded("requests", "2.32.3")
        assert result["3.13t"] in {STATUS_SUCCESS, STATUS_NOT_TESTED, STATUS_UNKNOWN}
        assert isinstance(result["is_pure_python"], bool)
