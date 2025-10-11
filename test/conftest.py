# -*- coding: utf-8 -*-
"""
Pytest configuration and shared fixtures for zBot async races testing.
"""
import sys
from pathlib import Path

import pytest

# Add the project root to the Python path so we can import modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_user_id():
    """Returns a sample Discord user ID for testing."""
    return 123456789


@pytest.fixture
def sample_guild_id():
    """Returns a sample Discord guild/server ID for testing."""
    return 987654321


# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test (no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test (with mocked dependencies)"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test (full workflow)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )

