"""Tests for the CLI entry point."""

from __future__ import annotations

from pathlib import Path

from ftready.cli import main


class TestCLI:
    def test_missing_pyproject_returns_2(self, tmp_path: Path):
        exit_code = main(["--pyproject", str(tmp_path / "nonexistent.toml")])
        assert exit_code == 2

    def test_plain_output(self, mocker, sample_pyproject: Path, sample_ft_db):
        mocker.patch("ftready.cli.fetch_ftchecker_db", autospec=True, return_value=sample_ft_db)
        mocker.patch("ftready.cli.build_results", autospec=True, return_value=[])
        exit_code = main(["--pyproject", str(sample_pyproject), "--plain", "--no-pypi-fallback"])
        assert exit_code == 0

    def test_output_to_file(self, mocker, sample_pyproject: Path, sample_ft_db, tmp_path: Path):
        mocker.patch("ftready.cli.fetch_ftchecker_db", autospec=True, return_value=sample_ft_db)
        mocker.patch("ftready.cli.build_results", autospec=True, return_value=[])
        output = tmp_path / "report.txt"
        exit_code = main(["--pyproject", str(sample_pyproject), "--output", str(output), "--plain"])
        assert exit_code == 0
        assert output.exists()

    def test_all_deps_missing_lockfile_returns_2(self, sample_pyproject: Path, mocker):
        mocker.patch("ftready.cli.fetch_ftchecker_db", autospec=True, return_value={})
        exit_code = main(["--pyproject", str(sample_pyproject), "--all-deps"])
        assert exit_code == 2
