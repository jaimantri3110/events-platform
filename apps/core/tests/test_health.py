from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_check_healthy():
    client = APIClient()
    with patch("apps.core.views.Redis") as mock_redis_cls:
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis_cls.from_url.return_value = mock_redis
        response = client.get("/api/v1/health/")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert data["checks"]["database"] == "ok"
    assert data["checks"]["redis"] == "ok"


@pytest.mark.django_db
def test_health_check_db_failure():
    client = APIClient()
    with patch("django.db.connection.cursor") as mock_cursor:
        mock_cursor.side_effect = Exception("DB connection failed")
        with patch("apps.core.views.Redis") as mock_redis_cls:
            mock_redis = MagicMock()
            mock_redis.ping.return_value = True
            mock_redis_cls.from_url.return_value = mock_redis
            response = client.get("/api/v1/health/")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["checks"]["database"] != "ok"
