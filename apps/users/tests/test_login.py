import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import Profile

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def login_url():
    return "/api/v1/auth/login/"


def make_verified_user(email="user@example.com", role="seeker"):
    user = User.objects.create_user(
        username=email,
        email=email,
        password="StrongPass123!",
    )
    Profile.objects.create(user=user, role=role, is_email_verified=True)
    return user


@pytest.mark.django_db
def test_login_success(api_client, login_url):
    make_verified_user()
    response = api_client.post(
        login_url,
        {"email": "user@example.com", "password": "StrongPass123!"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data
    assert "refresh" in response.data
    assert response.data["user"]["role"] == "seeker"


@pytest.mark.django_db
def test_login_unverified_user(api_client, login_url):
    user = User.objects.create_user(
        username="unverified@example.com",
        email="unverified@example.com",
        password="StrongPass123!",
    )
    Profile.objects.create(user=user, role="seeker", is_email_verified=False)

    response = api_client.post(
        login_url,
        {"email": "unverified@example.com", "password": "StrongPass123!"},
        format="json",
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data["code"] == "email_not_verified"


@pytest.mark.django_db
def test_login_wrong_password(api_client, login_url):
    make_verified_user()
    response = api_client.post(
        login_url,
        {"email": "user@example.com", "password": "WrongPassword!"},
        format="json",
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.data["code"] == "invalid_credentials"


@pytest.mark.django_db
def test_login_case_insensitive_email(api_client, login_url):
    make_verified_user(email="CaseTest@example.com")
    response = api_client.post(
        login_url,
        {"email": "casetest@example.com", "password": "StrongPass123!"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_token_refresh(api_client, login_url):
    make_verified_user()
    login_resp = api_client.post(
        login_url,
        {"email": "user@example.com", "password": "StrongPass123!"},
        format="json",
    )
    refresh_token = login_resp.data["refresh"]

    response = api_client.post(
        "/api/v1/auth/refresh/",
        {"refresh": refresh_token},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data


@pytest.mark.django_db
def test_signup_throttle():
    """6th signup attempt from the same IP within an hour returns 429."""
    cache.clear()
    client = APIClient()
    client.defaults["REMOTE_ADDR"] = "10.0.0.1"

    for i in range(5):
        client.post(
            "/api/v1/auth/signup/",
            {"email": f"throttle{i}@example.com", "password": "StrongPass123!", "role": "seeker"},
            format="json",
        )

    # 6th attempt must be throttled
    response = client.post(
        "/api/v1/auth/signup/",
        {"email": "throttle6@example.com", "password": "StrongPass123!", "role": "seeker"},
        format="json",
    )
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.django_db
def test_login_throttle():
    """11th login attempt from the same IP within an hour returns 429."""
    cache.clear()
    make_verified_user(email="throttlelogin@example.com")
    client = APIClient()
    client.defaults["REMOTE_ADDR"] = "10.0.0.2"

    for _ in range(10):
        client.post(
            "/api/v1/auth/login/",
            {"email": "throttlelogin@example.com", "password": "WrongPassword!"},
            format="json",
        )

    # 11th attempt must be throttled
    response = client.post(
        "/api/v1/auth/login/",
        {"email": "throttlelogin@example.com", "password": "WrongPassword!"},
        format="json",
    )
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
