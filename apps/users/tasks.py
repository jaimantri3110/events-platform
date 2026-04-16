import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def cleanup_expired_otps():
    """Remove expired, unused OTPs to keep the table clean."""
    from .models import EmailOTP

    deleted_count, _ = EmailOTP.objects.filter(
        expires_at__lt=timezone.now(),
        is_used=False,
    ).delete()
    logger.info("expired_otps_cleaned", extra={"count": deleted_count})
