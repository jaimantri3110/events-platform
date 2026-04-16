import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("events", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Enrollment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="enrollments",
                        to="events.event",
                    ),
                ),
                (
                    "seeker",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="enrollments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("enrolled", "Enrolled"), ("canceled", "Canceled")],
                        default="enrolled",
                        max_length=20,
                    ),
                ),
                ("followup_sent", models.BooleanField(default=False)),
                ("reminder_sent", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AddConstraint(
            model_name="enrollment",
            constraint=models.UniqueConstraint(
                condition=models.Q(status="enrolled"),
                fields=["event", "seeker"],
                name="unique_active_enrollment",
            ),
        ),
        migrations.AddIndex(
            model_name="enrollment",
            index=models.Index(fields=["seeker", "status"], name="enrollments_seeker_status_idx"),
        ),
        migrations.AddIndex(
            model_name="enrollment",
            index=models.Index(fields=["event", "status"], name="enrollments_event_status_idx"),
        ),
        migrations.AddIndex(
            model_name="enrollment",
            index=models.Index(fields=["followup_sent", "created_at"], name="enrollments_followup_idx"),
        ),
        migrations.AddIndex(
            model_name="enrollment",
            index=models.Index(fields=["reminder_sent", "status"], name="enrollments_reminder_idx"),
        ),
    ]
