"""
Pytest configuration for the patients app tests.
"""
import os
import pytest
import django
from django.conf import settings

def pytest_configure():
    """Configure Django settings for pytest."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pigw.settings.dev")
    django.setup()


@pytest.fixture(autouse=True)
def disable_csrf(settings):
    """Disable CSRF middleware for all tests."""
    settings.MIDDLEWARE = tuple(
        m for m in settings.MIDDLEWARE
        if 'csrf' not in m.lower()
    )

