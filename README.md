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
  <a href="https://github.com/dxvidparham/ftready"><img src="https://img.shields.io/badge/coverage-92%25-brightgreen" alt="Coverage"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
</p>

<p align="center">
  <a href="#-quickstart">Quickstart</a> ·
  <a href="#-features">Features</a> ·
  <a href="#-usage">Usage</a> ·
  <a href="#-ci-integration">CI Integration</a> ·
  <a href="https://pypi.org/project/ftready/">PyPI</a>
</p>

---

Python 3.13 shipped a **free-threaded build** (`-t` suffix) that disables the GIL — unlocking true multi-core parallelism. But your project is only as ready as its **least-compatible dependency**.

`ftready` scans your dependency tree, queries PyPI for `cp313t`/`cp314t` wheels, cross-references [ft-checker.com](https://ft-checker.com) test results, and tells you exactly where you stand:

```
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
pip install ftready
ftready
```

That's it. Reads your `pyproject.toml` and prints a compatibility report.

## 🎯 Features

- **PyPI-first detection** — queries `cp313t`/`cp314t` wheel tags in parallel for every dependency
- **Real test results** — enriches with [ft-checker.com](https://ft-checker.com) data covering ~1000 top packages
- **Pure-Python detection** — flags packages with no C extensions as likely compatible
- **Every input format** — `pyproject.toml` (PEP 621 + Poetry), `requirements.txt`, `uv.lock`, `poetry.lock`, `pdm.lock`
- **Full dependency tree** — `--all-deps` scans transitive deps via lock files with pinned-version accuracy
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
```

### Data source control

```bash
ftready --no-ftchecker   # PyPI only (skip ft-checker.com)
ftready --no-pypi        # ft-checker only (skip PyPI)
ftready --no-cache       # force fresh ft-checker scrape
```

### Exit codes

| Code | Meaning |
| ---- | ------- |
| `0`  | No blocking issues (configurable via `--fail-on`) |
| `1`  | At least one dependency has a **Failed** status |
| `2`  | Configuration error (missing input file, etc.) |

```bash
ftready --fail-on=never    # always exit 0 (report only)
ftready --fail-on=unknown  # exit 1 on Failed OR Unknown
ftready --fail-on=failed   # exit 1 on Failed only (default)
```

## 🔄 How It Works

```
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

## 📊 Data Sources

| Source | Role | Coverage |
| ------ | ---- | -------- |
| PyPI JSON API | **Primary** — `cp313t`/`cp314t` wheel tag detection | Every package on PyPI |
| PyPI version endpoint | **Primary** — pinned-version checking from lock files | Every package on PyPI |
| [ft-checker.com](https://ft-checker.com) | **Enrichment** — actual test results | ~1000 top packages |

When both sources report on a package, ft-checker.com takes priority — a package may ship free-threaded wheels but still fail tests.

## 📄 License

[MIT](LICENSE)
