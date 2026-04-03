"""Tests for the CLI entry point."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from ftready.cli import main
from ftready.constants import STATUS_FAILED, STATUS_SUCCESS, STATUS_UNKNOWN
from ftready.models import PackageResult


class TestCLI:
    def test_version_flag(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "ftready" in result.output

    def test_missing_pyproject_returns_2(self, tmp_path: Path):
        runner = CliRunner()
        result = runner.invoke(main, ["--pyproject", str(tmp_path / "nonexistent.toml")])
        assert result.exit_code == 2

    def test_plain_output(self, mocker, sample_pyproject: Path, sample_ft_db):
        mocker.patch("ftready.cli.fetch_ftchecker_db", autospec=True, return_value=sample_ft_db)
        mocker.patch("ftready.cli.build_results", autospec=True, return_value=[])
        runner = CliRunner()
        result = runner.invoke(main, ["--pyproject", str(sample_pyproject), "--plain", "--no-pypi"])
        assert result.exit_code == 0

    def test_output_to_file(self, mocker, sample_pyproject: Path, sample_ft_db, tmp_path: Path):
        mocker.patch("ftready.cli.fetch_ftchecker_db", autospec=True, return_value=sample_ft_db)
        mocker.patch("ftready.cli.build_results", autospec=True, return_value=[])
        output = tmp_path / "report.txt"
        runner = CliRunner()
        result = runner.invoke(main, ["--pyproject", str(sample_pyproject), "--output", str(output), "--plain"])
        assert result.exit_code == 0
        assert output.exists()

    def test_all_deps_missing_lockfile_returns_2(self, sample_pyproject: Path, mocker):
        mocker.patch("ftready.cli.fetch_ftchecker_db", autospec=True, return_value={})
        runner = CliRunner()
        result = runner.invoke(main, ["--pyproject", str(sample_pyproject), "--all-deps"])
        assert result.exit_code == 2

    def test_requirements_mode_reads_file(self, mocker, tmp_path: Path, sample_ft_db):
        """Given a requirements.txt, when using --requirements, then deps are loaded from it."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("numpy>=1.26\nrequests>=2.31\n")
        mocker.patch("ftready.cli.fetch_ftchecker_db", autospec=True, return_value=sample_ft_db)
        mocker.patch("ftready.cli.build_results", autospec=True, return_value=[])
        runner = CliRunner()
        result = runner.invoke(main, ["--requirements", str(req_file), "--plain"])
        assert result.exit_code == 0

    def test_requirements_missing_file_returns_2(self, tmp_path: Path):
        """Given a nonexistent requirements file, then exit code is 2."""
        runner = CliRunner()
        result = runner.invoke(main, ["--requirements", str(tmp_path / "missing.txt")])
        assert result.exit_code == 2

    def test_fail_on_unknown_exits_1_when_unknown_status(self, mocker, sample_pyproject: Path, sample_ft_db):
        """Given --fail-on=unknown and an Unknown dep, then exit code is 1."""
        results = [PackageResult("pkg", ">=1.0", STATUS_UNKNOWN, STATUS_UNKNOWN, is_direct=True)]
        mocker.patch("ftready.cli.fetch_ftchecker_db", autospec=True, return_value=sample_ft_db)
        mocker.patch("ftready.cli.build_results", autospec=True, return_value=results)
        runner = CliRunner()
        result = runner.invoke(main, ["--pyproject", str(sample_pyproject), "--plain", "--fail-on", "unknown"])
        assert result.exit_code == 1

    def test_fail_on_never_exits_0_even_with_failures(self, mocker, sample_pyproject: Path, sample_ft_db):
        """Given --fail-on=never and a Failed dep, then exit code is always 0."""
        results = [PackageResult("pkg", ">=1.0", STATUS_FAILED, STATUS_FAILED, is_direct=True)]
        mocker.patch("ftready.cli.fetch_ftchecker_db", autospec=True, return_value=sample_ft_db)
        mocker.patch("ftready.cli.build_results", autospec=True, return_value=results)
        runner = CliRunner()
        result = runner.invoke(main, ["--pyproject", str(sample_pyproject), "--plain", "--fail-on", "never"])
        assert result.exit_code == 0

    def test_fail_on_failed_exits_1_when_direct_dep_failed(self, mocker, sample_pyproject: Path, sample_ft_db):
        """Given default --fail-on and a direct Failed dep, then exit code is 1."""
        results = [PackageResult("pkg", ">=1.0", STATUS_FAILED, STATUS_SUCCESS, is_direct=True)]
        mocker.patch("ftready.cli.fetch_ftchecker_db", autospec=True, return_value=sample_ft_db)
        mocker.patch("ftready.cli.build_results", autospec=True, return_value=results)
        runner = CliRunner()
        result = runner.invoke(main, ["--pyproject", str(sample_pyproject), "--plain"])
        assert result.exit_code == 1

    def test_no_cache_deletes_existing_cache(self, mocker, sample_pyproject: Path, sample_ft_db, tmp_path: Path):
        """Given --no-cache with an existing cache file, then the cache is deleted before fetch."""
        cache = tmp_path / ".ft_cache.json"
        cache.write_text("{}")
        mocker.patch("ftready.cli.fetch_ftchecker_db", autospec=True, return_value=sample_ft_db)
        mocker.patch("ftready.cli.build_results", autospec=True, return_value=[])
        runner = CliRunner()
        result = runner.invoke(
            main, ["--pyproject", str(sample_pyproject), "--plain", "--no-cache", "--cache-file", str(cache)]
        )
        assert result.exit_code == 0
        assert not cache.exists()

    def test_verbose_prints_progress_to_stderr(self, mocker, sample_pyproject: Path, sample_ft_db):
        """Given --verbose, then progress messages appear on stderr."""
        mocker.patch("ftready.cli.fetch_ftchecker_db", autospec=True, return_value=sample_ft_db)
        mocker.patch("ftready.cli.build_results", autospec=True, return_value=[])
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, ["--pyproject", str(sample_pyproject), "--plain", "--verbose"])
        assert "[ftready]" in result.stderr


