"""ftready — Check if your dependencies are ready for free-threaded Python."""

from ftready.checker import build_results
from ftready.models import PackageResult
from ftready.parser import load_dependencies, load_lockfile_dependencies, load_requirements
from ftready.report import generate_report
from ftready.scraper import fetch_ftchecker_db

__all__ = [
    "PackageResult",
    "build_results",
    "fetch_ftchecker_db",
    "generate_report",
    "load_dependencies",
    "load_lockfile_dependencies",
    "load_requirements",
]
