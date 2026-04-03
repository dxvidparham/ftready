"""Command-line interface for ftready."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import rich_click as click

from ftready.checker import build_results
from ftready.constants import _DEFAULT_CACHE_TTL_HOURS, STATUS_FAILED, STATUS_UNKNOWN
from ftready.parser import load_dependencies, load_lockfile_dependencies, load_requirements
from ftready.report import generate_report
from ftready.scraper import fetch_ftchecker_db

_logger = logging.getLogger(__name__)


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
        lock_path = lock or pyproject.parent / "poetry.lock"
        if not lock_path.exists():
            msg = f"{lock_path} not found. Run 'poetry lock' first."
            raise click.UsageError(msg)
        _logger.info("[ftready] Reading all deps from %s …", lock_path)
        deps = load_lockfile_dependencies(lock_path, direct_names)
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


@click.command(help="Check project dependencies for free-threaded Python (3.13t/3.14t) compatibility.")
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
    help="Check ALL resolved dependencies (direct + transitive) by reading poetry.lock.",
)
@click.option(
    "--lock",
    type=click.Path(path_type=Path),
    default=None,
    metavar="LOCK_FILE",
    help="Path to poetry.lock. Defaults to poetry.lock next to --pyproject.",
)
@click.option("--no-ftchecker", is_flag=True, help="Skip ft-checker.com enrichment (use PyPI only).")
@click.option("--no-pypi", is_flag=True, help="Skip PyPI wheel tag detection (use ft-checker only).")
@click.option("--plain", is_flag=True, help="Force plain-text output even if rich is available.")
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
def main(
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
    verbose: bool,
    requirements: Path | None,
    fail_on: str,
) -> None:
    """Entry point for the free-threaded compatibility checker."""
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
