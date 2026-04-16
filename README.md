# Events Platform API

Production-quality Django REST Framework backend for an **Events Platform** with two roles:
- **Seeker** — discovers and enrolls in events
- **Facilitator** — creates and manages events

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Framework | Django 4.2 + DRF 3.15 |
| Database | PostgreSQL 16 |
| Auth | `djangorestframework-simplejwt` (JWT) |
| API Docs | `drf-spectacular` (Swagger + ReDoc) |
| Task Queue | Celery + Redis (`django-celery-beat`) |
| Static Files | `whitenoise` (brotli compressed) |
| Email | Console (dev) / SMTP (prod) |
| Logging | `python-json-logger` (structured JSON) |
| Testing | `pytest-django` + `factory_boy` + `faker` |
| Container | Docker + Docker Compose |

---

## Architecture & Design Decisions

### Profile via OneToOneField
The spec requires Django's default `auth.User` model (no `AbstractUser`). User roles and verification state are stored in a `Profile` model linked via `OneToOneField`. This keeps the auth model unchanged while extending it cleanly.

### Hashed OTP Storage
OTP values are hashed with Django's PBKDF2 hasher (`make_password`) before storage. Plain-text OTPs are a security vulnerability — if the DB is breached, raw OTPs expose a verification bypass. `check_password()` verifies at submission time. The trade-off: ~100ms latency per verify call (acceptable for a security gate).

### DB-Level Email Uniqueness (Case-Insensitive)
`auth.User.email` has no unique constraint by default. A migration adds `CREATE UNIQUE INDEX ON auth_user (LOWER(email))` to enforce case-insensitive uniqueness at the database level. The view also pre-checks with `filter(email__iexact=email).exists()` for a clean error message, then catches `IntegrityError` as a safety net for race conditions.

### `transaction.atomic()` + `select_for_update()`
- **Signup**: User + Profile + EmailOTP creation is wrapped in `atomic()` — partial-save states are impossible.
- **OTP Verification**: `select_for_update()` on the OTP row prevents two concurrent requests from both passing verification.
- **Enrollment**: `select_for_update()` on the Event row prevents overselling capacity under concurrent requests.
- **Cancel**: Wrapped in `atomic()` to prevent partial updates.

### `annotate()` Instead of `@property` for Counts
`enrolled_count` and `available_seats` are computed via `Event.objects.with_counts()` using `annotate()` — a single SQL query regardless of result set size. `@property` methods would issue one query per event (N+1). A custom `EventManager` exposes `with_counts()` and is used in **all** views that return events.

### Idempotent Enrollment API
`POST /api/v1/enrollments/` returns **200** with the existing enrollment if the seeker is already enrolled, and **201** for new enrollments. This is safe for network retries and avoids confusing 400 errors for legitimate double-clicks.

### `select_for_update(skip_locked=True)` in Celery Tasks
When multiple Celery workers run simultaneously, they could each pick up the same enrollment for email sending. `skip_locked=True` skips rows locked by other workers, preventing duplicate emails. The trade-off: some rows may be delayed by one beat cycle (5 min) if locked.

### Scheduled Email Tasks
Two Celery beat tasks run every 5 minutes:
- **Follow-up**: sends to seekers who enrolled 55–65 minutes ago (`followup_sent=False`)
- **Reminder**: sends to seekers whose event starts 55–65 minutes from now (`reminder_sent=False`)

The ±5-minute window handles clock drift between beat scheduler and task execution. Both tasks use `select_for_update(skip_locked=True)` so parallel workers don't send duplicates.

### Structured JSON Logging
`python-json-logger` emits machine-readable JSON to stdout, enabling log aggregation (Datadog, Loki, Railway Logs) to parse fields like `user_id`, `event_id`, `status_code` without regex.

### Error Response Shape
All API errors follow `{"detail": "...", "code": "..."}` via a custom DRF exception handler (`config/exceptions.py`). Validation errors are flattened into a single readable string rather than nested field dicts.

### API Versioning
All endpoints are prefixed with `/api/v1/`. Breaking changes can be introduced under `/api/v2/` without disrupting existing clients.

