"""
Celery tasks for the patients app.

send_welcome_email is intentionally side-effect-free in the current
implementation — it writes to the Django log so it is safe to run
in any environment without SMTP configuration.

To run a Celery worker:
    celery -A pigw worker -l info

With Redis (see docker-compose.dev.yml), add to .env:
    CELERY_BROKER_URL=redis://localhost:6379/0
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_welcome_email(self, patient_id: str) -> str:
    """Notify the admin team that a new patient record was created.

    In a real deployment, replace the log statement with an email via
    Django's send_mail() or a transactional email provider (SES, SendGrid).
    """
    try:
        logger.info(
            "send_welcome_email: patient %s ingested — notify admin team.",
            patient_id,
        )
        # Placeholder: in prod call send_mail() here
        return f"welcome email logged for {patient_id}"
    except Exception as exc:  # pragma: no cover
        # Retry on transient failures (e.g. SMTP timeout)
        raise self.retry(exc=exc)
