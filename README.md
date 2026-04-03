<h1 align="center">
  🧵 ftready
</h1>

<p align="center">
  <strong>Is your project ready for free-threaded Python? Find out in one command.</strong>
</p>

<p align="center">
  <a href="https://github.com/dxvidparham/ftready/actions/workflows/ci.yml"><img src="https://github.com/dxvidparham/ftready/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/ftready/"><img src="https://img.shields.io/pypi/v/ftready" alt="PyPI version"></a>
  <a href="https://pypi.org/project/ftready/"><img src="https://img.shields.io/pypi/pyversions/ftready" alt="Python versions"></a>
  <a href="https://github.com/dxvidparham/ftready"><img src="https://img.shields.io/badge/coverage-93%25-brightgreen" alt="Coverage"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
</p>

<p align="center">
  <a href="#-quickstart">Quickstart</a> ·
  <a href="#-features">Features</a> ·
  <a href="#-usage">Usage</a> ·
  <a href="#-tracking-progress">Tracking Progress</a> ·
  <a href="#-ci-integration">CI Integration</a> ·
  <a href="#-python-api">Python API</a> ·
  <a href="https://pypi.org/project/ftready/">PyPI</a>
</p>

---

[PEP 703](https://peps.python.org/pep-0703/) introduced a **free-threaded build** of CPython (3.13t) that disables the GIL — unlocking true multi-core parallelism. [PEP 779](https://peps.python.org/pep-0779/) made free-threading a **supported** (no longer experimental) feature in CPython 3.14. But your project is only as ready as its **least-compatible dependency**. See the [free-threading guide](https://py-free-threading.github.io/) for background.

`ftready` scans your dependency tree, queries PyPI for `cp313t`/`cp314t` wheels, cross-references [ft-checker.com](https://ft-checker.com) test results, and tells you exactly where you stand:

```text
 Package          Compatibility   Details
─────────────────────────────────────────────────────
 numpy            ✅ Success      free-threaded wheel found
 pandas           ✅ Success      free-threaded wheel found
 scipy            ✅ Success      free-threaded wheel found
 scikit-learn     ✅ Success      free-threaded wheel found
 matplotlib       ✅ Success      free-threaded wheel found
 pillow           ✅ Success      free-threaded wheel found
 opencv-python    ⬜ Not tested
 tqdm             🐍 Pure Python  likely compatible (no C extensions)
 loguru           🐍 Pure Python  likely compatible (no C extensions)
─────────────────────────────────────────────────────
 ✅ 6 passed · ❌ 0 failed · ⬜ 1 unknown · 🐍 2 pure
```

## ⚡ Quickstart

```bash
pip install ftready   # or: uv tool install ftready
ftready
```

That's it. Reads your `pyproject.toml` and prints a compatibility report.

## 🎯 Features

- **PyPI-first detection** — queries `cp313t`/`cp314t` wheel tags in parallel for every dependency
- **Real test results** — enriches with [ft-checker.com](https://ft-checker.com) data covering ~1000 top packages
- **Pure-Python detection** — flags packages with no C extensions as likely compatible
- **Every input format** — `pyproject.toml` (PEP 621 + Poetry), `requirements.txt`, `uv.lock`, `poetry.lock`, `pdm.lock`
- **Full dependency tree** — `--all-deps` scans transitive deps via lock files with pinned-version accuracy
- **Progress tracking** — `ftready diff` compares two JSON reports to show what changed over time
- **Multiple outputs** — rich tables, plain text, JSON, or CSV
- **CI-ready** — configurable exit codes (`--fail-on`) to gate or report without blocking
- **Offline-safe** — `--no-ftchecker` and `--no-pypi` flags for controlled environments

## 📖 Usage

### Input sources

```bash
ftready                                    # pyproject.toml in current dir
ftready --pyproject path/to/pyproject.toml # specific pyproject.toml
ftready --requirements requirements.txt    # requirements file
ftready --include-dev                      # include dev dependencies
ftready --all-deps                         # full tree (auto-detects lock file)
ftready --all-deps --lock path/to/uv.lock  # specific lock file
```

### Output formats

```bash
ftready                       # rich table (default)
ftready --plain               # plain-text table
ftready --format json         # JSON (for scripting)
ftready --format csv          # CSV
ftready --output report.txt   # write to file
ftready -v                    # verbose progress to stderr
```

### Data source control

```bash
ftready --no-ftchecker                  # PyPI only (skip ft-checker.com)
ftready --no-pypi                       # ft-checker only (skip PyPI)
ftready --no-cache                      # force fresh ft-checker scrape
ftready --cache-ttl 48                  # cache ft-checker data for 48 hours
ftready --cache-file /tmp/ft_cache.json # custom cache location
```

### Exit codes

| Code | Meaning                                           |
| ---- | ------------------------------------------------- |
| `0`  | No blocking issues (configurable via `--fail-on`) |
| `1`  | At least one dependency has a **Failed** status   |
| `2`  | Configuration error (missing input file, etc.)    |

```bash
ftready --fail-on=never    # always exit 0 (report only)
ftready --fail-on=unknown  # exit 1 on Failed OR Unknown
ftready --fail-on=failed   # exit 1 on Failed only (default)
```

## 📈 Tracking Progress

Save JSON reports over time and use `ftready diff` to see what changed:

```bash
# Save a baseline
ftready --format json --output baseline.json

# ... weeks later, check again
ftready --format json --output current.json

# Compare the two
ftready diff baseline.json current.json
```

```text
ftready diff: 2025-01-15T12:00:00+00:00 → 2025-03-01T12:00:00+00:00

3.13t ready: 5 → 8 (+3)
3.14t ready: 2 → 5 (+3)

✅ Improved (3):
  scipy: 3.13t: Not tested → Success
  pillow: 3.13t: Not tested → Success, 3.14t: Not tested → Success
  matplotlib: 3.14t: Not tested → Success
```

The diff also supports `--format json` for machine-readable output.

## 🔄 How It Works

```text
pyproject.toml ─┐
requirements.txt ┼──▶ Parse ──▶ PyPI API ──▶ ft-checker.com ──▶ Report
uv.lock ────────┘      │        (parallel)     (optional)        │
                        │                                         │
                        └── pinned versions ──▶ exact endpoint    ▼
                                                              table/json/csv
```

1. **Parse** — reads your dependency file and extracts package names (+ pinned versions from lock files)
2. **Query PyPI** — hits `/pypi/{pkg}/json` (or `/pypi/{pkg}/{version}/json` for pinned versions) in parallel
3. **Detect pure-Python** — flags packages with only `py3-none-any` wheels and no C extensions
4. **Enrich** — optionally fetches [ft-checker.com](https://ft-checker.com) test results (cached 24h)
5. **Report** — renders results as a styled table, JSON, or CSV with configurable exit codes

> **About "Pure Python":** A package is flagged as 🐍 when *all* its published wheels use the `py3-none-any` tag — meaning no compiled C extensions. These packages typically work on free-threaded Python without changes. However, packages using `ctypes`, `cffi`, or calling native code at runtime may still have issues despite being "pure." Treat this as a strong signal, not a guarantee.

## 🏗 CI Integration

**Report without blocking:**

```yaml
- name: Check free-threaded compatibility
  run: |
    pip install ftready
    ftready --plain --fail-on=never -v
```

**Gate on failures:**

```yaml
- name: Check free-threaded compatibility
  run: |
    pip install ftready
    ftready --plain -v
```

**JSON artifact for downstream processing:**

```yaml
- name: Check free-threaded compatibility
  run: |
    pip install ftready
    ftready --format json --output ft-report.json --fail-on=never

- uses: actions/upload-artifact@v4
  with:
    name: ft-compat-report
    path: ft-report.json
```

**Track progress across CI runs** by downloading a previous artifact and diffing:

```yaml
- name: Compare with baseline
  run: |
    pip install ftready
    ftready --format json --output current.json --fail-on=never
    ftready diff baseline.json current.json || true
```

## 🐍 Python API

`ftready` exports a public API for programmatic use:

```python
from ftready import (
    load_dependencies,
    fetch_ftchecker_db,
    build_results,
    generate_report,
    diff_reports,
    format_diff,
)
from pathlib import Path

# Load deps from pyproject.toml
deps = load_dependencies(Path("pyproject.toml"))

# Query data sources
ft_db = fetch_ftchecker_db(Path(".ft_cache.json"))
results = build_results(deps, ft_db)

# Render as JSON
report = generate_report(results, include_dev=False, output_format="json")

# Compare two JSON reports
summary = diff_reports("old_report.json", "new_report.json")
print(format_diff(summary))
```

## 📊 Data Sources

| Source                                   | Role                                                  | Coverage              |
| ---------------------------------------- | ----------------------------------------------------- | --------------------- |
| PyPI JSON API                            | **Primary** — `cp313t`/`cp314t` wheel tag detection   | Every package on PyPI |
| PyPI version endpoint                    | **Primary** — pinned-version checking from lock files | Every package on PyPI |
| [ft-checker.com](https://ft-checker.com) | **Enrichment** — actual test results                  | ~1000 top packages    |

When both sources report on a package, ft-checker.com takes priority — a package may ship free-threaded wheels but still fail tests.

### Related resources

- [py-free-threading.github.io](https://py-free-threading.github.io/) — official porting guide, C-API status, and ecosystem tracker
- [hugovk.dev/free-threaded-wheels](https://hugovk.dev/free-threaded-wheels/) — auto-updated dashboard of the top 360 packages with free-threaded wheels

## ⚠️ Limitations

- **Latest release only** (without lock files): When no lock file is used, ftready checks the *latest* PyPI release. If you're pinned to an older version, use `--all-deps` with a lock file for exact version checks.
- **Wheel tags ≠ runtime compatibility**: A package shipping `cp313t` wheels doesn't guarantee it works correctly under free-threaded Python — it only means the maintainer built wheels for that target. ft-checker.com test results provide stronger evidence.
- **ft-checker.com coverage**: The enrichment source covers ~1000 popular packages. Niche packages may only have PyPI wheel tag data.
- **No transitive blocker tracing**: The tool reports status per-package but doesn't show dependency chains (e.g., "X depends on Y which depends on Z, and Z is the blocker").

## 📄 License

[MIT](LICENSE)
