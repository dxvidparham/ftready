"""Command-line interface for ftready."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import rich_click as click

from ftready.checker import build_results
from ftready.constants import _DEFAULT_CACHE_TTL_HOURS, STATUS_FAILED, STATUS_UNKNOWN
from ftready.diff import diff_reports, format_diff, format_diff_json
from ftready.parser import load_dependencies, load_lockfile_dependencies, load_requirements
from ftready.report import generate_report
from ftready.scraper import fetch_ftchecker_db

if TYPE_CHECKING:
    from collections.abc import Callable

_logger = logging.getLogger(__name__)

_LOCK_FILE_NAMES = ("uv.lock", "poetry.lock", "pdm.lock")


def _find_lock_file(project_dir: Path) -> Path | None:
    """Auto-detect the first available lock file in *project_dir*."""
    for name in _LOCK_FILE_NAMES:
        candidate = project_dir / name
        if candidate.exists():
            return candidate
    return None


def _lock_loader_for(
    lock_path: Path,  # noqa: ARG001
) -> Callable[[Path, set[str]], dict[str, str]]:
    """Return the lock-file parser (all formats share the same ``[[package]]`` structure)."""
    return load_lockfile_dependencies


def _resolve_deps(
    *,
    requirements: Path | None,
    pyproject: Path,
    include_dev: bool,
    all_deps: bool,
    lock: Path | None,
) -> tuple[dict[str, str], set[str] | None]:
    """
    Load dependencies from the configured source.

    :param requirements: Optional path to a requirements.txt-style file.
    :param pyproject: Path to pyproject.toml.
    :param include_dev: Include dev-only dependencies.
    :param all_deps: Include transitive dependencies from poetry.lock.
    :param lock: Optional explicit path to poetry.lock.
    :return: ``(deps, direct_names)`` tuple.
    :raises click.UsageError: When a required file is missing.
    """
    if requirements is not None:
        _logger.info("[ftready] Reading %s …", requirements)
        deps = load_requirements(requirements)
        _logger.info("[ftready] Found %d packages in %s.", len(deps), requirements)
        return deps, None

    if not pyproject.exists():
        msg = f"{pyproject} not found."
        raise click.UsageError(msg)
    _logger.info("[ftready] Reading %s …", pyproject)

    direct_deps = load_dependencies(pyproject, include_dev=include_dev)
    direct_names = set(direct_deps.keys())

    if all_deps:
        lock_path = lock or _find_lock_file(pyproject.parent)
        if lock_path is None:
            msg = "No lock file found (tried uv.lock, poetry.lock, pdm.lock). Create one first."
            raise click.UsageError(msg)
        if not lock_path.exists():
            msg = f"{lock_path} not found."
            raise click.UsageError(msg)
        _logger.info("[ftready] Reading all deps from %s …", lock_path)
        loader = _lock_loader_for(lock_path)
        deps = loader(lock_path, direct_names)
        transitive = len(deps) - len(direct_names)
        _logger.info(
            "[ftready] Found %d packages in lock file (%d direct, %d transitive).",
            len(deps),
            len(direct_names),
            transitive,
        )
    else:
        deps = direct_deps
        dev_note = " (including dev)" if include_dev else ""
        _logger.info("[ftready] Found %d direct dependencies%s.", len(deps), dev_note)

    return deps, direct_names


class _DefaultGroup(click.RichGroup):
    """A click Group that falls through to a default subcommand when none is given."""

    default_cmd_name: str = "check"

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        """Prepend the default subcommand when args don't start with a known command."""
        if args and args[0] not in self.commands and not args[0].startswith("-"):
            args = [self.default_cmd_name, *args]
        elif args and args[0] not in self.commands:
            # Flags like --plain go to the default subcommand
            args = [self.default_cmd_name, *args]
        elif not args:
            args = [self.default_cmd_name]
        return super().parse_args(ctx, args)


@click.group(cls=_DefaultGroup, help="Check project dependencies for free-threaded Python (3.13t/3.14t) compatibility.")
def main() -> None:
    """Entry point group — delegates to ``check`` by default."""


