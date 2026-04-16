import logging
from datetime import timedelta

from celery import shared_task
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_enrollment_followup_email(self):
    """Send followup email to seekers who enrolled ~1 hour ago."""
    from .models import Enrollment

    now = timezone.now()
    sent_count = 0

    with transaction.atomic():
        enrollments = (
            Enrollment.objects.select_for_update(skip_locked=True)
            .filter(
                followup_sent=False,
                status="enrolled",
                created_at__lte=now - timedelta(minutes=55),
                created_at__gte=now - timedelta(minutes=65),
            )
            .select_related("event", "seeker")
        )
        for enrollment in enrollments:
            try:
                send_mail(
                    subject=f"Thanks for enrolling in {enrollment.event.title}!",
                    message=(
                        f"You're enrolled in {enrollment.event.title}. "
                        f"It starts on {enrollment.event.starts_at.strftime('%B %d, %Y at %H:%M UTC')}."
                    ),
                    from_email=None,
                    recipient_list=[enrollment.seeker.email],
                )
                enrollment.followup_sent = True
                enrollment.save(update_fields=["followup_sent"])
                sent_count += 1
            except Exception as e:
                logger.error(
                    "followup_email_failed",
                    extra={"enrollment_id": enrollment.id, "error": str(e)},
                )

    logger.info("followup_emails_sent", extra={"count": sent_count})


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_event_reminder_email(self):
    """Send reminder email to seekers whose event starts in ~1 hour."""
    from .models import Enrollment

    now = timezone.now()
    sent_count = 0

    with transaction.atomic():
        enrollments = (
            Enrollment.objects.select_for_update(skip_locked=True)
            .filter(
                reminder_sent=False,
                status="enrolled",
                event__starts_at__gte=now + timedelta(minutes=55),
                event__starts_at__lte=now + timedelta(minutes=65),
            )
            .select_related("event", "seeker")
        )
        for enrollment in enrollments:
            try:
                send_mail(
                    subject=f"Reminder: {enrollment.event.title} starts soon!",
                    message=(
                        f"Reminder: {enrollment.event.title} starts in about 1 hour "
                        f"at {enrollment.event.location}!"
                    ),
                    from_email=None,
                    recipient_list=[enrollment.seeker.email],
                )
                enrollment.reminder_sent = True
                enrollment.save(update_fields=["reminder_sent"])
                sent_count += 1
            except Exception as e:
                logger.error(
                    "reminder_email_failed",
                    extra={"enrollment_id": enrollment.id, "error": str(e)},
                )

    logger.info("reminder_emails_sent", extra={"count": sent_count})
