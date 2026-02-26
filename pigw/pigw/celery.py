"""
Celery application factory for pigw.

Autodiscovers tasks from all installed apps (e.g. patients/tasks.py).
Run a worker with:
    celery -A pigw worker -l info
"""
import os

from celery import Celery

# Default to dev settings; override with DJANGO_SETTINGS_MODULE in production
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pigw.settings.dev")
app = Celery("pigw")

# Read Celery config from Django settings with the CELERY_ prefix
app.config_from_object("django.conf:settings", namespace="CELERY")



# Autodiscover tasks.py modules in all INSTALLED_APPS
app.autodiscover_tasks()
