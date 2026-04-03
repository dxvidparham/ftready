"""Compare two ftready JSON reports to track compatibility progress over time."""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PackageDiff:
    """A single package's status change between two reports."""

    name: str
    old_313t: str
    new_313t: str
    old_314t: str
    new_314t: str
    added: bool = False
    removed: bool = False

    @property
    def changed(self) -> bool:
        """Return ``True`` if any status field changed (or package was added/removed)."""
        return self.added or self.removed or self.old_313t != self.new_313t or self.old_314t != self.new_314t


@dataclass(frozen=True)
class DiffSummary:
    """Aggregate summary of changes between two reports."""

    old_generated_at: str
    new_generated_at: str
    packages: list[PackageDiff]
    old_ok_313: int
    new_ok_313: int
    old_ok_314: int
    new_ok_314: int

    @property
    def changed(self) -> list[PackageDiff]:
        """Return only packages whose status changed."""
        return [p for p in self.packages if p.changed]

    @property
    def improved(self) -> list[PackageDiff]:
        """Return packages that gained a ``Success`` status."""
        return [
            p
            for p in self.packages
            if (p.new_313t == "Success" and p.old_313t != "Success")
            or (p.new_314t == "Success" and p.old_314t != "Success")
        ]

    @property
    def regressed(self) -> list[PackageDiff]:
        """Return packages that lost a ``Success`` status."""
        return [
            p
            for p in self.packages
            if (p.old_313t == "Success" and p.new_313t != "Success")
            or (p.old_314t == "Success" and p.new_314t != "Success")
        ]


def _load_report(path_or_data: str | dict[str, Any]) -> dict[str, Any]:
    """Load a JSON report from a file path or an already-parsed dict."""
    if isinstance(path_or_data, dict):
        return path_or_data
    with pathlib.Path(path_or_data).open(encoding="utf-8") as f:
        return json.load(f)


def diff_reports(old: str | dict[str, Any], new: str | dict[str, Any]) -> DiffSummary:
    """
    Compare two ftready JSON reports and return a structured diff.

    :param old: Path to the older JSON report, or a parsed dict.
    :param new: Path to the newer JSON report, or a parsed dict.
    :return: A :class:`DiffSummary` with per-package changes and aggregate stats.
    """
    old_data = _load_report(old)
    new_data = _load_report(new)

    old_pkgs: dict[str, dict[str, str]] = {p["name"]: p for p in old_data.get("packages", [])}
    new_pkgs: dict[str, dict[str, str]] = {p["name"]: p for p in new_data.get("packages", [])}

    all_names = sorted(set(old_pkgs) | set(new_pkgs))
    diffs: list[PackageDiff] = []

    for name in all_names:
        old_pkg = old_pkgs.get(name)
        new_pkg = new_pkgs.get(name)

        if old_pkg is None and new_pkg is not None:
            diffs.append(
                PackageDiff(
                    name=name,
                    old_313t="",
                    new_313t=new_pkg.get("status_313t", ""),
                    old_314t="",
                    new_314t=new_pkg.get("status_314t", ""),
                    added=True,
                )
            )
        elif new_pkg is None and old_pkg is not None:
            diffs.append(
                PackageDiff(
                    name=name,
                    old_313t=old_pkg.get("status_313t", ""),
                    new_313t="",
                    old_314t=old_pkg.get("status_314t", ""),
                    new_314t="",
                    removed=True,
                )
            )
        elif old_pkg is not None and new_pkg is not None:
            diffs.append(
                PackageDiff(
                    name=name,
                    old_313t=old_pkg.get("status_313t", ""),
                    new_313t=new_pkg.get("status_313t", ""),
                    old_314t=old_pkg.get("status_314t", ""),
                    new_314t=new_pkg.get("status_314t", ""),
                )
            )

    old_summary = old_data.get("summary", {})
    new_summary = new_data.get("summary", {})

    return DiffSummary(
        old_generated_at=old_data.get("generated_at", ""),
        new_generated_at=new_data.get("generated_at", ""),
        packages=diffs,
        old_ok_313=old_summary.get("ok_313", 0),
        new_ok_313=new_summary.get("ok_313", 0),
        old_ok_314=old_summary.get("ok_314", 0),
        new_ok_314=new_summary.get("ok_314", 0),
    )


