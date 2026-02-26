"""
Development settings – loads .env file for local dev convenience.
Uses SQLite if Postgres env vars are not configured.
"""
import os
from pathlib import Path
from .base import *  # noqa: F401, F403

try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
    load_dotenv(dotenv_path=_env_path)
except ImportError:
    pass 

# ------------
# Core
# ---------------------------------------------------------------------------
DEBUG = True

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "dev-insecure-key-change-before-production",  # safe for local dev only
)

ALLOWED_HOSTS = ["*"]

 # Database – SQLite fallback when Postgres env vars are absent
# ---------------------------------------------------------------------------
_pg_db = os.environ.get("POSTGRES_DB")
_pg_user = os.environ.get("POSTGRES_USER")
_pg_pass = os.environ.get("POSTGRES_PASSWORD")
_pg_host = os.environ.get("POSTGRES_HOST", "localhost")
_pg_port = os.environ.get("POSTGRES_PORT", "5432")

if _pg_db and _pg_user and _pg_pass:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": _pg_db,
            "USER": _pg_user,
            "PASSWORD": _pg_pass,
            "HOST": _pg_host,
            "PORT": _pg_port,
        }
    }


else:
     
    BASE_DIR_ = Path(__file__).resolve().parent.parent.parent
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR_ / "db.sqlite3",
        }
    }

# Encryption key ::::-- required even in dev (generate once, store in .env)
FERNET_KEY: str = os.environ.get("FERNET_KEY", "")
