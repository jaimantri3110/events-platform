import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("events_platform")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "send-enrollment-followups": {
        "task": "apps.enrollments.tasks.send_enrollment_followup_email",
        "schedule": 300.0,  # every 5 minutes
    },
    "send-event-reminders": {
        "task": "apps.enrollments.tasks.send_event_reminder_email",
        "schedule": 300.0,
    },
}
