# ftready

Check if your Python project dependencies are ready for **free-threaded Python** (3.13t / 3.14t).

Supports `pyproject.toml` (PEP 621 + Poetry), `requirements.txt`, and any custom requirements-style file.
Uses [ft-checker.com](https://ft-checker.com) as the primary database and falls back to PyPI wheel tag
detection for packages not yet tracked there.

## Installation

```bash
# From source
pip install .

# With rich tables (recommended)
pip install ".[rich]"
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

# Force fresh scrape (ignore cache)
ftready --no-cache

# Exit 0 regardless of results (report only, never block CI)
ftready --fail-on=never

# Exit 1 if any direct dep is Failed or Unknown
ftready --fail-on=unknown
```

## How It Works

1. Parses `pyproject.toml` (PEP 621 and Poetry formats) **or** a `requirements.txt`-style file
2. Scrapes [ft-checker.com](https://ft-checker.com) for known compatibility data (cached locally for 24h)
3. Falls back to the PyPI JSON API to check for `cp313t`/`cp314t` wheel tags for any package absent from ft-checker
4. Renders a table showing compatibility status for each dependency

## Exit Codes

| Code | Meaning                                                          |
| ---- | ---------------------------------------------------------------- |
| `0`  | No blocking issues found (see `--fail-on` for what counts)       |
| `1`  | At least one direct dependency has a **Failed** status (default) |
| `2`  | Configuration error (input file not found, etc.)                 |

Control the exit code threshold with `--fail-on={never,failed,unknown}`.

## Pre-commit Hook

Add `ftready` as a pre-commit hook to block commits when known-incompatible packages are added.

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/dxvidparham/ftready
    rev: v0.1.0
    hooks:
      # For pyproject.toml projects
      - id: ftready

      # For requirements.txt projects
      - id: ftready-requirements
```

Or configure it manually with custom args:

```yaml
repos:
  - repo: https://github.com/dxvidparham/ftready
    rev: v0.1.0
    hooks:
      - id: ftready
        args: [--fail-on=unknown, --plain]
```

## CI Usage

```yaml
- name: Check free-threaded compatibility
  run: |
    pip install ftready
    ftready --output report.txt --plain -v
```

For `requirements.txt` projects:

```yaml
- name: Check free-threaded compatibility
  run: |
    pip install ftready
    ftready --requirements requirements.txt --output report.txt --plain -v
```

## Data Sources

| Source                                   | Use                                                |
| ---------------------------------------- | -------------------------------------------------- |
| [ft-checker.com](https://ft-checker.com) | Primary — daily-tested top-1000 PyPI packages      |
| PyPI JSON API (`/pypi/{pkg}/json`)       | Fallback — wheel tag (`cp313t`/`cp314t`) detection |

ft-checker.com data is cached locally for 24 hours (configurable via `--cache-ttl`).
The cache path defaults to `.ft_cache.json` and can be changed with `--cache-file`.

## License

MIT

