# ftready

Check if your Python project dependencies are ready for **free-threaded Python** (3.13t / 3.14t).

Compares dependencies declared in `pyproject.toml` against [ft-checker.com](https://ft-checker.com) and falls back to checking PyPI wheel filenames for packages not in the ft-checker database.

## Installation

```bash
# From source
pip install .

# With rich tables (recommended)
pip install ".[rich]"
```

## Usage

```bash
# Check direct dependencies of the current project
ftready

# Point to a specific pyproject.toml
ftready --pyproject path/to/pyproject.toml

# Include dev dependencies
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
```

## How It Works

1. Parses `pyproject.toml` (PEP 621 and Poetry formats) to extract dependencies
2. Scrapes [ft-checker.com](https://ft-checker.com) for known compatibility data (cached locally for 24h)
3. Falls back to the PyPI JSON API to check for `cp313t`/`cp314t` wheel tags
4. Renders a table showing compatibility status for each dependency

## Exit Codes

- `0` — All direct dependencies are compatible (or unknown)
- `1` — At least one direct dependency has a **Failed** status
- `2` — Configuration error (missing pyproject.toml, etc.)

## CI Usage

```yaml
- name: Check free-threaded compatibility
  run: |
    pip install ftready
    ftready --output report.txt --plain -v
```

## License

MIT
