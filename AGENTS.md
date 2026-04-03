# AGENTS.md

You are an expert Python developer working on a CLI tool for checking free-threaded Python compatibility.

## Project Summary

**ftready** is a standalone CLI tool that checks whether a Python project's dependencies support free-threaded Python (3.13t / 3.14t). It scrapes [ft-checker.com](https://ft-checker.com) and falls back to the PyPI JSON API to determine compatibility from wheel filenames (`cp313t`, `cp314t`).

**Tech Stack:** Python 3.11+, Hatchling, stdlib-only (rich optional), Ruff, ty, pytest

## File Structure

- `src/ftready/` — Core package (parser, scraper, checker, report, cli, models, constants)
- `tests/` — Unit tests (pytest)
- `.github/workflows/` — CI and weekly ft-checker workflow
- `.github/copilot-instructions.md` — Code style and conventions

## Commands You Can Use

### Testing
```bash
# Run all tests with coverage (primary test command)
pytest --cov-branch --cov=ftready

# Run specific test file
pytest tests/test_parser.py -v

# Run specific test function
pytest tests/test_parser.py::test_function_name -v

# Run including slow/network tests
pytest -m "slow" -v
pytest -m "network" -v
```

### Linting and Formatting
```bash
# Check for linting issues
ruff check .

# Auto-fix linting issues
ruff check --fix .

# Format code
ruff format .

# Run pre-commit hooks on all files
prek --all-files
```

### Type Checking
```bash
ty check
```

### Building
```bash
pip install -e ".[rich]"
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
  1. Run `ruff check --fix . && ruff format .`
  2. Run `pytest --cov-branch --cov=ftready`
  3. Ensure all tests pass

## Boundaries

### Always Do
- Run `pytest --cov-branch --cov=ftready` before committing
- Run `ruff check --fix . && ruff format .` after code changes
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
