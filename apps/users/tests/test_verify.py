import threading

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import EmailOTP, Profile
from apps.users.services import create_and_send_otp, generate_otp

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def verify_url():
    return "/api/v1/auth/verify-email/"


def create_user_with_otp():
    """Helper: create an unverified user and raw OTP."""
    user = User.objects.create_user(
        username="verify@example.com",
        email="verify@example.com",
        password="StrongPass123!",
    )
    Profile.objects.create(user=user, role="seeker", is_email_verified=False)
    raw_otp = generate_otp()
    otp_record = EmailOTP(
        user=user,
        expires_at=timezone.now() + timezone.timedelta(minutes=5),
    )
    otp_record.set_otp(raw_otp)
    otp_record.save()
    return user, raw_otp


@pytest.mark.django_db
def test_verify_email_success(api_client, verify_url):
    user, raw_otp = create_user_with_otp()

    response = api_client.post(
        verify_url,
        {"email": user.email, "otp": raw_otp},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    user.profile.refresh_from_db()
    assert user.profile.is_email_verified is True

    otp = EmailOTP.objects.filter(user=user).first()
    assert otp.is_used is True


@pytest.mark.django_db
def test_verify_email_expired_otp(api_client, verify_url):
    user = User.objects.create_user(
        username="expired@example.com",
        email="expired@example.com",
        password="StrongPass123!",
    )
    Profile.objects.create(user=user, role="seeker", is_email_verified=False)
    raw_otp = generate_otp()
    otp_record = EmailOTP(
        user=user,
        expires_at=timezone.now() - timezone.timedelta(minutes=10),  # already expired
    )
    otp_record.set_otp(raw_otp)
    otp_record.save()

    response = api_client.post(
        verify_url,
        {"email": user.email, "otp": raw_otp},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_verify_email_max_attempts(api_client, verify_url):
    user, raw_otp = create_user_with_otp()

    # Exhaust all attempts with wrong OTP
    for _ in range(EmailOTP.MAX_ATTEMPTS):
        api_client.post(
            verify_url,
            {"email": user.email, "otp": "000000"},
            format="json",
        )

    # Now try with correct OTP — should be 429
    response = api_client.post(
        verify_url,
        {"email": user.email, "otp": raw_otp},
        format="json",
    )
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.django_db
def test_verify_email_wrong_otp(api_client, verify_url):
    user, raw_otp = create_user_with_otp()

    response = api_client.post(
        verify_url,
        {"email": user.email, "otp": "000000"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    otp = EmailOTP.objects.filter(user=user).first()
    assert otp.attempts == 1


@pytest.mark.django_db(transaction=True)
def test_verify_email_atomic():
    """Concurrent verification requests must not corrupt OTP state (only one succeeds)."""
    user, raw_otp = create_user_with_otp()

    results = []
    lock = threading.Lock()

    def attempt_verify():
        client = APIClient()
        resp = client.post(
            "/api/v1/auth/verify-email/",
            {"email": user.email, "otp": raw_otp},
            format="json",
        )
        with lock:
            results.append(resp.status_code)

    threads = [threading.Thread(target=attempt_verify) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Exactly one request should succeed (200), rest should fail (400)
    success_count = results.count(status.HTTP_200_OK)
    assert success_count == 1, f"Expected 1 success, got {success_count}. Results: {results}"

    # OTP must be marked used exactly once
    otp = EmailOTP.objects.filter(user=user).first()
    assert otp.is_used is True
