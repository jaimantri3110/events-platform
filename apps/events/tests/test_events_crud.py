from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.events.models import Event
from apps.users.tests.factories import VerifiedFacilitatorFactory, VerifiedSeekerFactory

from .factories import EventFactory


def auth_client(user):
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


@pytest.mark.django_db
def test_create_event_as_facilitator():
    facilitator = VerifiedFacilitatorFactory()
    client = auth_client(facilitator)

    data = {
        "title": "Django Workshop",
        "description": "A hands-on workshop.",
        "language": "English",
        "location": "Mumbai",
        "starts_at": (timezone.now() + timedelta(days=5)).isoformat(),
        "ends_at": (timezone.now() + timedelta(days=5, hours=2)).isoformat(),
        "capacity": 50,
    }
    response = client.post("/api/v1/events/", data, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["title"] == "Django Workshop"
    # Timestamps should be timezone-aware (contain 'Z' or '+')
    assert "Z" in response.data["starts_at"] or "+" in response.data["starts_at"]


@pytest.mark.django_db
def test_create_event_as_seeker_forbidden():
    seeker = VerifiedSeekerFactory()
    client = auth_client(seeker)

    data = {
        "title": "Yoga",
        "description": "Yoga session.",
        "language": "English",
        "location": "Delhi",
        "starts_at": (timezone.now() + timedelta(days=3)).isoformat(),
        "ends_at": (timezone.now() + timedelta(days=3, hours=1)).isoformat(),
    }
    response = client.post("/api/v1/events/", data, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_create_event_past_start_time():
    facilitator = VerifiedFacilitatorFactory()
    client = auth_client(facilitator)

    data = {
        "title": "Past Event",
        "description": "This is in the past.",
        "language": "English",
        "location": "Mumbai",
        "starts_at": (timezone.now() - timedelta(days=1)).isoformat(),
        "ends_at": (timezone.now() + timedelta(hours=1)).isoformat(),
    }
    response = client.post("/api/v1/events/", data, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_create_event_end_before_start():
    facilitator = VerifiedFacilitatorFactory()
    client = auth_client(facilitator)

    data = {
        "title": "Bad Dates",
        "description": "ends_at before starts_at.",
        "language": "English",
        "location": "Mumbai",
        "starts_at": (timezone.now() + timedelta(days=5)).isoformat(),
        "ends_at": (timezone.now() + timedelta(days=4)).isoformat(),
    }
    response = client.post("/api/v1/events/", data, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_update_own_event():
    facilitator = VerifiedFacilitatorFactory()
    event = EventFactory(created_by=facilitator)
    client = auth_client(facilitator)

    response = client.patch(
        f"/api/v1/events/{event.pk}/",
        {"title": "Updated Title"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["title"] == "Updated Title"


@pytest.mark.django_db
def test_update_other_facilitator_event_forbidden():
    facilitator1 = VerifiedFacilitatorFactory()
    facilitator2 = VerifiedFacilitatorFactory()
    event = EventFactory(created_by=facilitator1)
    client = auth_client(facilitator2)

    response = client.patch(
        f"/api/v1/events/{event.pk}/",
        {"title": "Hacked"},
        format="json",
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_delete_own_event():
    facilitator = VerifiedFacilitatorFactory()
    event = EventFactory(created_by=facilitator)
    client = auth_client(facilitator)

    response = client.delete(f"/api/v1/events/{event.pk}/")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Event.objects.filter(pk=event.pk).exists()


@pytest.mark.django_db
def test_my_events_shows_counts():
    facilitator = VerifiedFacilitatorFactory()
    EventFactory(created_by=facilitator)
    EventFactory(created_by=facilitator)
    client = auth_client(facilitator)

    response = client.get("/api/v1/events/my-events/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2
    for event in response.data["results"]:
        assert "enrolled_count" in event
        assert "available_seats" in event


@pytest.mark.django_db
def test_pagination():
    facilitator = VerifiedFacilitatorFactory()
    seeker = VerifiedSeekerFactory()
    for _ in range(5):
        EventFactory(created_by=facilitator)
    client = auth_client(seeker)

    response = client.get("/api/v1/events/")
    assert response.status_code == status.HTTP_200_OK
    assert "count" in response.data
    assert "next" in response.data
    assert "previous" in response.data
    assert "results" in response.data


@pytest.mark.django_db
def test_event_timestamps_are_utc():
    facilitator = VerifiedFacilitatorFactory()
    seeker = VerifiedSeekerFactory()
    EventFactory(created_by=facilitator)
    client = auth_client(seeker)

    response = client.get("/api/v1/events/")
    assert response.status_code == status.HTTP_200_OK
    event = response.data["results"][0]
    # DRF serializes UTC datetimes with 'Z' suffix
    assert event["starts_at"].endswith("Z")
    assert event["ends_at"].endswith("Z")