class TestOutputFormats:
    def test_json_format(self, mocker, sample_pyproject: Path, sample_ft_db):
        mocker.patch("ftready.cli.fetch_ftchecker_db", autospec=True, return_value=sample_ft_db)
        mocker.patch(
            "ftready.cli.build_results",
            autospec=True,
            return_value=[PackageResult("numpy", "1.26", STATUS_SUCCESS, STATUS_SUCCESS)],
        )
        runner = CliRunner()
        result = runner.invoke(main, ["--pyproject", str(sample_pyproject), "--format", "json"])
        assert result.exit_code == 0
        import json

        data = json.loads(result.output)
        assert "packages" in data
        assert data["packages"][0]["name"] == "numpy"

    def test_csv_format(self, mocker, sample_pyproject: Path, sample_ft_db):
        mocker.patch("ftready.cli.fetch_ftchecker_db", autospec=True, return_value=sample_ft_db)
        mocker.patch(
            "ftready.cli.build_results",
            autospec=True,
            return_value=[PackageResult("numpy", "1.26", STATUS_SUCCESS, STATUS_SUCCESS)],
        )
        runner = CliRunner()
        result = runner.invoke(main, ["--pyproject", str(sample_pyproject), "--format", "csv"])
        assert result.exit_code == 0
        assert "package,requested" in result.output
        assert "numpy" in result.output

    def test_invalid_format_rejected(self, sample_pyproject: Path):
        runner = CliRunner()
        result = runner.invoke(main, ["--pyproject", str(sample_pyproject), "--format", "xml"])
        assert result.exit_code == 2


class TestLockFileAutoDetect:
    def test_uv_lock_auto_detected(self, mocker, sample_pyproject: Path, sample_ft_db):
        """When uv.lock exists, it should be auto-detected for --all-deps."""
        uv_lock = sample_pyproject.parent / "uv.lock"
        uv_lock.write_text("""\
[[package]]
name = "numpy"
version = "1.26.4"

[[package]]
name = "requests"
version = "2.31.0"
""")
        mocker.patch("ftready.cli.fetch_ftchecker_db", autospec=True, return_value=sample_ft_db)
        mocker.patch(
            "ftready.cli.build_results",
            autospec=True,
            return_value=[PackageResult("numpy", "1.26.4", STATUS_SUCCESS, STATUS_SUCCESS)],
        )
        runner = CliRunner()
        result = runner.invoke(main, ["--pyproject", str(sample_pyproject), "--all-deps", "--plain"])
        assert result.exit_code == 0

    def test_no_lock_file_error(self, mocker, sample_pyproject: Path, sample_ft_db):
        """When no lock file exists, --all-deps should error."""
        mocker.patch("ftready.cli.fetch_ftchecker_db", autospec=True, return_value=sample_ft_db)
        runner = CliRunner()
        result = runner.invoke(main, ["--pyproject", str(sample_pyproject), "--all-deps"])
        assert result.exit_code == 2
