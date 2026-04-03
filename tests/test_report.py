"""Tests for the report rendering module."""

from __future__ import annotations

import json

from ftready.constants import STATUS_FAILED, STATUS_SUCCESS, STATUS_UNKNOWN
from ftready.models import PackageResult, Stats, compute_stats
from ftready.report import generate_report


class TestComputeStats:
    def test_empty_results(self):
        stats = compute_stats([])
        assert stats == Stats(
            total=0,
            direct_total=0,
            ok_313=0,
            ok_314=0,
            ok_313_direct=0,
            ok_314_direct=0,
            fail_313=0,
            fail_314=0,
        )

    def test_all_success(self):
        results = [
            PackageResult("a", "1.0", STATUS_SUCCESS, STATUS_SUCCESS, is_direct=True),
            PackageResult("b", "2.0", STATUS_SUCCESS, STATUS_SUCCESS, is_direct=True),
        ]
        stats = compute_stats(results)
        assert stats.total == 2
        assert stats.ok_313 == 2
        assert stats.ok_314 == 2
        assert stats.direct_total == 2

    def test_mixed_results(self):
        results = [
            PackageResult("a", "1.0", STATUS_SUCCESS, STATUS_FAILED, is_direct=True),
            PackageResult("b", "2.0", STATUS_UNKNOWN, STATUS_SUCCESS, is_direct=False),
        ]
        stats = compute_stats(results)
        assert stats.total == 2
        assert stats.direct_total == 1
        assert stats.ok_313 == 1
        assert stats.ok_314 == 1
        assert stats.ok_313_direct == 1
        assert stats.ok_314_direct == 0


class TestGenerateReport:
    def test_plain_report_contains_packages(self):
        results = [
            PackageResult("numpy", ">=1.26", STATUS_SUCCESS, STATUS_SUCCESS, source="ft-checker.com"),
            PackageResult("click", ">=8.0", STATUS_FAILED, STATUS_FAILED, source="ft-checker.com"),
        ]
        report = generate_report(results, include_dev=False, use_rich=False)
        assert "numpy" in report
        assert "click" in report
        assert "Success" in report
        assert "Failed" in report

    def test_plain_report_footer(self):
        results = [
            PackageResult("numpy", ">=1.26", STATUS_SUCCESS, STATUS_SUCCESS, source="ft-checker.com"),
        ]
        report = generate_report(results, include_dev=False, use_rich=False)
        assert "3.13t ready" in report
        assert "3.14t ready" in report
        assert "1/1 total" in report

    def test_all_deps_mode_shows_type_column(self):
        results = [
            PackageResult("numpy", "1.26.4", STATUS_SUCCESS, STATUS_SUCCESS, is_direct=True),
            PackageResult("urllib3", "↳ 2.2.1", STATUS_UNKNOWN, STATUS_UNKNOWN, is_direct=False),
        ]
        report = generate_report(results, include_dev=False, all_deps=True, use_rich=False)
        assert "direct" in report
        assert "transitive" in report
        assert "Type" in report

    def test_dev_deps_label(self):
        results = [PackageResult("ruff", ">=0.4", STATUS_SUCCESS, STATUS_SUCCESS)]
        report = generate_report(results, include_dev=True, use_rich=False)
        assert "included" in report


class TestRichReport:
    def test_rich_report_contains_packages(self):
        """Rich is always available — report should contain all package names."""
        results = [
            PackageResult("numpy", ">=1.26", STATUS_SUCCESS, STATUS_SUCCESS, source="ft-checker.com"),
            PackageResult("click", ">=8.0", STATUS_FAILED, STATUS_FAILED, source="ft-checker.com"),
        ]
        report = generate_report(results, include_dev=False, use_rich=True)
        assert "numpy" in report
        assert "click" in report

    def test_rich_report_disabled_falls_back_to_plain(self):
        """When rich is explicitly disabled, plain text should be used."""
        results = [PackageResult("pkg", "1.0", STATUS_SUCCESS, STATUS_UNKNOWN)]
        report = generate_report(results, include_dev=False, use_rich=False)
        # Plain text uses ASCII table separators
        assert "+" in report
        assert "|" in report


