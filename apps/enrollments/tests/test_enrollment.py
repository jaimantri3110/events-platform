from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.enrollments.models import Enrollment, EnrollmentStatus
from apps.events.tests.factories import EventFactory
from apps.users.tests.factories import VerifiedFacilitatorFactory, VerifiedSeekerFactory

from .factories import EnrollmentFactory

ENROLL_URL = "/api/v1/enrollments/"


def auth_client(user):
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


@pytest.mark.django_db
def test_enroll_success():
    seeker = VerifiedSeekerFactory()
    event = EventFactory()
    client = auth_client(seeker)

    response = client.post(ENROLL_URL, {"event_id": event.pk}, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert Enrollment.objects.filter(seeker=seeker, event=event, status="enrolled").exists()


@pytest.mark.django_db
def test_enroll_idempotent():
    seeker = VerifiedSeekerFactory()
    event = EventFactory()
    client = auth_client(seeker)

    r1 = client.post(ENROLL_URL, {"event_id": event.pk}, format="json")
    r2 = client.post(ENROLL_URL, {"event_id": event.pk}, format="json")

    assert r1.status_code == status.HTTP_201_CREATED
    assert r2.status_code == status.HTTP_200_OK
    assert r1.data["id"] == r2.data["id"]
    assert Enrollment.objects.filter(seeker=seeker, event=event, status="enrolled").count() == 1


@pytest.mark.django_db
def test_enroll_full_event():
    seeker1 = VerifiedSeekerFactory()
    seeker2 = VerifiedSeekerFactory()
    event = EventFactory(capacity=1)
    EnrollmentFactory(event=event, seeker=seeker1, status="enrolled")

    client = auth_client(seeker2)
    response = client.post(ENROLL_URL, {"event_id": event.pk}, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "event_full"


@pytest.mark.django_db
def test_enroll_ended_event():
    seeker = VerifiedSeekerFactory()
    now = timezone.now()
    event = EventFactory(
        starts_at=now - timedelta(hours=3),
        ends_at=now - timedelta(hours=1),
    )
    client = auth_client(seeker)
    response = client.post(ENROLL_URL, {"event_id": event.pk}, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "event_ended"


@pytest.mark.django_db
def test_cancel_enrollment():
    seeker = VerifiedSeekerFactory()
    enrollment = EnrollmentFactory(seeker=seeker, status="enrolled")
    client = auth_client(seeker)

    response = client.patch(f"/api/v1/enrollments/{enrollment.pk}/cancel/")
    assert response.status_code == status.HTTP_200_OK
    enrollment.refresh_from_db()
    assert enrollment.status == EnrollmentStatus.CANCELED


@pytest.mark.django_db
def test_reenroll_after_cancel():
    seeker = VerifiedSeekerFactory()
    event = EventFactory()
    EnrollmentFactory(seeker=seeker, event=event, status="canceled")
    client = auth_client(seeker)

    response = client.post(ENROLL_URL, {"event_id": event.pk}, format="json")
    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_facilitator_cannot_enroll():
    facilitator = VerifiedFacilitatorFactory()
    event = EventFactory(created_by=facilitator)
    client = auth_client(facilitator)

    response = client.post(ENROLL_URL, {"event_id": event.pk}, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN
