import pytest
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.tests.factories import VerifiedFacilitatorFactory, VerifiedSeekerFactory


@pytest.fixture(autouse=True)
def clear_cache():
    """Reset the throttle cache before every test.

    DRF throttle counters live in Django's cache, not in the DB transaction,
    so they are NOT rolled back between tests. Without this fixture, throttle
    counters accumulate across the test suite and cause spurious 429 responses
    in tests that expect 400/401.
    """
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def seeker_user(db):
    return VerifiedSeekerFactory()


@pytest.fixture
def facilitator_user(db):
    return VerifiedFacilitatorFactory()


@pytest.fixture
def auth_seeker_client(api_client, seeker_user):
    token = RefreshToken.for_user(seeker_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return api_client, seeker_user


@pytest.fixture
def auth_facilitator_client(api_client, facilitator_user):
    token = RefreshToken.for_user(facilitator_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return api_client, facilitator_user
