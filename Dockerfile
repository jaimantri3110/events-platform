FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Production settings are the default for the built image.
# Override with DJANGO_SETTINGS_MODULE=config.settings.dev for local docker-compose.
ENV DJANGO_SETTINGS_MODULE=config.settings.prod

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/prod.txt

COPY . .

# Collect static files at build time.
# A dummy SECRET_KEY is sufficient — collectstatic never touches the DB or crypto.
RUN SECRET_KEY=build-time-placeholder python manage.py collectstatic --noinput

EXPOSE 8000

# Use shell form so $PORT (injected by Railway) is expanded at runtime.
# Falls back to 8000 for local docker-compose runs.
CMD python manage.py migrate && \
    gunicorn config.wsgi:application \
      --bind 0.0.0.0:${PORT:-8000} \
      --workers 3 \
      --timeout 120 \
      --access-logfile -
