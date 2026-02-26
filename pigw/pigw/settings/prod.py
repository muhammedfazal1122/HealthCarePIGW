"""
Production settings for pigw.

Key differences from dev:
  - DEBUG = False
  - Fernet key validation at startup
  - Secure cookie and HSTS settings
  - Postgres-only database
  - Console logging at INFO level
"""
import os
import sys

from .base import *  # noqa: F401, F403

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
DEBUG = False

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]  # hard fail if missing

# ALLOWED_HOSTS set to ['*'] for the assessment.
# In real production, replace with your actual domain(s) e.g. ['api.example.com'].
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")

# ---------------------------------------------------------------------------
# Fernet key – fail fast if missing rather than silently accepting broken crypto
# ---------------------------------------------------------------------------
FERNET_KEY: str = os.environ.get("FERNET_KEY", "")
if not FERNET_KEY:
    print(
        "FATAL: FERNET_KEY environment variable is not set. "
        "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"",
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Database – Postgres required in production (no SQLite fallback)
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["POSTGRES_DB"],
        "USER": os.environ["POSTGRES_USER"],
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,  # persistent connections
    }
}

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
# HSTS: tell browsers to use HTTPS for 1 year (including subdomains)
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SESSION_COOKIE_SECURE = True   # session cookie only over HTTPS
CSRF_COOKIE_SECURE = True      # CSRF cookie only over HTTPS

# Enable SSL redirect unless explicitly disabled (e.g., when terminating TLS
# at a load balancer that forwards plain HTTP internally)
_ssl_redirect = os.environ.get("SECURE_SSL_REDIRECT", "true").lower()
SECURE_SSL_REDIRECT = _ssl_redirect == "true"

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# ---------------------------------------------------------------------------
# Static / media (Whitenoise or object storage in production)
# ---------------------------------------------------------------------------
STATIC_ROOT = os.environ.get("STATIC_ROOT", "/app/staticfiles")

# ---------------------------------------------------------------------------
# Celery (optional – only active when CELERY_BROKER_URL is set)
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "")

# ---------------------------------------------------------------------------
# Logging – console handler at INFO, errors to stderr
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{levelname}] {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "patients": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
