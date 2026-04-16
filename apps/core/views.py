import logging

from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from redis import Redis

logger = logging.getLogger(__name__)


def health_check(request):
    health = {"status": "healthy", "checks": {}}

    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health["checks"]["database"] = "ok"
    except Exception as e:
        health["status"] = "unhealthy"
        health["checks"]["database"] = str(e)
        logger.error("health_check_db_failed", extra={"error": str(e)})

    # Redis check
    try:
        redis_url = settings.CELERY_BROKER_URL
        r = Redis.from_url(redis_url)
        r.ping()
        health["checks"]["redis"] = "ok"
    except Exception as e:
        health["status"] = "unhealthy"
        health["checks"]["redis"] = str(e)
        logger.error("health_check_redis_failed", extra={"error": str(e)})

    status_code = 200 if health["status"] == "healthy" else 503
    return JsonResponse(health, status=status_code)
