# Import the Celery app so @shared_task decorators resolve correctly
# when Django apps are loaded. This must stay here.
from .celery import app as celery_app  # noqa: F401

__all__ = ["celery_app"]