### Database Indexes
- Individual indexes on `starts_at`, `language`, `location`, `created_by` — support single-field filters and sorts.
- Composite index on `(starts_at, language, location)` — supports the common multi-filter search pattern.
- `UniqueConstraint` with `condition=Q(status="enrolled")` on `(event, seeker)` — prevents duplicate active enrollments at the DB level while allowing re-enrollment after cancellation.
- `Enrollment` indexes on `(seeker, status)`, `(event, status)`, `(followup_sent, created_at)`, `(reminder_sent, status)` — targeted at the Celery task queries.

### Static Files (WhiteNoise)
`whitenoise.middleware.WhiteNoiseMiddleware` serves static files directly from gunicorn without a CDN or separate nginx. Files are brotli/gzip compressed and fingerprinted (`CompressedManifestStaticFilesStorage`) so browsers cache aggressively. `collectstatic` runs at Docker build time so the image is self-contained.

### Railway / PaaS SSL
Railway terminates TLS at its edge proxy and forwards plain HTTP internally. `SECURE_SSL_REDIRECT=True` is explicitly **off** in prod settings to avoid an infinite redirect loop. Instead, `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` lets Django know the original request was HTTPS so cookies and HSTS headers work correctly.

---

## API Documentation

| Interface | URL |
|-----------|-----|
| Swagger UI | `http://localhost:8000/api/v1/docs/` |
| ReDoc | `http://localhost:8000/api/v1/redoc/` |
| OpenAPI Schema (YAML) | `http://localhost:8000/api/v1/schema/` |
| Postman Collection | `postman/Events_Platform.postman_collection.json` |

---

## API Reference

### Auth (`/api/v1/auth/`)

| Method | Path | Auth | Throttle | Description |
|--------|------|------|----------|-------------|
| POST | `/signup/` | None | 5/hour | Register new user |
| POST | `/verify-email/` | None | 10/hour | Verify OTP |
| POST | `/login/` | None | 10/hour | Get JWT pair |
| POST | `/refresh/` | None | Default | Refresh access token |

### Events (`/api/v1/events/`)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/` | Seeker | Search/list events |
| POST | `/` | Facilitator | Create event |
| GET | `/{id}/` | Any | Get event detail |
| PUT/PATCH | `/{id}/` | Facilitator (owner) | Update event |
| DELETE | `/{id}/` | Facilitator (owner) | Delete event |
| GET | `/my-events/` | Facilitator | Own events with counts |

### Enrollments (`/api/v1/enrollments/`)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/` | Seeker | Enroll (idempotent) |
| PATCH | `/{id}/cancel/` | Seeker (owner) | Cancel enrollment |
| GET | `/upcoming/` | Seeker | Future enrollments |
| GET | `/history/` | Seeker | Past enrollments |

### Pagination
All list endpoints return:
```json
{
  "count": 42,
  "next": "http://…?page=3",
  "previous": "http://…?page=1",
  "results": [...]
}
```

### Error Shape
```json
{ "detail": "Human-readable message.", "code": "machine_readable_code" }
```

---

## Setup — Docker (Recommended)

**Prerequisites:** Docker, Docker Compose

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env if needed (defaults work for Docker)

# 2. Build and start all services (web + db + redis + celery-worker + celery-beat)
docker-compose up --build

# 3. Create superuser (optional)
docker-compose exec web python manage.py createsuperuser

# 4. Access the API
# Swagger UI:  http://localhost:8000/api/v1/docs/
# Health:      http://localhost:8000/api/v1/health/
# Admin:       http://localhost:8000/admin/
```

---

## Setup — Without Docker

```bash
# Python 3.11+, PostgreSQL 16, Redis 7 required

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements/dev.txt

export DJANGO_SETTINGS_MODULE=config.settings.dev
export DATABASE_URL=postgres://events_user:events_password@localhost:5432/events_db
export REDIS_URL=redis://localhost:6379/0
export SECRET_KEY=your-secret-key-here

python manage.py migrate
python manage.py runserver

# In separate terminals:
celery -A config worker -l info
celery -A config beat -l info
```

---

## Running Tests

```bash
# Inside Docker
docker-compose exec web pytest -v --cov=apps

