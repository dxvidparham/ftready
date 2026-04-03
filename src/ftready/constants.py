"""Shared constants and data types."""

from __future__ import annotations

import enum
from typing import TypedDict

_BASE_URL = "https://ft-checker.com"
_PYPI_API = "https://pypi.org/pypi/{package}/json"
try:
    from importlib.metadata import version as _pkg_version

    _USER_AGENT = f"ftready/{_pkg_version('ftready')}"
except Exception:
    _USER_AGENT = "ftready/dev"


class Status(enum.StrEnum):
    """Compatibility status for a package against a free-threaded Python build."""

    SUCCESS = "Success"
    FAILED = "Failed"
    UNKNOWN = "Unknown"
    NOT_TESTED = "Not tested"


# Convenience aliases for backwards compatibility and brevity.
STATUS_SUCCESS = Status.SUCCESS
STATUS_FAILED = Status.FAILED
STATUS_UNKNOWN = Status.UNKNOWN
STATUS_NOT_TESTED = Status.NOT_TESTED

_DEFAULT_CACHE_TTL_HOURS = 24
_DEFAULT_MAX_WORKERS = 10
_HTTP_TIMEOUT = 15  # seconds
_FALLBACK_PAGES = 50


# Use functional form: "3.13t" / "3.14t" are not valid Python identifiers.
FTEntry = TypedDict("FTEntry", {"3.13t": str, "3.14t": str, "checked_at": str})

# ft-checker DB: maps normalised_name -> FTEntry.
FTDb = dict[str, FTEntry]
