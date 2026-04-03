"""Tests for the diff module."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from ftready.cli import main
from ftready.diff import DiffSummary, PackageDiff, diff_reports, format_diff, format_diff_json


def _make_report(
    packages: list[dict],
    *,
    ok_313: int = 0,
    ok_314: int = 0,
    fail_313: int = 0,
    fail_314: int = 0,
    generated_at: str = "2025-01-01T00:00:00+00:00",
) -> dict:
    return {
        "generated_at": generated_at,
        "scope": "direct",
        "include_dev": False,
        "summary": {
            "total": len(packages),
            "direct_total": len(packages),
            "ok_313": ok_313,
            "ok_314": ok_314,
            "fail_313": fail_313,
            "fail_314": fail_314,
        },
        "packages": packages,
    }


def _pkg(name: str, s313: str = "Success", s314: str = "Success") -> dict:
    return {
        "name": name,
        "requested": ">=1.0",
        "status_313t": s313,
        "status_314t": s314,
        "source": "pypi",
        "checked_at": "2025-01-01",
        "is_direct": True,
        "is_pure_python": False,
    }


class TestDiffReports:
    def test_no_changes(self):
        old = _make_report([_pkg("numpy")], ok_313=1, ok_314=1)
        new = _make_report([_pkg("numpy")], ok_313=1, ok_314=1, generated_at="2025-02-01T00:00:00+00:00")
        summary = diff_reports(old, new)
        assert len(summary.changed) == 0

    def test_status_change_detected(self):
        old = _make_report([_pkg("numpy", "Not tested", "Not tested")], ok_313=0, ok_314=0)
        new = _make_report(
            [_pkg("numpy", "Success", "Success")],
            ok_313=1,
            ok_314=1,
            generated_at="2025-02-01T00:00:00+00:00",
        )
        summary = diff_reports(old, new)
        assert len(summary.changed) == 1
        assert summary.changed[0].name == "numpy"
        assert summary.changed[0].new_313t == "Success"

    def test_added_package(self):
        old = _make_report([_pkg("numpy")])
        new = _make_report(
            [_pkg("numpy"), _pkg("pandas")],
            ok_313=2,
            ok_314=2,
            generated_at="2025-02-01T00:00:00+00:00",
        )
        summary = diff_reports(old, new)
        added = [p for p in summary.changed if p.added]
        assert len(added) == 1
        assert added[0].name == "pandas"

    def test_removed_package(self):
        old = _make_report([_pkg("numpy"), _pkg("pandas")], ok_313=2)
        new = _make_report([_pkg("numpy")], ok_313=1, generated_at="2025-02-01T00:00:00+00:00")
        summary = diff_reports(old, new)
        removed = [p for p in summary.changed if p.removed]
        assert len(removed) == 1
        assert removed[0].name == "pandas"

    def test_improved_property(self):
        old = _make_report([_pkg("numpy", "Not tested", "Not tested")])
        new = _make_report(
            [_pkg("numpy", "Success", "Not tested")],
            ok_313=1,
            generated_at="2025-02-01T00:00:00+00:00",
        )
        summary = diff_reports(old, new)
        assert len(summary.improved) == 1
        assert summary.improved[0].name == "numpy"

    def test_regressed_property(self):
        old = _make_report([_pkg("numpy", "Success", "Success")], ok_313=1, ok_314=1)
        new = _make_report(
            [_pkg("numpy", "Failed", "Success")],
            ok_314=1,
            fail_313=1,
            generated_at="2025-02-01T00:00:00+00:00",
        )
        summary = diff_reports(old, new)
        assert len(summary.regressed) == 1
        assert summary.regressed[0].name == "numpy"

    def test_reads_from_files(self, tmp_path: Path):
        old = _make_report([_pkg("numpy", "Not tested", "Not tested")])
        new = _make_report(
            [_pkg("numpy", "Success", "Success")],
            ok_313=1,
            ok_314=1,
            generated_at="2025-02-01T00:00:00+00:00",
        )
        old_file = tmp_path / "old.json"
        new_file = tmp_path / "new.json"
        old_file.write_text(json.dumps(old))
        new_file.write_text(json.dumps(new))
        summary = diff_reports(str(old_file), str(new_file))
        assert len(summary.changed) == 1


class TestPackageDiff:
    def test_changed_when_status_differs(self):
        d = PackageDiff("pkg", "Not tested", "Success", "Not tested", "Not tested")
        assert d.changed is True

    def test_not_changed_when_same(self):
        d = PackageDiff("pkg", "Success", "Success", "Success", "Success")
        assert d.changed is False

    def test_changed_when_added(self):
        d = PackageDiff("pkg", "", "Success", "", "Success", added=True)
        assert d.changed is True

    def test_changed_when_removed(self):
        d = PackageDiff("pkg", "Success", "", "Success", "", removed=True)
        assert d.changed is True


class TestFormatDiff:
    def test_no_changes_message(self):
        summary = DiffSummary(
            old_generated_at="2025-01-01",
            new_generated_at="2025-02-01",
            packages=[PackageDiff("numpy", "Success", "Success", "Success", "Success")],
            old_ok_313=1,
            new_ok_313=1,
            old_ok_314=1,
            new_ok_314=1,
        )
        output = format_diff(summary)
        assert "No changes" in output

    def test_improved_section_shown(self):
        summary = DiffSummary(
            old_generated_at="2025-01-01",
            new_generated_at="2025-02-01",
            packages=[PackageDiff("numpy", "Not tested", "Success", "Not tested", "Not tested")],
            old_ok_313=0,
            new_ok_313=1,
            old_ok_314=0,
            new_ok_314=0,
        )
        output = format_diff(summary)
        assert "Improved" in output
        assert "numpy" in output

    def test_regressed_section_shown(self):
        summary = DiffSummary(
            old_generated_at="2025-01-01",
            new_generated_at="2025-02-01",
            packages=[PackageDiff("numpy", "Success", "Failed", "Success", "Success")],
            old_ok_313=1,
            new_ok_313=0,
            old_ok_314=1,
            new_ok_314=1,
        )
        output = format_diff(summary)
        assert "Regressed" in output
        assert "numpy" in output

    def test_added_section_shown(self):
        summary = DiffSummary(
            old_generated_at="2025-01-01",
            new_generated_at="2025-02-01",
            packages=[PackageDiff("pandas", "", "Success", "", "Success", added=True)],
            old_ok_313=0,
            new_ok_313=1,
            old_ok_314=0,
            new_ok_314=1,
        )
        output = format_diff(summary)
        assert "Added" in output
        assert "pandas" in output

    def test_removed_section_shown(self):
        summary = DiffSummary(
            old_generated_at="2025-01-01",
            new_generated_at="2025-02-01",
            packages=[PackageDiff("pandas", "Success", "", "Success", "", removed=True)],
            old_ok_313=1,
            new_ok_313=0,
            old_ok_314=1,
            new_ok_314=0,
        )
        output = format_diff(summary)
        assert "Removed" in output
        assert "pandas" in output

    def test_delta_counts_shown(self):
        summary = DiffSummary(
            old_generated_at="2025-01-01",
            new_generated_at="2025-02-01",
            packages=[PackageDiff("numpy", "Not tested", "Success", "Not tested", "Success")],
            old_ok_313=0,
            new_ok_313=1,
            old_ok_314=0,
            new_ok_314=1,
        )
        output = format_diff(summary)
        assert "+1" in output
        assert "0 → 1" in output


class TestFormatDiffJson:
    def test_valid_json(self):
        summary = DiffSummary(
            old_generated_at="2025-01-01",
            new_generated_at="2025-02-01",
            packages=[PackageDiff("numpy", "Not tested", "Success", "Not tested", "Not tested")],
            old_ok_313=0,
            new_ok_313=1,
            old_ok_314=0,
            new_ok_314=0,
        )
        output = format_diff_json(summary)
        data = json.loads(output)
        assert "changes" in data
        assert "summary" in data
        assert data["summary"]["delta_313"] == 1

    def test_json_only_includes_changed(self):
        summary = DiffSummary(
            old_generated_at="2025-01-01",
            new_generated_at="2025-02-01",
            packages=[
                PackageDiff("numpy", "Success", "Success", "Success", "Success"),  # unchanged
                PackageDiff("pandas", "Not tested", "Success", "Not tested", "Not tested"),  # changed
            ],
            old_ok_313=1,
            new_ok_313=2,
            old_ok_314=1,
            new_ok_314=1,
        )
        output = format_diff_json(summary)
        data = json.loads(output)
        assert len(data["changes"]) == 1
        assert data["changes"][0]["name"] == "pandas"


class TestDiffCLI:
    def test_diff_command(self, tmp_path: Path):
        old = _make_report([_pkg("numpy", "Not tested", "Not tested")])
        new = _make_report(
            [_pkg("numpy", "Success", "Success")],
            ok_313=1,
            ok_314=1,
            generated_at="2025-02-01T00:00:00+00:00",
        )
        old_file = tmp_path / "old.json"
        new_file = tmp_path / "new.json"
        old_file.write_text(json.dumps(old))
        new_file.write_text(json.dumps(new))
        runner = CliRunner()
        result = runner.invoke(main, ["diff", str(old_file), str(new_file)])
        assert result.exit_code == 0
        assert "Improved" in result.output
        assert "numpy" in result.output

    def test_diff_json_output(self, tmp_path: Path):
        old = _make_report([_pkg("numpy", "Not tested", "Not tested")])
        new = _make_report([_pkg("numpy", "Success", "Success")], ok_313=1, ok_314=1)
        old_file = tmp_path / "old.json"
        new_file = tmp_path / "new.json"
        old_file.write_text(json.dumps(old))
        new_file.write_text(json.dumps(new))
        runner = CliRunner()
        result = runner.invoke(main, ["diff", str(old_file), str(new_file), "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "changes" in data

    def test_diff_output_to_file(self, tmp_path: Path):
        old = _make_report([_pkg("numpy")])
        new = _make_report([_pkg("numpy")])
        old_file = tmp_path / "old.json"
        new_file = tmp_path / "new.json"
        out_file = tmp_path / "diff.txt"
        old_file.write_text(json.dumps(old))
        new_file.write_text(json.dumps(new))
        runner = CliRunner()
        result = runner.invoke(main, ["diff", str(old_file), str(new_file), "--output", str(out_file)])
        assert result.exit_code == 0
        assert out_file.exists()

    def test_diff_missing_file_returns_2(self, tmp_path: Path):
        old_file = tmp_path / "old.json"
        old_file.write_text("{}")
        runner = CliRunner()
        result = runner.invoke(main, ["diff", str(old_file), str(tmp_path / "missing.json")])
        assert result.exit_code == 2
