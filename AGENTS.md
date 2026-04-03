# AGENTS.md

You are an expert Python developer working on a CLI tool for checking free-threaded Python compatibility.

## Project Summary

**ftready** is a standalone CLI tool that checks whether a Python project's dependencies support free-threaded Python (3.13t / 3.14t). It scrapes [ft-checker.com](https://ft-checker.com) and falls back to the PyPI JSON API to determine compatibility from wheel filenames (`cp313t`, `cp314t`).

**Tech Stack:** Python 3.11+, uv, Hatchling, stdlib-only (rich optional), Ruff, ty, pytest

## File Structure

- `src/ftready/` — Core package (parser, scraper, checker, report, cli, models, constants)
- `tests/` — Unit tests (pytest)
- `.github/workflows/` — CI, weekly ft-checker, release, and publish workflows
- `.github/copilot-instructions.md` — Code style and conventions

## Commands You Can Use

### Project Management (uv)
```bash
# Sync all dependencies (dev + extras)
uv sync --all-extras

# Add a dev dependency
uv add --group dev <package>

# Build distributions (sdist + wheel)
uv build

# Update lockfile
uv lock
```

### Testing
```bash
# Run all tests with coverage (primary test command)
uv run pytest --cov-branch --cov=ftready

# Run specific test file
uv run pytest tests/test_parser.py -v

# Run specific test function
uv run pytest tests/test_parser.py::test_function_name -v

# Run including slow/network tests
uv run pytest -m "slow" -v
uv run pytest -m "network" -v
```

### Linting and Formatting
```bash
# Check for linting issues
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .

# Format code
uv run ruff format .

# Run pre-commit hooks on all files
uv run prek --all-files
```

### Type Checking
```bash
uv run ty check
```

### Building & Publishing
```bash
# Build sdist + wheel
uv build

# Publish to PyPI (CI handles this via trusted publishing)
uv publish
```

### Releasing
```bash
# Preview next version (dry run)
uv run semantic-release version --print

# Create a release (bumps version, updates CHANGELOG, tags, pushes)
# Normally done via GitHub Actions on push to main
uv run semantic-release version
```

## Testing Standards

- Write tests using **pytest** and place them in `tests/`
- Use **pytest-mock's `mocker` fixture** for mocking
- Always use `autospec=True` when patching
- Mock where the object is **used**, not where it's defined
- **All tests must run offline** — mock all HTTP calls
- Tests requiring network: mark with `@pytest.mark.network`

## Code Style

- Use **Sphinx-style RST docstrings** for public classes and functions
- Follow Ruff linting rules defined in `pyproject.toml`
- Type hints on all function signatures
- **Zero runtime dependencies** — only stdlib; `rich` is optional

## PR and Commit Guidelines

- **Commit messages:** [Conventional Commits](https://www.conventionalcommits.org/) format
- **Before opening a PR:**
  1. Run `uv run ruff check --fix . && uv run ruff format .`
  2. Run `uv run pytest --cov-branch --cov=ftready`
  3. Ensure all tests pass

## Boundaries

### Always Do
- Run `uv run pytest --cov-branch --cov=ftready` before committing
- Run `uv run ruff check --fix . && uv run ruff format .` after code changes
- Write tests for all new features
- Use type hints on all function signatures
- Mock all HTTP calls in tests
- Follow Conventional Commits format

### Ask First
- Before adding runtime dependencies (this tool is stdlib-only by design)
- Before modifying CI/CD workflows

### Never Do
- Make real HTTP calls in tests (except `@pytest.mark.network`)
- Use wildcard imports (`from module import *`)
- Add runtime dependencies beyond stdlib + optional rich
