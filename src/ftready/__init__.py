"""ftready — Check if your dependencies are ready for free-threaded Python."""

from ftready.checker import build_results
from ftready.constants import Status
from ftready.diff import DiffSummary, PackageDiff, diff_reports, format_diff, format_diff_json
from ftready.models import PackageResult
from ftready.parser import load_dependencies, load_lockfile_dependencies, load_requirements, load_uv_lock_dependencies
from ftready.report import generate_report
from ftready.scraper import check_pypi_batch, fetch_ftchecker_db

__all__ = [
    "DiffSummary",
    "PackageDiff",
    "PackageResult",
    "Status",
    "build_results",
    "check_pypi_batch",
    "diff_reports",
    "fetch_ftchecker_db",
    "format_diff",
    "format_diff_json",
    "generate_report",
    "load_dependencies",
    "load_lockfile_dependencies",
    "load_requirements",
    "load_uv_lock_dependencies",
]
