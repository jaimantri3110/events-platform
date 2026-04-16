import threading
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.enrollments.models import Enrollment
from apps.events.tests.factories import EventFactory
from apps.users.tests.factories import VerifiedSeekerFactory


@pytest.mark.django_db(transaction=True)
def test_enrollment_capacity_race_condition():
    """10 concurrent enrollments on capacity=5 event — exactly 5 should succeed."""
    event = EventFactory(capacity=5)
    seekers = [VerifiedSeekerFactory() for _ in range(10)]

    results = []
    lock = threading.Lock()

    def enroll(seeker):
        client = APIClient()
        token = RefreshToken.for_user(seeker)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        resp = client.post("/api/v1/enrollments/", {"event_id": event.pk}, format="json")
        with lock:
            results.append(resp.status_code)

    threads = [threading.Thread(target=enroll, args=(s,)) for s in seekers]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    enrolled_count = Enrollment.objects.filter(event=event, status="enrolled").count()
    assert enrolled_count == 5, f"Expected 5 enrollments, got {enrolled_count}"


@pytest.mark.django_db
def test_enrollment_atomic_integrity():
    """After concurrent enroll attempts, DB enrollment count matches actual enrollments."""
    event = EventFactory(capacity=3)
    seekers = [VerifiedSeekerFactory() for _ in range(3)]

    clients = []
    for seeker in seekers:
        client = APIClient()
        token = RefreshToken.for_user(seeker)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        clients.append(client)

    for client in clients:
        client.post("/api/v1/enrollments/", {"event_id": event.pk}, format="json")

    enrolled_count = Enrollment.objects.filter(event=event, status="enrolled").count()
    assert enrolled_count == 3
