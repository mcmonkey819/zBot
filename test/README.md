# zBot Async Races - Testing Suite

This directory contains the test suite for the zBot async races Discord bot.

## Setup

### Install Test Dependencies

From the project root, install the test requirements:

```bash
pip install -r test/requirements.txt
```

Or install individual packages:

```bash
pip install pytest pytest-asyncio pytest-mock pytest-cov
```

### Verify Installation

Check that pytest is installed correctly:

```bash
pytest --version
```

## Running Tests

### Run All Tests

From the project root:

```bash
pytest test/
```

### Run Specific Test Files

```bash
# Run only formatter tests
pytest test/unit/test_ui_util_formatters.py

# Run all unit tests
pytest test/unit/
```

### Run Specific Test Classes or Functions

```bash
# Run a specific test class
pytest test/unit/test_ui_util_formatters.py::TestGetPlaceStr

# Run a specific test function
pytest test/unit/test_ui_util_formatters.py::TestGetPlaceStr::test_first_place
```

### Run with Verbose Output

```bash
pytest -v test/
```

### Run with Coverage Report

```bash
# Basic coverage
pytest --cov=ui --cov=cogs test/

# Coverage with missing lines
pytest --cov=ui --cov=cogs --cov-report=term-missing test/

# Generate HTML coverage report
pytest --cov=ui --cov=cogs --cov-report=html test/
# Open htmlcov/index.html in browser
```

### Run Tests by Marker

Tests are marked with custom markers for organization:

```bash
# Run only unit tests (no dependencies)
pytest -m unit test/

# Run only integration tests
pytest -m integration test/

# Run only slow tests
pytest -m slow test/

# Exclude slow tests
pytest -m "not slow" test/
```

## Test Organization

```
test/
├── conftest.py              # Pytest configuration and shared fixtures
├── requirements.txt         # Test dependencies
├── __init__.py              # Package initialization
├── unit/                    # Unit tests (no external dependencies)
│   ├── __init__.py
│   ├── test_ui_util_formatters.py    # Formatting function tests
│   └── ...
├── integration/             # Integration tests (with mocked dependencies)
│   └── ...
└── e2e/                     # End-to-end tests (full workflows)
    └── ...
```

## Writing Tests

### Example Unit Test

```python
import pytest
from ui.ui_util import get_place_str

@pytest.mark.unit
def test_first_place():
    """Test 1st place formatting."""
    assert get_place_str(1) == "1st"
```

### Example Async Test

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Test an async function."""
    result = await some_async_function()
    assert result == expected_value
```

### Using Fixtures

```python
def test_with_fixture(sample_user_id):
    """Test using a fixture from conftest.py."""
    assert sample_user_id == 123456789
```

## Test Markers

Available markers (defined in `conftest.py`):
- `@pytest.mark.unit` - Pure unit tests with no external dependencies
- `@pytest.mark.integration` - Integration tests with mocked dependencies
- `@pytest.mark.e2e` - End-to-end tests with full workflows
- `@pytest.mark.slow` - Tests that take significant time to run

## Continuous Integration

When running tests in CI/CD:

```bash
# Run tests with coverage and JUnit XML output
pytest --cov=ui --cov=cogs --cov-report=xml --junitxml=test-results.xml test/
```

## Current Test Status

See `test_checklist.md` for the comprehensive testing checklist and progress tracking.

**Phase 1 (Pure Functions)**: ✅ 2/11 tests implemented
- ✅ `get_place_str()` - Complete
- ✅ `format_points_str()` - Complete
- ☐ Other Phase 1 tests - Pending

**Phase 2 (Business Logic)**: ☐ 0/24 tests implemented

**Phase 3 (Complex Interactions)**: ☐ 0/21 tests implemented

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError` when running tests:

1. Make sure you're running pytest from the project root
2. Check that `conftest.py` is properly adding the project root to `sys.path`
3. Verify your Python path: `echo $PYTHONPATH`

### Async Test Issues

If async tests don't run:

1. Ensure `pytest-asyncio` is installed
2. Mark async tests with `@pytest.mark.asyncio`
3. Check that `pytest_plugins = ('pytest_asyncio',)` is in `conftest.py`

### Test Discovery Issues

Pytest uses naming conventions to discover tests:
- Test files: `test_*.py` or `*_test.py`
- Test functions: `test_*`
- Test classes: `Test*`

Make sure your tests follow these conventions.

