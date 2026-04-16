from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.events.tests.factories import EventFactory
from apps.users.tests.factories import VerifiedSeekerFactory

from .factories import EnrollmentFactory


def auth_client(user):
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


@pytest.mark.django_db
def test_upcoming_enrollments():
    seeker = VerifiedSeekerFactory()
    now = timezone.now()

    future_event = EventFactory(
        starts_at=now + timedelta(days=3),
        ends_at=now + timedelta(days=3, hours=2),
    )
    past_event = EventFactory(
        starts_at=now - timedelta(days=3),
        ends_at=now - timedelta(days=3) + timedelta(hours=2),
    )
    EnrollmentFactory(seeker=seeker, event=future_event, status="enrolled")
    EnrollmentFactory(seeker=seeker, event=past_event, status="enrolled")

    client = auth_client(seeker)
    response = client.get("/api/v1/enrollments/upcoming/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["event"]["id"] == future_event.pk


@pytest.mark.django_db
def test_enrollment_history():
    seeker = VerifiedSeekerFactory()
    now = timezone.now()

    past_event_enrolled = EventFactory(
        starts_at=now - timedelta(days=5),
        ends_at=now - timedelta(days=5) + timedelta(hours=2),
    )
    past_event_canceled = EventFactory(
        starts_at=now - timedelta(days=2),
        ends_at=now - timedelta(days=2) + timedelta(hours=2),
    )
    future_event = EventFactory(
        starts_at=now + timedelta(days=3),
        ends_at=now + timedelta(days=3, hours=2),
    )
    EnrollmentFactory(seeker=seeker, event=past_event_enrolled, status="enrolled")
    EnrollmentFactory(seeker=seeker, event=past_event_canceled, status="canceled")
    EnrollmentFactory(seeker=seeker, event=future_event, status="enrolled")

    client = auth_client(seeker)
    response = client.get("/api/v1/enrollments/history/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2  # both past events (enrolled + canceled)


@pytest.mark.django_db
def test_enrollment_select_related():
    """Verify no N+1 queries on upcoming list view."""
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    seeker = VerifiedSeekerFactory()
    now = timezone.now()
    for _ in range(5):
        event = EventFactory(
            starts_at=now + timedelta(days=3),
            ends_at=now + timedelta(days=3, hours=2),
        )
        EnrollmentFactory(seeker=seeker, event=event, status="enrolled")

    client = auth_client(seeker)

    with CaptureQueriesContext(connection) as ctx:
        response = client.get("/api/v1/enrollments/upcoming/")
    assert response.status_code == status.HTTP_200_OK
    query_count_5 = len(ctx.captured_queries)

    # Add 5 more enrollments
    for _ in range(5):
        event = EventFactory(
            starts_at=now + timedelta(days=3),
            ends_at=now + timedelta(days=3, hours=2),
        )
        EnrollmentFactory(seeker=seeker, event=event, status="enrolled")

    with CaptureQueriesContext(connection) as ctx2:
        response2 = client.get("/api/v1/enrollments/upcoming/")
    assert response2.status_code == status.HTTP_200_OK
    query_count_10 = len(ctx2.captured_queries)

    assert query_count_5 == query_count_10, (
        f"N+1 detected: {query_count_5} queries for 5 enrollments, {query_count_10} for 10"
    )
