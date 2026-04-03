"""Shared constants and data types."""

from __future__ import annotations

_BASE_URL = "https://ft-checker.com"
_PYPI_API = "https://pypi.org/pypi/{package}/json"
_USER_AGENT = "ftready/0.1.0"

STATUS_SUCCESS = "Success"
STATUS_FAILED = "Failed"
STATUS_UNKNOWN = "Unknown"
STATUS_NOT_TESTED = "Not tested"

_DEFAULT_CACHE_TTL_HOURS = 24
_DEFAULT_MAX_WORKERS = 10
_HTTP_TIMEOUT = 15  # seconds
_FALLBACK_PAGES = 50

# ft-checker DB: maps normalised_name -> {"3.13t": status, "3.14t": status, "checked_at": date}.
FTDb = dict[str, dict[str, str]]
