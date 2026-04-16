#!/bin/bash
set -e

echo "==> PORT is: ${PORT:-8000}"
echo "==> DJANGO_SETTINGS_MODULE is: $DJANGO_SETTINGS_MODULE"
echo "==> DATABASE_URL is set: $([ -n "$DATABASE_URL" ] && echo YES || echo NO)"
echo "==> REDIS_URL is set: $([ -n "$REDIS_URL" ] && echo YES || echo NO)"

echo "==> Running migrations..."
python manage.py migrate --noinput

echo "==> Starting gunicorn on 0.0.0.0:${PORT:-8000}..."
exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:${PORT:-8000} \
  --workers 1 \
  --timeout 120 \
  --log-level debug \
  --access-logfile - \
  --error-logfile -
