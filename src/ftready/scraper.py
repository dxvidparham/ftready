"""Scrape ft-checker.com and query PyPI for free-threaded compatibility data."""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path

from ftready.constants import (
    FTDb,
    STATUS_FAILED,
    STATUS_NOT_TESTED,
    STATUS_SUCCESS,
    STATUS_UNKNOWN,
    _BASE_URL,
    _DEFAULT_CACHE_TTL_HOURS,
    _DEFAULT_MAX_WORKERS,
    _FALLBACK_PAGES,
    _HTTP_TIMEOUT,
    _PYPI_API,
    _USER_AGENT,
)


# ---------------------------------------------------------------------------
# ft-checker.com HTML parser
# ---------------------------------------------------------------------------


class _FTPageParser(HTMLParser):
    """Extract compatibility rows from a single ft-checker.com page.

    The page contains two ``<table>`` blocks — one for 3.13t and one for 3.14t.
    Each row carries: package name | latest version | status | details | date.
    """

    def __init__(self) -> None:
        super().__init__()
        self._section: str | None = None
        self._in_heading: bool = False
        self._heading_buf: str = ""
        self._in_row: bool = False
        self._in_cell: bool = False
        self._cell_buf: str = ""
        self._row: list[str] = []
        self.entries: FTDb = {}

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in {"h2", "h3", "h4"}:
            self._in_heading, self._heading_buf = True, ""
        elif tag == "tr":
            self._in_row, self._row = True, []
        elif tag == "td" and self._in_row:
            self._in_cell, self._cell_buf = True, ""

    def handle_data(self, data: str) -> None:
        if self._in_heading:
            self._heading_buf += data
        elif self._in_cell:
            self._cell_buf += data

    def handle_endtag(self, tag: str) -> None:
        if tag in {"h2", "h3", "h4"}:
            self._in_heading = False
            h = self._heading_buf
            if "3.13t" in h:
                self._section = "3.13t"
            elif "3.14t" in h:
                self._section = "3.14t"
        elif tag == "td":
            self._row.append(self._cell_buf.strip())
            self._in_cell = False
        elif tag == "tr":
            self._in_row = False
            self._flush_row()

    def _flush_row(self) -> None:
        """Persist a completed table row into :attr:`entries`."""
        row = self._row
        if len(row) < 3 or not row[0] or self._section is None:
            return
        status = row[2].strip()
        if status not in {STATUS_SUCCESS, STATUS_FAILED}:
            return
        name = re.sub(r"[-_.]+", "-", row[0]).lower()
        entry = self.entries.setdefault(
            name,
            {"3.13t": STATUS_UNKNOWN, "3.14t": STATUS_UNKNOWN, "checked_at": ""},
        )
        entry[self._section] = status
        if not entry["checked_at"] and len(row) > 4:
            entry["checked_at"] = row[4].strip()


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _http_get(url: str) -> str:
    """Fetch *url* and return decoded body text, or empty string on error."""
    if not url.startswith(("http:", "https:")):
        msg = f"Only http/https URLs are permitted, got: {url!r}"
        raise ValueError(msg)
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})  # noqa: S310
    try:
        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:  # noqa: S310
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError:
        return ""


# ---------------------------------------------------------------------------
# ft-checker.com scraping
# ---------------------------------------------------------------------------


def _parse_page(html: str) -> FTDb:
    """Parse ft-checker.com HTML and return an :data:`FTDb` fragment."""
    parser = _FTPageParser()
    parser.feed(html)
    return parser.entries


def _fetch_first_page() -> tuple[FTDb, int]:
    """Fetch page 1 and return its data *and* the total page count."""
    html = _http_get(f"{_BASE_URL}/?page=1")
    if not html:
        return {}, _FALLBACK_PAGES
    page_nums = re.findall(r"\?page=(\d+)", html)
    total = max(int(n) for n in page_nums) if page_nums else _FALLBACK_PAGES
    return _parse_page(html), total


def _fetch_page(page: int) -> FTDb:
    """Fetch a single paginated page from ft-checker.com."""
    html = _http_get(f"{_BASE_URL}/?page={page}")
    return _parse_page(html) if html else {}


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------


def _load_cache(path: Path) -> tuple[FTDb, str]:
    """Load cached ft-checker data.

    :return: ``(entries, fetched_at)`` — *fetched_at* is empty when absent or corrupt.
    """
    if not path.exists():
        return {}, ""
    try:
        raw: dict = json.loads(path.read_text(encoding="utf-8"))
        return raw["entries"], raw["fetched_at"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return {}, ""


def _save_cache(path: Path, entries: FTDb) -> None:
    """Write *entries* to *path* atomically (write-then-rename)."""
    payload = json.dumps({"fetched_at": datetime.now(tz=UTC).isoformat(), "entries": entries}, indent=2)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(payload, encoding="utf-8")
    Path(tmp).replace(path)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_ftchecker_db(
    cache_file: Path,
    *,
    ttl_hours: int = _DEFAULT_CACHE_TTL_HOURS,
    max_workers: int = _DEFAULT_MAX_WORKERS,
    verbose: bool = False,
) -> FTDb:
    """Return a complete ft-checker.com compatibility DB, backed by a local cache.

    :param cache_file: Path to the local JSON cache file.
    :param ttl_hours: Cache TTL in hours before a fresh scrape is triggered.
    :param max_workers: Thread pool size for parallel page fetching.
    :param verbose: When ``True``, print progress to stderr.
    :return: ``{normalised_name: {"3.13t": status, "3.14t": status, "checked_at": …}}``
    """
    entries, fetched_at = _load_cache(cache_file)
    if fetched_at:
        age = datetime.now(tz=UTC) - datetime.fromisoformat(fetched_at)
        if age < timedelta(hours=ttl_hours):
            if verbose:
                print(f"[ftready] Using cached data (age: {age})", file=sys.stderr)
            return entries

    if verbose:
        print("[ftready] Scraping ft-checker.com …", file=sys.stderr)

    page1_entries, total = _fetch_first_page()
    if verbose:
        print(f"[ftready] Fetching pages 2-{total} using up to {max_workers} threads …", file=sys.stderr)

    all_entries: FTDb = {**page1_entries}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for page_data in pool.map(_fetch_page, range(2, total + 1)):
            all_entries.update(page_data)

    if verbose:
        print(f"[ftready] Found {len(all_entries)} packages.", file=sys.stderr)

    _save_cache(cache_file, all_entries)
    return all_entries


# ---------------------------------------------------------------------------
# PyPI fallback
# ---------------------------------------------------------------------------


def check_pypi_freethreaded(package: str) -> dict[str, str]:
    """Query the PyPI JSON API to infer free-threaded support from wheel filenames.

    :param package: Normalised package name.
    :return: ``{"3.13t": status, "3.14t": status}``
    """
    url = _PYPI_API.format(package=package)
    if not url.startswith(("http:", "https:")):
        return {"3.13t": STATUS_UNKNOWN, "3.14t": STATUS_UNKNOWN}
    try:
        with urllib.request.urlopen(url, timeout=_HTTP_TIMEOUT) as resp:  # noqa: S310
            data = json.loads(resp.read())
    except (urllib.error.URLError, json.JSONDecodeError):
        return {"3.13t": STATUS_UNKNOWN, "3.14t": STATUS_UNKNOWN}

    filenames = " ".join(u.get("filename", "") for u in data.get("urls", []))
    return {
        "3.13t": STATUS_SUCCESS if "cp313t" in filenames else STATUS_NOT_TESTED,
        "3.14t": STATUS_SUCCESS if "cp314t" in filenames else STATUS_NOT_TESTED,
    }