def _status_parts(p: PackageDiff) -> str:
    """Format the status change parts for a single package diff."""
    parts: list[str] = []
    if p.old_313t != p.new_313t:
        parts.append(f"3.13t: {p.old_313t} \u2192 {p.new_313t}")
    if p.old_314t != p.new_314t:
        parts.append(f"3.14t: {p.old_314t} \u2192 {p.new_314t}")
    return ", ".join(parts)


def _append_section(lines: list[str], header: str, items: list[PackageDiff], fmt: str = "status") -> None:
    """Append a labelled section of package diffs to *lines*."""
    lines.append(header)
    if fmt == "added":
        lines.extend(f"  {p.name}: 3.13t={p.new_313t}, 3.14t={p.new_314t}" for p in items)
    elif fmt == "removed":
        lines.extend(f"  {p.name}" for p in items)
    else:
        lines.extend(f"  {p.name}: {_status_parts(p)}" for p in items)
    lines.append("")


def format_diff(summary: DiffSummary) -> str:
    """
    Render a :class:`DiffSummary` as a human-readable plain-text report.

    :param summary: The diff summary to render.
    :return: Formatted string.
    """
    lines: list[str] = []
    changed = summary.changed

    if not changed:
        lines.extend([
            "No changes detected between reports.",
            f"  Old: {summary.old_generated_at}",
            f"  New: {summary.new_generated_at}",
        ])
        return "\n".join(lines)

    delta_313 = summary.new_ok_313 - summary.old_ok_313
    delta_314 = summary.new_ok_314 - summary.old_ok_314

    def _sign(n: int) -> str:
        return f"+{n}" if n > 0 else str(n)

    lines.extend([
        f"ftready diff: {summary.old_generated_at} \u2192 {summary.new_generated_at}",
        "",
        f"3.13t ready: {summary.old_ok_313} \u2192 {summary.new_ok_313} ({_sign(delta_313)})",
        f"3.14t ready: {summary.old_ok_314} \u2192 {summary.new_ok_314} ({_sign(delta_314)})",
        "",
    ])

    improved = summary.improved
    regressed = summary.regressed
    added = [p for p in changed if p.added]
    removed = [p for p in changed if p.removed]
    other = [p for p in changed if not p.added and not p.removed and p not in improved and p not in regressed]

    if improved:
        _append_section(lines, f"\u2705 Improved ({len(improved)}):", improved)
    if regressed:
        _append_section(lines, f"\u274c Regressed ({len(regressed)}):", regressed)
    if added:
        _append_section(lines, f"+ Added ({len(added)}):", added, fmt="added")
    if removed:
        _append_section(lines, f"- Removed ({len(removed)}):", removed, fmt="removed")
    if other:
        _append_section(lines, f"\U0001f504 Other changes ({len(other)}):", other)

    return "\n".join(lines)


def format_diff_json(summary: DiffSummary) -> str:
    """
    Render a :class:`DiffSummary` as a JSON document.

    :param summary: The diff summary to render.
    :return: JSON string.
    """
    payload = {
        "old_generated_at": summary.old_generated_at,
        "new_generated_at": summary.new_generated_at,
        "summary": {
            "old_ok_313": summary.old_ok_313,
            "new_ok_313": summary.new_ok_313,
            "old_ok_314": summary.old_ok_314,
            "new_ok_314": summary.new_ok_314,
            "delta_313": summary.new_ok_313 - summary.old_ok_313,
            "delta_314": summary.new_ok_314 - summary.old_ok_314,
        },
        "changes": [
            {
                "name": p.name,
                "old_313t": p.old_313t,
                "new_313t": p.new_313t,
                "old_314t": p.old_314t,
                "new_314t": p.new_314t,
                "added": p.added,
                "removed": p.removed,
            }
            for p in summary.changed
        ],
    }
    return json.dumps(payload, indent=2)