# Locally
pytest -v --cov=apps --cov-report=term-missing
```

---

## Deploy on Railway

### Prerequisites
1. A [Railway](https://railway.app) account
2. Railway CLI installed: `npm install -g @railway/cli`

### Step 1 — Create the project

```bash
railway login
railway init          # creates a new Railway project
railway link          # links this directory
```

### Step 2 — Add plugins

In the Railway dashboard, attach:
- **PostgreSQL** plugin → Railway auto-sets `DATABASE_URL`
- **Redis** plugin → Railway auto-sets `REDIS_URL`

### Step 3 — Set environment variables

In Railway dashboard → **Variables**, add:

| Variable | Value |
|----------|-------|
| `DJANGO_SETTINGS_MODULE` | `config.settings.prod` |
| `SECRET_KEY` | *(generate a strong random key)* |
| `ALLOWED_HOSTS` | *(leave blank — `RAILWAY_PUBLIC_DOMAIN` is read automatically)* |
| `EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST` | `smtp.gmail.com` |
| `EMAIL_PORT` | `587` |
| `EMAIL_USE_TLS` | `True` |
| `EMAIL_HOST_USER` | your Gmail address |
| `EMAIL_HOST_PASSWORD` | your Gmail app password |
| `DEFAULT_FROM_EMAIL` | `noreply@yourdomain.com` |

> `DATABASE_URL`, `REDIS_URL`, and `PORT` are injected automatically by Railway — do **not** set them manually.

### Step 4 — Deploy the web service

```bash
railway up
```

Railway reads `railway.toml` → builds the Dockerfile → runs:
```
python manage.py migrate && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT ...
```

### Step 5 — Add Celery worker and beat (separate Railway services)

Railway runs one process per service. Create two additional services in the Railway dashboard and set their **Custom Start Command**:

**Worker service:**
```
celery -A config worker --loglevel=info --concurrency=2
```

**Beat service:**
```
celery -A config beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

Both services share the same environment variables and plugins as the web service.

> **Tip**: Use the Railway dashboard → *New Service* → *Empty Service* → paste the start command and point it at the same repo/branch.

### Step 6 — Verify

```
https://<your-app>.up.railway.app/api/v1/health/
```

Should return `{"status": "healthy", "checks": {"database": "ok", "redis": "ok"}}`.

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | insecure dev key |
| `DEBUG` | Debug mode | `False` |
| `DATABASE_URL` | PostgreSQL connection URL | local postgres |
| `REDIS_URL` | Redis URL (Railway plugin) | `redis://localhost:6379/0` |
| `CELERY_BROKER_URL` | Override broker URL | falls back to `REDIS_URL` |
| `CELERY_RESULT_BACKEND` | Override result backend | falls back to `REDIS_URL` |
| `EMAIL_BACKEND` | Django email backend | console (dev) |
| `EMAIL_HOST` | SMTP host | `smtp.gmail.com` |
| `EMAIL_PORT` | SMTP port | `587` |
| `EMAIL_USE_TLS` | TLS for SMTP | `True` |
| `EMAIL_HOST_USER` | SMTP username | — |
| `EMAIL_HOST_PASSWORD` | SMTP password | — |
| `DEFAULT_FROM_EMAIL` | Sender address | `noreply@eventsplatform.com` |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | `localhost,127.0.0.1` |
| `RAILWAY_PUBLIC_DOMAIN` | Auto-injected by Railway | — |
| `PORT` | HTTP port (auto-injected by Railway) | `8000` |
| `DJANGO_SETTINGS_MODULE` | Settings module | `config.settings.dev` |

---

## Tradeoffs

- **PBKDF2 on OTP**: ~100ms overhead per verify — acceptable security cost for a verification gate.
- **Console email in dev**: OTPs appear in server logs; switch `EMAIL_BACKEND` to SMTP for production.
- **WhiteNoise over nginx/CDN**: Simpler to deploy (no extra process or service). Trade-off: all static file I/O goes through gunicorn workers. For very high traffic, put a CDN in front.
- **Page-based pagination**: Simpler than cursor-based; cursor pagination should be considered for large datasets with frequent inserts.
- **`icontains` search**: Simpler than PostgreSQL full-text search; sufficient for current scale. For advanced search, add `django.contrib.postgres` and `SearchVector`.
- **Celery beat 55–65 min window**: Handles clock drift between beat schedule and actual task execution. The ±5-minute asymmetry prevents missed emails due to minor delays.
- **`skip_locked=True`**: Means some rows may be delayed one beat cycle (5 min) if locked by another worker — an acceptable trade-off over duplicate emails.
- **In-memory beat schedule**: Tasks are defined in `config/celery.py` (`app.conf.beat_schedule`). Using `DatabaseScheduler` (as recommended for production) lets you modify schedules via Django admin without redeploying.
