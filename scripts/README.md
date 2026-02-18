# Development Scripts

This directory contains scripts for maintaining code quality in the RAG chatbot project.

## Overview

All scripts must be run from the project root directory.

## Scripts

### `quality.sh` - Master Script
Runs all quality checks in sequence: format → lint → type check → test.

**Usage:**
```bash
./scripts/quality.sh
```

**What it does:**
1. Formats all Python code with Ruff
2. Runs linting checks
3. Performs static type checking with Mypy
4. Runs the test suite with coverage reporting

**When to use:** Before committing code or opening a pull request.

---

### `format.sh` - Code Formatting
Formats Python code using Ruff (Black-compatible) and sorts imports.

**Usage:**
```bash
./scripts/format.sh
```

**What it does:**
- Formats code to 100-character line length
- Enforces consistent quote style (double quotes)
- Sorts imports (stdlib → third-party → local)
- Fixes spacing and indentation

**When to use:** After making code changes, before committing.

---

### `lint.sh` - Code Linting
Checks code for common errors and style violations.

**Usage:**
```bash
./scripts/lint.sh
```

**What it checks:**
- Undefined names and unused imports
- PEP 8 naming conventions
- Common bug patterns (flake8-bugbear)
- Simplification opportunities
- Code complexity

**Auto-fix mode:**
```bash
cd backend && uv run ruff check --fix .
```

**When to use:** During development to catch issues early.

---

### `typecheck.sh` - Static Type Checking
Validates type hints using Mypy.

**Usage:**
```bash
./scripts/typecheck.sh
```

**What it checks:**
- Type mismatches
- Missing return types
- Incompatible types in assignments
- Function signature violations

**When to use:** After modifying function signatures or adding type hints.

---

### `test.sh` - Test Suite with Coverage
Runs pytest with coverage reporting.

**Usage:**
```bash
./scripts/test.sh
```

**What it does:**
- Runs all tests in `backend/tests/`
- Generates branch coverage report
- Creates HTML coverage report at `backend/htmlcov/index.html`
- Shows coverage summary in terminal

**View coverage report:**
```bash
open backend/htmlcov/index.html  # macOS
xdg-open backend/htmlcov/index.html  # Linux
```

**When to use:** After modifying code, before committing.

---

## Quick Reference

| Task | Command |
|------|---------|
| Run all checks | `./scripts/quality.sh` |
| Format code | `./scripts/format.sh` |
| Check for errors | `./scripts/lint.sh` |
| Fix linting issues | `cd backend && uv run ruff check --fix .` |
| Type check | `./scripts/typecheck.sh` |
| Run tests | `./scripts/test.sh` |
| View coverage | `open backend/htmlcov/index.html` |

## Troubleshooting

**"Permission denied" error:**
```bash
chmod +x scripts/*.sh
```

**"Module not found" error:**
```bash
uv sync  # Install dependencies
```

**Linting failures:**
- Review the output for specific errors
- Run `cd backend && uv run ruff check --fix .` to auto-fix issues
- Some issues require manual fixes (e.g., undefined names)

**Type checking errors:**
- Review Mypy output for type mismatches
- Add type hints where missing
- Use `# type: ignore` for unavoidable third-party issues

## Configuration

All tool configurations are in `pyproject.toml`:

- **Ruff**: `[tool.ruff]` and `[tool.ruff.lint]`
- **Mypy**: `[tool.mypy]`
- **Pytest**: `[tool.pytest.ini_options]`
- **Coverage**: `[tool.coverage.run]` and `[tool.coverage.report]`

## Integration with Development Workflow

**Before starting work:**
```bash
git checkout -b feature/my-feature
```

**During development:**
```bash
./scripts/format.sh  # Keep code formatted
./scripts/lint.sh    # Check for issues
```

**Before committing:**
```bash
./scripts/quality.sh  # Run all checks
git add .
git commit -m "Add feature"
```

**Before pushing:**
```bash
./scripts/test.sh     # Ensure tests pass
git push origin feature/my-feature
```
