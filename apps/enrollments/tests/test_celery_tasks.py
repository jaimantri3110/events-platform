from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.events.tests.factories import EventFactory
from apps.users.tests.factories import VerifiedSeekerFactory

from ..tasks import send_enrollment_followup_email, send_event_reminder_email
from .factories import EnrollmentFactory


@pytest.mark.django_db
def test_followup_email_sent_after_one_hour():
    now = timezone.now()
    seeker = VerifiedSeekerFactory()
    event = EventFactory()
    enrollment = EnrollmentFactory(seeker=seeker, event=event, status="enrolled", followup_sent=False)

    # Backdate creation to ~1 hour ago
    from apps.enrollments.models import Enrollment

    Enrollment.objects.filter(pk=enrollment.pk).update(created_at=now - timedelta(minutes=60))

    with patch("apps.enrollments.tasks.send_mail") as mock_send:
        send_enrollment_followup_email()

    mock_send.assert_called_once()
    enrollment.refresh_from_db()
    assert enrollment.followup_sent is True


@pytest.mark.django_db
def test_followup_not_resent():
    now = timezone.now()
    seeker = VerifiedSeekerFactory()
    event = EventFactory()
    enrollment = EnrollmentFactory(seeker=seeker, event=event, status="enrolled", followup_sent=True)

    from apps.enrollments.models import Enrollment

    Enrollment.objects.filter(pk=enrollment.pk).update(created_at=now - timedelta(minutes=60))

    with patch("apps.enrollments.tasks.send_mail") as mock_send:
        send_enrollment_followup_email()

    mock_send.assert_not_called()


@pytest.mark.django_db
def test_reminder_email_sent_one_hour_before():
    now = timezone.now()
    seeker = VerifiedSeekerFactory()
    event = EventFactory(
        starts_at=now + timedelta(minutes=60),
        ends_at=now + timedelta(minutes=60, hours=2),
    )
    enrollment = EnrollmentFactory(seeker=seeker, event=event, status="enrolled", reminder_sent=False)

    with patch("apps.enrollments.tasks.send_mail") as mock_send:
        send_event_reminder_email()

    mock_send.assert_called_once()
    enrollment.refresh_from_db()
    assert enrollment.reminder_sent is True


@pytest.mark.django_db
def test_reminder_not_resent():
    now = timezone.now()
    seeker = VerifiedSeekerFactory()
    event = EventFactory(
        starts_at=now + timedelta(minutes=60),
        ends_at=now + timedelta(minutes=60, hours=2),
    )
    EnrollmentFactory(seeker=seeker, event=event, status="enrolled", reminder_sent=True)

    with patch("apps.enrollments.tasks.send_mail") as mock_send:
        send_event_reminder_email()

    mock_send.assert_not_called()