@main.command(help="Check project dependencies for free-threaded Python compatibility.")
@click.option(
    "--pyproject",
    type=click.Path(path_type=Path),
    default="pyproject.toml",
    show_default=True,
    help="Path to pyproject.toml.",
)
@click.option("--output", type=click.Path(path_type=Path), default=None, help="Write the report to this file.")
@click.option(
    "--cache-file",
    type=click.Path(path_type=Path),
    default=".ft_cache.json",
    show_default=True,
    help="Path for the ft-checker.com result cache.",
)
@click.option(
    "--cache-ttl",
    type=int,
    default=_DEFAULT_CACHE_TTL_HOURS,
    show_default=True,
    metavar="HOURS",
    help="Cache TTL in hours before a fresh scrape is triggered.",
)
@click.option("--no-cache", is_flag=True, help="Ignore and overwrite the existing cache.")
@click.option("--include-dev", is_flag=True, help="Include dev-only dependencies in the report.")
@click.option(
    "--all-deps",
    is_flag=True,
    help="Check ALL resolved dependencies (direct + transitive) from lock file (uv.lock/poetry.lock/pdm.lock).",
)
@click.option(
    "--lock",
    type=click.Path(path_type=Path),
    default=None,
    metavar="LOCK_FILE",
    help="Explicit path to lock file. Auto-detects uv.lock, poetry.lock, or pdm.lock when omitted.",
)
@click.option("--no-ftchecker", is_flag=True, help="Skip ft-checker.com enrichment (use PyPI only).")
@click.option("--no-pypi", is_flag=True, help="Skip PyPI wheel tag detection (use ft-checker only).")
@click.option("--plain", is_flag=True, help="Force plain-text output even if rich is available.")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    show_default=True,
    help="Output format: rich/plain table, JSON, or CSV.",
)
@click.option("-v", "--verbose", is_flag=True, help="Print progress to stderr.")
@click.option(
    "--requirements",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    metavar="FILE",
    help="Path to a requirements.txt-style file to check instead of pyproject.toml.",
)
@click.option(
    "--fail-on",
    type=click.Choice(["never", "failed", "unknown"]),
    default="failed",
    show_default=True,
    help="When to exit with code 1.",
)
def check(
    pyproject: Path,
    output: Path | None,
    cache_file: Path,
    cache_ttl: int,
    no_cache: bool,
    include_dev: bool,
    all_deps: bool,
    lock: Path | None,
    no_ftchecker: bool,
    no_pypi: bool,
    plain: bool,
    output_format: str,
    verbose: bool,
    requirements: Path | None,
    fail_on: str,
) -> None:
    """Run the free-threaded compatibility check."""
    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr, force=True)

    deps, direct_names = _resolve_deps(
        requirements=requirements,
        pyproject=pyproject,
        include_dev=include_dev,
        all_deps=all_deps,
        lock=lock,
    )

    if no_cache and cache_file.exists():
        cache_file.unlink()

    # ft-checker.com is optional enrichment
    ft_db = None
    if not no_ftchecker:
        ft_db = fetch_ftchecker_db(
            cache_file,
            ttl_hours=cache_ttl,
        )

    results = build_results(
        deps,
        ft_db,
        direct_names=direct_names if all_deps else None,
        pypi_fallback=not no_pypi,
    )

    report = generate_report(
        results,
        include_dev=include_dev,
        all_deps=all_deps,
        output_format=output_format,
        use_rich=not plain,
    )

    if output:
        output.write_text(report, encoding="utf-8")
        click.echo(f"Report written to {output}", err=True)
    else:
        click.echo(report)

    if fail_on == "never":
        return
    statuses_to_flag = {STATUS_FAILED}
    if fail_on == "unknown":
        statuses_to_flag.add(STATUS_UNKNOWN)
    any_direct_bad = any(
        r.is_direct and (r.status_313t in statuses_to_flag or r.status_314t in statuses_to_flag) for r in results
    )
    if any_direct_bad:
        sys.exit(1)


@main.command(name="diff", help="Compare two JSON reports to track compatibility changes over time.")
@click.argument("old_report", type=click.Path(exists=True, path_type=Path))
@click.argument("new_report", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
    help="Output format for the diff.",
)
@click.option("--output", type=click.Path(path_type=Path), default=None, help="Write the diff to this file.")
def diff_cmd(
    old_report: Path,
    new_report: Path,
    output_format: str,
    output: Path | None,
) -> None:
    """Compare two ftready JSON reports and show what changed."""
    summary = diff_reports(str(old_report), str(new_report))
    result = format_diff_json(summary) if output_format == "json" else format_diff(summary)

    if output:
        output.write_text(result, encoding="utf-8")
        click.echo(f"Diff written to {output}", err=True)
    else:
        click.echo(result)
