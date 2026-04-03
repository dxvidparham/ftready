# Copilot Instructions

These instructions guide GitHub Copilot in understanding code style, conventions, and best practices for this repository. For executable commands, build/test workflows, and agent-specific boundaries, see the [AGENTS.md](../AGENTS.md) file in the repository root.

---

## Code Standards

### Documentation Requirements

* All documentation and code must be written in **English**.
* Use **Sphinx-style reStructuredText (RST)** docstrings for all public classes and functions:

```python
"""Check project dependencies for free-threaded Python compatibility.

:param pyproject_path: Path to the pyproject.toml file
:param include_dev: When True, also include dev dependencies
:return: List of compatibility results
"""
```

* Exclude `:type`, `:raises`, and `:rtype` fields — these are inferred from type annotations.
* For small, self-explanatory functions, use one-line docstrings.

### Python Code Style

* Follow **Ruff** linting rules as configured in `pyproject.toml`.
* `rich-click` is the sole required runtime dependency (provides Click CLI + Rich output).
* Apply core design principles: **SOC**, **DRY**, **KISS**, **YAGNI**.
* Optimize for **clarity and maintainability** over cleverness or micro-optimization.

---

## Import Management

* Use `__init__.py` to define the public API of `ftready`.
* Use explicit imports — no wildcard imports (`from .module import *`).
* Group imports: standard library → third-party → local application.

---

## Testing Best Practices

### Mock Guidelines

* Mock where the object is **used**, not where it's defined.
* Use `autospec=True` to prevent invalid mock usage.
* Add call assertions to verify mock interactions.
* Use **pytest-mock's `mocker` fixture** (not `@patch` decorators).

```python
def test_example(mocker):
    mock_func = mocker.patch("ftready.scraper._http_get", autospec=True)
    mock_func.assert_called_once_with(expected_url)
```

### Network Isolation

* All tests must run **without network access** by default.
* Mock HTTP calls in unit tests — never hit ft-checker.com or PyPI in CI.
* Tests that require network access must be marked with `@pytest.mark.network`.
