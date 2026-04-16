#!/bin/bash
set -e
exec 2>&1

# Python is unbuffered (PYTHONUNBUFFERED=1), so these lines will always appear.
python -c "
import os, sys
print('[boot] PORT            :', os.environ.get('PORT', '8000 (default)'))
print('[boot] SETTINGS MODULE :', os.environ.get('DJANGO_SETTINGS_MODULE', 'NOT SET'))
print('[boot] DATABASE_URL    :', 'SET' if os.environ.get('DATABASE_URL') else 'NOT SET')
print('[boot] REDIS_URL       :', 'SET' if os.environ.get('REDIS_URL') else 'NOT SET')
"

echo "--- running migrations ---"
python manage.py migrate --noinput

echo "--- testing wsgi import ---"
python -c "from config.wsgi import application; print('[boot] WSGI import OK')"

PORT=${PORT:-8000}
echo "--- starting gunicorn on 0.0.0.0:$PORT ---"
exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:$PORT \
  --workers 1 \
  --timeout 120 \
  --log-level debug \
  --access-logfile - \
  --error-logfile -
