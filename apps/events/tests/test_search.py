from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.tests.factories import VerifiedFacilitatorFactory, VerifiedSeekerFactory

from .factories import EventFactory


def auth_seeker_client():
    seeker = VerifiedSeekerFactory()
    client = APIClient()
    token = RefreshToken.for_user(seeker)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


@pytest.mark.django_db
def test_search_by_location():
    facilitator = VerifiedFacilitatorFactory()
    EventFactory(created_by=facilitator, location="Mumbai")
    EventFactory(created_by=facilitator, location="Delhi")
    client = auth_seeker_client()

    response = client.get("/api/v1/events/", {"location": "mumbai"})
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["location"] == "Mumbai"


@pytest.mark.django_db
def test_search_by_language():
    facilitator = VerifiedFacilitatorFactory()
    EventFactory(created_by=facilitator, language="English")
    EventFactory(created_by=facilitator, language="Hindi")
    client = auth_seeker_client()

    response = client.get("/api/v1/events/", {"language": "ENGLISH"})
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1


@pytest.mark.django_db
def test_search_by_date_range():
    facilitator = VerifiedFacilitatorFactory()
    now = timezone.now()
    EventFactory(created_by=facilitator, starts_at=now + timedelta(days=2), ends_at=now + timedelta(days=2, hours=2))
    EventFactory(created_by=facilitator, starts_at=now + timedelta(days=10), ends_at=now + timedelta(days=10, hours=2))
    client = auth_seeker_client()

    response = client.get(
        "/api/v1/events/",
        {"starts_after": (now + timedelta(days=1)).isoformat(), "starts_before": (now + timedelta(days=5)).isoformat()},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1


@pytest.mark.django_db
def test_search_by_text_query():
    facilitator = VerifiedFacilitatorFactory()
    EventFactory(created_by=facilitator, title="Yoga Morning Session", description="Relaxing yoga.")
    EventFactory(created_by=facilitator, title="Python Workshop", description="Coding in yoga style.")
    EventFactory(created_by=facilitator, title="Art Expo", description="Art and craft.")
    client = auth_seeker_client()

    response = client.get("/api/v1/events/", {"q": "yoga"})
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2


@pytest.mark.django_db
def test_list_events_no_n_plus_one():
    """Query count must stay constant regardless of event count."""
    from django.test.utils import CaptureQueriesContext
    from django.db import connection

    facilitator = VerifiedFacilitatorFactory()
    seeker = VerifiedSeekerFactory()
    for _ in range(10):
        EventFactory(created_by=facilitator)

    client = APIClient()
    token = RefreshToken.for_user(seeker)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

    with CaptureQueriesContext(connection) as ctx:
        response = client.get("/api/v1/events/")
    assert response.status_code == status.HTTP_200_OK
    query_count_10 = len(ctx.captured_queries)

    # Add 10 more events
    for _ in range(10):
        EventFactory(created_by=facilitator)

    with CaptureQueriesContext(connection) as ctx2:
        response2 = client.get("/api/v1/events/")
    assert response2.status_code == status.HTTP_200_OK
    query_count_20 = len(ctx2.captured_queries)

    # Query count should be the same (constant) — no N+1
    assert query_count_10 == query_count_20, (
        f"N+1 detected: {query_count_10} queries for 10 events, {query_count_20} for 20 events"
    )