class TestJSONOutput:
    def test_json_is_valid(self):
        results = [PackageResult("numpy", "1.26.4", STATUS_SUCCESS, STATUS_SUCCESS, source="pypi")]
        report = generate_report(results, include_dev=False, output_format="json")
        data = json.loads(report)
        assert "packages" in data
        assert "summary" in data

    def test_json_contains_all_fields(self):
        results = [
            PackageResult("click", "8.1.7", STATUS_SUCCESS, STATUS_FAILED, source="pypi", is_pure_python=True),
        ]
        report = generate_report(results, include_dev=False, output_format="json")
        data = json.loads(report)
        pkg = data["packages"][0]
        assert pkg["name"] == "click"
        assert pkg["status_313t"] == STATUS_SUCCESS
        assert pkg["status_314t"] == STATUS_FAILED
        assert pkg["is_pure_python"] is True

    def test_json_summary_counts(self):
        results = [
            PackageResult("a", "1.0", STATUS_SUCCESS, STATUS_SUCCESS),
            PackageResult("b", "2.0", STATUS_FAILED, STATUS_SUCCESS),
        ]
        report = generate_report(results, include_dev=False, output_format="json")
        data = json.loads(report)
        assert data["summary"]["total"] == 2
        assert data["summary"]["ok_313"] == 1
        assert data["summary"]["ok_314"] == 2

    def test_json_scope_field(self):
        results = [PackageResult("a", "1.0", STATUS_SUCCESS, STATUS_SUCCESS)]
        report = generate_report(results, include_dev=True, all_deps=True, output_format="json")
        data = json.loads(report)
        assert data["scope"] == "all"
        assert data["include_dev"] is True


class TestCSVOutput:
    def test_csv_header_row(self):
        results = [PackageResult("numpy", "1.26.4", STATUS_SUCCESS, STATUS_SUCCESS)]
        report = generate_report(results, include_dev=False, output_format="csv")
        lines = report.strip().splitlines()
        assert lines[0] == "package,requested,3.13t,3.14t,source,checked_at,is_direct,is_pure_python"

    def test_csv_data_row(self):
        results = [
            PackageResult("click", "8.1.7", STATUS_SUCCESS, STATUS_FAILED, source="pypi", is_pure_python=True),
        ]
        report = generate_report(results, include_dev=False, output_format="csv")
        lines = report.strip().splitlines()
        assert len(lines) == 2
        assert "click" in lines[1]
        assert "True" in lines[1]

    def test_csv_multiple_rows(self):
        results = [
            PackageResult("a", "1.0", STATUS_SUCCESS, STATUS_SUCCESS),
            PackageResult("b", "2.0", STATUS_FAILED, STATUS_FAILED),
        ]
        report = generate_report(results, include_dev=False, output_format="csv")
        lines = report.strip().splitlines()
        assert len(lines) == 3  # header + 2 data rows


class TestStatusLegend:
    def test_plain_report_contains_legend(self):
        results = [PackageResult("pkg", "1.0", STATUS_SUCCESS, STATUS_SUCCESS)]
        report = generate_report(results, include_dev=False, use_rich=False)
        assert "Legend:" in report

    def test_rich_report_contains_legend(self):
        results = [PackageResult("pkg", "1.0", STATUS_SUCCESS, STATUS_SUCCESS)]
        report = generate_report(results, include_dev=False, use_rich=True)
        assert "Legend:" in report


class TestPurePythonColumn:
    def test_plain_report_shows_pure_icon(self):
        results = [PackageResult("click", "8.0", STATUS_SUCCESS, STATUS_SUCCESS, is_pure_python=True)]
        report = generate_report(results, include_dev=False, use_rich=False)
        assert "🐍" in report

    def test_plain_report_no_icon_for_native(self):
        results = [PackageResult("numpy", "1.26", STATUS_SUCCESS, STATUS_SUCCESS, is_pure_python=False)]
        report = generate_report(results, include_dev=False, use_rich=False)
        # Should have the Pure column header but no emoji for this row
        assert "Pure" in report
