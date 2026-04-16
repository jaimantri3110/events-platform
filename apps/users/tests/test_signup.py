import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import EmailOTP, Profile

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def signup_url():
    return "/api/v1/auth/signup/"


@pytest.mark.django_db
def test_signup_success(api_client, signup_url, mailoutbox):
    data = {"email": "test@example.com", "password": "StrongPass123!", "role": "seeker"}
    response = api_client.post(signup_url, data, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["email"] == "test@example.com"
    assert User.objects.filter(email="test@example.com").exists()
    assert Profile.objects.filter(user__email="test@example.com", role="seeker").exists()
    assert EmailOTP.objects.filter(user__email="test@example.com").exists()


@pytest.mark.django_db
def test_signup_rejects_username_field(api_client, signup_url):
    data = {
        "email": "test@example.com",
        "password": "StrongPass123!",
        "role": "seeker",
        "username": "hacker",
    }
    response = api_client.post(signup_url, data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "username_not_allowed"


@pytest.mark.django_db
def test_signup_duplicate_email(api_client, signup_url):
    data = {"email": "dup@example.com", "password": "StrongPass123!", "role": "seeker"}
    api_client.post(signup_url, data, format="json")
    response = api_client.post(signup_url, data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "email_exists"


@pytest.mark.django_db
def test_signup_duplicate_email_case_insensitive(api_client, signup_url):
    data = {"email": "test@email.com", "password": "StrongPass123!", "role": "seeker"}
    api_client.post(signup_url, data, format="json")

    data2 = {"email": "Test@Email.com", "password": "StrongPass123!", "role": "seeker"}
    response = api_client.post(signup_url, data2, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "email_exists"


@pytest.mark.django_db
def test_signup_weak_password(api_client, signup_url):
    data = {"email": "test@example.com", "password": "123", "role": "seeker"}
    response = api_client.post(signup_url, data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_otp_stored_hashed(api_client, signup_url):
    data = {"email": "otp@example.com", "password": "StrongPass123!", "role": "seeker"}
    api_client.post(signup_url, data, format="json")

    user = User.objects.get(email="otp@example.com")
    otp_record = EmailOTP.objects.filter(user=user).first()

    assert otp_record is not None
    # The stored value should NOT be a 6-digit number
    assert len(otp_record.otp) > 6
    # Should look like a Django password hash (starts with algorithm prefix)
    assert otp_record.otp.startswith("pbkdf2") or "$" in otp_record.otp
