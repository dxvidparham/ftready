"""Report rendering — rich tables or plain-text fallback."""

from __future__ import annotations

from datetime import UTC, datetime
from itertools import starmap

from ftready.models import PackageResult, Stats, compute_stats

try:
    from io import StringIO

    from rich.console import Console
    from rich.table import Table

    _RICH_AVAILABLE = True
except ImportError:
    _RICH_AVAILABLE = False

_ICON = {"Success": "✓", "Failed": "✗", "Unknown": "?", "Not tested": "-"}


def _summary_lines(stats: Stats, *, include_dev: bool, all_deps: bool) -> list[str]:
    """Return the footer lines shared by both renderers."""
    s = stats

    def _ready(ok: int, ok_d: int) -> str:
        base = f"{ok}/{s.total} total"
        return base + (f"  ({ok_d}/{s.direct_total} direct)" if all_deps else "")

    return [
        f"Generated   : {datetime.now(tz=UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Scope       : {'all deps (incl. transitive)' if all_deps else 'direct deps only'}",
        f"Dev deps    : {'included' if include_dev else 'excluded'}",
        f"3.13t ready : {_ready(s.ok_313, s.ok_313_direct)}",
        f"3.14t ready : {_ready(s.ok_314, s.ok_314_direct)}",
    ]


def _row_cells(r: PackageResult, *, all_deps: bool) -> tuple[str, ...]:
    """Return the display cells for one result row."""
    base = (r.name, r.requested, r.status_313t, r.status_314t)
    tail = ("direct" if r.is_direct else "transitive", r.source, r.checked_at)
    return (*base, *tail) if all_deps else (*base, r.source, r.checked_at)


def _header_cells(*, all_deps: bool) -> tuple[str, ...]:
    base = ("Package", "Version / Spec", "3.13t", "3.14t")
    return (*base, "Type", "Source", "Checked At") if all_deps else (*base, "Source", "Checked At")


def _render_report_rich(results: list[PackageResult], *, include_dev: bool, all_deps: bool) -> str:
    """Render the report using ``rich`` for a styled table."""
    style_for = {"Success": "green", "Failed": "red", "Unknown": "yellow", "Not tested": "dim"}.get

    title = "Free-threaded Python Compatibility" + (" (all deps)" if all_deps else " (direct deps)")
    table = Table(title=title, show_header=True, header_style="bold")
    table.add_column("Package", style="cyan", no_wrap=True)
    table.add_column("Version / Spec", style="dim")
    table.add_column("3.13t", justify="center")
    table.add_column("3.14t", justify="center")
    if all_deps:
        table.add_column("Type", style="dim")
    table.add_column("Source", style="dim")
    table.add_column("Checked At", style="dim")

    for r in results:

        def _cell(s: str) -> str:
            return f"[{style_for(s, '')}]{_ICON.get(s, '?')} {s}[/]"

        row: list[str] = [r.name, r.requested, _cell(r.status_313t), _cell(r.status_314t)]
        if all_deps:
            row.append("direct" if r.is_direct else "[dim]transitive[/dim]")
        row += [r.source, r.checked_at]
        table.add_row(*row)

    buf = StringIO()
    console = Console(file=buf, width=120, highlight=False)
    console.print(table)
    console.print("\n" + "\n".join(_summary_lines(compute_stats(results), include_dev=include_dev, all_deps=all_deps)))
    return buf.getvalue()


def _render_report_plain(results: list[PackageResult], *, include_dev: bool, all_deps: bool) -> str:
    """Render the report as a plain-text ASCII table."""
    header = _header_cells(all_deps=all_deps)
    rows = [_row_cells(r, all_deps=all_deps) for r in results]

    widths = list(map(len, header))
    for row in rows:
        for i, cell in enumerate(row):
            if (n := len(cell)) > widths[i]:
                widths[i] = n

    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    fmt = "| " + " | ".join(f"{{:<{w}}}" for w in widths) + " |"
    lines = [sep, fmt.format(*header), sep, *starmap(fmt.format, rows), sep, ""]
    lines.extend(_summary_lines(compute_stats(results), include_dev=include_dev, all_deps=all_deps))
    return "\n".join(lines)


def generate_report(
    results: list[PackageResult],
    *,
    include_dev: bool,
    all_deps: bool = False,
    use_rich: bool = True,
) -> str:
    """Generate the full compatibility report as a string.

    :param results: List of :class:`PackageResult`.
    :param include_dev: Whether dev dependencies were included in the check.
    :param all_deps: Whether the report covers all transitive dependencies.
    :param use_rich: Try to render with ``rich``; fall back to plain text.
    :return: Formatted report string.
    """
    if use_rich and _RICH_AVAILABLE:
        return _render_report_rich(results, include_dev=include_dev, all_deps=all_deps)
    return _render_report_plain(results, include_dev=include_dev, all_deps=all_deps)
