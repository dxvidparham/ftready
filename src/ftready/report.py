"""Report rendering — rich tables, plain-text, JSON, and CSV output."""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from io import StringIO
from itertools import starmap

from ftready.models import PackageResult, Stats, compute_stats

_ICON = {"Success": "✅", "Failed": "❌", "Unknown": "❓", "Not tested": "⬜"}

_STYLE = {"Success": "bold green", "Failed": "bold red", "Unknown": "bold yellow", "Not tested": "dim"}

_STATUS_LEGEND = (
    "Legend: "
    "✅ Success = free-threaded wheel found or test passed · "
    "❌ Failed = ft-checker test failed · "
    "❓ Unknown = could not determine (API error) · "
    "⬜ Not tested = no ft wheel on PyPI, not in ft-checker · "
    "🐍 = pure-Python (likely compatible)"
)


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


def _pct_bar(ok: int, fail: int, total: int) -> str:
    """Return a rich-markup 3-segment progress bar: green=success, red=failed, dim=untested."""
    if total == 0:
        return "[dim]no packages[/dim]"
    width = 20
    g = round(ok / total * width)
    r = round(fail / total * width)
    d = width - g - r
    bar = f"[green]{'█' * g}[/green][red]{'█' * r}[/red][dim]{'░' * d}[/dim]"
    pct_ok = ok / total
    pct_fail = fail / total
    untested = total - ok - fail
    pct_unt = untested / total
    parts = [
        bar,
        f" [green]{ok} ok ({pct_ok:.0%})[/green]",
        f" [red]{fail} failed ({pct_fail:.0%})[/red]",
        f" [dim]{untested} untested ({pct_unt:.0%})[/dim]",
    ]
    return " ".join(parts)


def _row_cells(r: PackageResult, *, all_deps: bool) -> tuple[str, ...]:
    """Return the display cells for one result row."""
    pure = "🐍" if r.is_pure_python else ""
    base = (r.name, r.requested, r.status_313t, r.status_314t, pure)
    tail = ("direct" if r.is_direct else "transitive",)
    return (*base, *tail) if all_deps else base


def _header_cells(*, all_deps: bool) -> tuple[str, ...]:
    base = ("Package", "Version / Spec", "3.13t", "3.14t", "Pure")
    return (*base, "Type") if all_deps else base


def _render_report_rich(results: list[PackageResult], *, include_dev: bool, all_deps: bool) -> str:
    """Render the report using ``rich`` for a styled table."""
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text

    title = "Free-threaded Python Compatibility"
    subtitle = "all deps (incl. transitive)" if all_deps else "direct deps only"
    if include_dev:
        subtitle += ", dev included"

    table = Table(title=title, caption=subtitle, show_header=True, header_style="bold", padding=(0, 1))
    table.add_column("Package", style="cyan", no_wrap=True)
    table.add_column("Requested", style="dim")
    table.add_column("3.13t", justify="left")
    table.add_column("3.14t", justify="left")
    table.add_column("Pure", justify="center", width=4)
    if all_deps:
        table.add_column("Type", style="dim")

    for r in results:

        def _cell(s: str) -> Text:
            icon = _ICON.get(s, "?")
            style = _STYLE.get(s, "")
            return Text(f"{icon} {s}", style=style)

        pure = Text("🐍", style="green") if r.is_pure_python else Text("")
        row: list[str | Text] = [r.name, r.requested, _cell(r.status_313t), _cell(r.status_314t), pure]
        if all_deps:
            row.append("direct" if r.is_direct else Text("transitive", style="dim"))
        table.add_row(*row)

    stats = compute_stats(results)

    buf = StringIO()
    console = Console(file=buf, width=120, highlight=False, force_terminal=True, force_jupyter=False)
    console.print(table)
    console.print()
    console.print(f"  [bold]3.13t[/bold]  {_pct_bar(stats.ok_313, stats.fail_313, stats.total)}")
    console.print(f"  [bold]3.14t[/bold]  {_pct_bar(stats.ok_314, stats.fail_314, stats.total)}")
    console.print()
    console.print(f"  [dim]{datetime.now(tz=UTC).strftime('%Y-%m-%d %H:%M UTC')}[/dim]")
    console.print(f"  [dim]{_STATUS_LEGEND}[/dim]")
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
    lines.extend(("", _STATUS_LEGEND))
    return "\n".join(lines)


def _render_report_json(results: list[PackageResult], *, include_dev: bool, all_deps: bool) -> str:
    """Render the report as a JSON document."""
    stats = compute_stats(results)
    payload = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "scope": "all" if all_deps else "direct",
        "include_dev": include_dev,
        "summary": {
            "total": stats.total,
            "direct_total": stats.direct_total,
            "ok_313": stats.ok_313,
            "ok_314": stats.ok_314,
            "fail_313": stats.fail_313,
            "fail_314": stats.fail_314,
        },
        "packages": [
            {
                "name": r.name,
                "requested": r.requested,
                "status_313t": r.status_313t,
                "status_314t": r.status_314t,
                "source": r.source,
                "checked_at": r.checked_at,
                "is_direct": r.is_direct,
                "is_pure_python": r.is_pure_python,
            }
            for r in results
        ],
    }
    return json.dumps(payload, indent=2)


def _render_report_csv(results: list[PackageResult]) -> str:
    """Render the report as a CSV document."""
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(["package", "requested", "3.13t", "3.14t", "source", "checked_at", "is_direct", "is_pure_python"])
    for r in results:
        writer.writerow([
            r.name,
            r.requested,
            r.status_313t,
            r.status_314t,
            r.source,
            r.checked_at,
            r.is_direct,
            r.is_pure_python,
        ])
    return buf.getvalue()


def generate_report(
    results: list[PackageResult],
    *,
    include_dev: bool,
    all_deps: bool = False,
    output_format: str = "table",
    use_rich: bool = True,
) -> str:
    """
    Generate the full compatibility report as a string.

    :param results: List of :class:`PackageResult`.
    :param include_dev: Whether dev dependencies were included in the check.
    :param all_deps: Whether the report covers all transitive dependencies.
    :param output_format: ``"table"`` (default), ``"json"``, or ``"csv"``.
    :param use_rich: Try to render with ``rich``; fall back to plain text (table only).
    :return: Formatted report string.
    """
    if output_format == "json":
        return _render_report_json(results, include_dev=include_dev, all_deps=all_deps)
    if output_format == "csv":
        return _render_report_csv(results)
    if use_rich:
        return _render_report_rich(results, include_dev=include_dev, all_deps=all_deps)
    return _render_report_plain(results, include_dev=include_dev, all_deps=all_deps)
