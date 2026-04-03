"""Command-line interface for ftready."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ftready.checker import build_results
from ftready.constants import STATUS_FAILED, _DEFAULT_CACHE_TTL_HOURS
from ftready.parser import load_dependencies, load_lockfile_dependencies
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the free-threaded compatibility checker.

    :param argv: Override ``sys.argv`` arguments (useful for testing).
    :return: Exit code (0 = success, non-zero if any direct dependency has a *Failed* status).
    """
    args = _parse_args(argv)

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

    any_direct_failed = any(r.is_direct and STATUS_FAILED in {r.status_313t, r.status_314t} for r in results)
    return 1 if any_direct_failed else 0


if __name__ == "__main__":
    sys.exit(main())
