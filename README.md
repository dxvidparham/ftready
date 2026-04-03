# ftready

[![CI](https://github.com/dxvidparham/ftready/actions/workflows/ci.yml/badge.svg)](https://github.com/dxvidparham/ftready/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/ftready)](https://pypi.org/project/ftready/)
[![Python versions](https://img.shields.io/pypi/pyversions/ftready)](https://pypi.org/project/ftready/)
[![Coverage](https://img.shields.io/badge/coverage-89%25-yellowgreen)](https://github.com/dxvidparham/ftready)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Check if your Python project dependencies are ready for **free-threaded Python** (3.13t / 3.14t).

Supports `pyproject.toml` (PEP 621 + Poetry), `requirements.txt`, and any custom requirements-style file.
Queries the **PyPI JSON API** for `cp313t`/`cp314t` wheel tags as the primary source and optionally
enriches results with [ft-checker.com](https://ft-checker.com) test data.

## Installation

```bash
# From PyPI (includes rich-click for styled output)
pip install ftready

# Or via uv
uv tool install ftready
```

## Usage

```bash
# Check direct dependencies from pyproject.toml (default)
ftready

# Check a requirements.txt file
ftready --requirements requirements.txt

# Check a custom dependency file (any requirements-style format)
ftready --requirements path/to/deps.txt

# Point to a specific pyproject.toml
ftready --pyproject path/to/pyproject.toml

# Include dev dependencies (pyproject.toml mode only)
ftready --include-dev

# Check ALL dependencies (direct + transitive via poetry.lock)
ftready --all-deps

# Write report to file
ftready --output report.txt

# Force plain-text output (no rich)
ftready --plain

# Verbose output
ftready -v

# Force fresh scrape (ignore ft-checker cache)
ftready --no-cache

# Skip ft-checker.com enrichment (PyPI only)
ftready --no-ftchecker

# Skip PyPI lookups (ft-checker only)
ftready --no-pypi

# Exit 0 regardless of results (report only, never block CI)
ftready --fail-on=never

# Exit 1 if any direct dep is Failed or Unknown
ftready --fail-on=unknown
```

## How It Works

1. Parses `pyproject.toml` (PEP 621 and Poetry formats) **or** a `requirements.txt`-style file
2. Queries the **PyPI JSON API** in parallel to detect `cp313t`/`cp314t` wheel tags (primary)
3. Optionally enriches with [ft-checker.com](https://ft-checker.com) test results (catches failures that wheels alone can't detect)
4. Renders a styled table showing compatibility status for each dependency

## Exit Codes

| Code | Meaning                                                          |
| ---- | ---------------------------------------------------------------- |
| `0`  | No blocking issues found (see `--fail-on` for what counts)       |
| `1`  | At least one direct dependency has a **Failed** status (default) |
| `2`  | Configuration error (input file not found, etc.)                 |

Control the exit code threshold with `--fail-on={never,failed,unknown}`.

## CI Usage

Add `ftready` to your GitHub Actions workflow to track free-threaded readiness over time.
Use `--fail-on=never` to report without blocking the pipeline:

```yaml
- name: Check free-threaded compatibility
  run: |
    pip install ftready
    ftready --output report.txt --plain --fail-on=never -v
```

To fail the build when any dependency is known-incompatible:

```yaml
- name: Check free-threaded compatibility
  run: |
    pip install ftready
    ftready --plain -v
```

For `requirements.txt` projects:

```yaml
- name: Check free-threaded compatibility
  run: |
    pip install ftready
    ftready --requirements requirements.txt --output report.txt --plain -v
```

## Data Sources

| Source                                   | Role                                                  | Coverage              |
| ---------------------------------------- | ----------------------------------------------------- | --------------------- |
| PyPI JSON API (`/pypi/{pkg}/json`)       | **Primary** — wheel tag detection (`cp313t`/`cp314t`) | Every package on PyPI |
| [ft-checker.com](https://ft-checker.com) | **Enrichment** — actual test results                  | ~1000 top packages    |

PyPI is queried in parallel for every dependency. ft-checker.com data is cached locally for 24 hours
(configurable via `--cache-ttl`). The cache path defaults to `.ft_cache.json` and can be changed with `--cache-file`.

When both sources have data for a package, ft-checker.com takes priority because it has actual test results
(a package may ship `cp313t` wheels but still fail tests).

## License

MIT
