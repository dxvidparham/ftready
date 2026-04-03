"""Command-line interface for ftready."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ftready.checker import build_results
from ftready.constants import _DEFAULT_CACHE_TTL_HOURS, STATUS_FAILED, STATUS_UNKNOWN
from ftready.parser import load_dependencies, load_lockfile_dependencies, load_requirements
from ftready.report import generate_report
from ftready.scraper import fetch_ftchecker_db


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ftready",
        description="Check project dependencies for free-threaded Python (3.13t/3.14t) compatibility.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--pyproject",
        type=Path,
        default=Path("pyproject.toml"),
        help="Path to pyproject.toml.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write the report to this file instead of stdout.",
    )
    parser.add_argument(
        "--cache-file",
        type=Path,
        default=Path(".ft_cache.json"),
        help="Path for the ft-checker.com result cache.",
    )
    parser.add_argument(
        "--cache-ttl",
        type=int,
        default=_DEFAULT_CACHE_TTL_HOURS,
        metavar="HOURS",
        help="Cache TTL in hours before a fresh scrape is triggered.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Ignore and overwrite the existing cache.",
    )
    parser.add_argument(
        "--include-dev",
        action="store_true",
        help="Include dev-only dependencies in the report.",
    )
    parser.add_argument(
        "--all-deps",
        action="store_true",
        help=(
            "Check ALL resolved dependencies (direct + transitive) by reading poetry.lock. "
            "Direct deps are shown first; transitive deps are marked in the Type column."
        ),
    )
    parser.add_argument(
        "--lock",
        type=Path,
        default=None,
        metavar="LOCK_FILE",
        help="Path to poetry.lock. Defaults to poetry.lock next to --pyproject. Used with --all-deps.",
    )
    parser.add_argument(
        "--no-pypi-fallback",
        action="store_true",
        help="Disable PyPI API fallback for packages absent from ft-checker.",
    )
    parser.add_argument(
        "--plain",
        action="store_true",
        help="Force plain-text output even if rich is available.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print progress to stderr.",
    )

    # --- Input sources ---
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--requirements",
        type=Path,
        default=None,
        metavar="FILE",
        help=(
            "Path to a requirements.txt-style file to check instead of pyproject.toml. "
            "Can also be a custom dependency file as long as it follows requirements.txt syntax."
        ),
    )

    # --- Pre-commit / CI exit-code control ---
    parser.add_argument(
        "--fail-on",
        choices=["never", "failed", "unknown"],
        default="failed",
        metavar="{never,failed,unknown}",
        help=(
            "When to exit with code 1. "
            "'failed' (default): at least one direct dep has a Failed status. "
            "'unknown': Failed or Unknown status. "
            "'never': always exit 0 (report only)."
        ),
    )

    return parser.parse_args(argv)


def _resolve_deps(args: argparse.Namespace) -> tuple[dict[str, str], set[str] | None] | int:
    """
    Load dependencies from the configured source.

    :param args: Parsed CLI arguments.
    :return: ``(deps, direct_names)`` tuple, or an ``int`` exit code on failure.
    """
    if args.requirements is not None:
        if not args.requirements.exists():
            print(f"Error: {args.requirements} not found.", file=sys.stderr)
            return 2
        if args.verbose:
            print(f"[ftready] Reading {args.requirements} …", file=sys.stderr)
        deps = load_requirements(args.requirements)
        if args.verbose:
            print(f"[ftready] Found {len(deps)} packages in {args.requirements}.", file=sys.stderr)
        return deps, None

    if not args.pyproject.exists():
        print(f"Error: {args.pyproject} not found.", file=sys.stderr)
        return 2
    if args.verbose:
        print(f"[ftready] Reading {args.pyproject} …", file=sys.stderr)

    direct_deps = load_dependencies(args.pyproject, include_dev=args.include_dev)
    direct_names = set(direct_deps.keys())

    if args.all_deps:
        lock_path = args.lock or args.pyproject.parent / "poetry.lock"
        if not lock_path.exists():
            print(f"Error: {lock_path} not found. Run 'poetry lock' first.", file=sys.stderr)
            return 2
        if args.verbose:
            print(f"[ftready] Reading all deps from {lock_path} …", file=sys.stderr)
        deps = load_lockfile_dependencies(lock_path, direct_names)
        if args.verbose:
            transitive = len(deps) - len(direct_names)
            print(
                f"[ftready] Found {len(deps)} packages in lock file "
                f"({len(direct_names)} direct, {transitive} transitive).",
                file=sys.stderr,
            )
    else:
        deps = direct_deps
        if args.verbose:
            dev_note = " (including dev)" if args.include_dev else ""
            print(f"[ftready] Found {len(deps)} direct dependencies{dev_note}.", file=sys.stderr)

    return deps, direct_names


def main(argv: list[str] | None = None) -> int:
    """
    Entry point for the free-threaded compatibility checker.

    :param argv: Override ``sys.argv`` arguments (useful for testing).
    :return: Exit code (0 = success, non-zero if any direct dependency has a *Failed* status).
    """
    args = _parse_args(argv)

    # ------------------------------------------------------------------ #
    # Resolve dependencies                                                  #
    # ------------------------------------------------------------------ #
    resolved = _resolve_deps(args)
    if isinstance(resolved, int):
        return resolved
    deps, direct_names = resolved

    if args.no_cache and args.cache_file.exists():
        args.cache_file.unlink()

    ft_db = fetch_ftchecker_db(
        args.cache_file,
        ttl_hours=args.cache_ttl,
        verbose=args.verbose,
    )

    results = build_results(
        deps,
        ft_db,
        direct_names=direct_names if args.all_deps else None,
        pypi_fallback=not args.no_pypi_fallback,
        verbose=args.verbose,
    )

    report = generate_report(
        results,
        include_dev=args.include_dev,
        all_deps=args.all_deps,
        use_rich=not args.plain,
    )

    if args.output:
        args.output.write_text(report, encoding="utf-8")
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(report)

    fail_on = args.fail_on
    if fail_on == "never":
        return 0
    statuses_to_flag = {STATUS_FAILED}
    if fail_on == "unknown":
        statuses_to_flag.add(STATUS_UNKNOWN)
    any_direct_bad = any(
        r.is_direct and (r.status_313t in statuses_to_flag or r.status_314t in statuses_to_flag) for r in results
    )
    return 1 if any_direct_bad else 0


if __name__ == "__main__":
    sys.exit(main())
