from django.conf import settings
from django.db import models


class EnrollmentStatus(models.TextChoices):
    ENROLLED = "enrolled", "Enrolled"
    CANCELED = "canceled", "Canceled"


class Enrollment(models.Model):
    event = models.ForeignKey(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    seeker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    status = models.CharField(
        max_length=20,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.ENROLLED,
    )
    followup_sent = models.BooleanField(default=False)
    reminder_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["event", "seeker"],
                condition=models.Q(status="enrolled"),
                name="unique_active_enrollment",
            )
        ]
        indexes = [
            models.Index(fields=["seeker", "status"]),
            models.Index(fields=["event", "status"]),
            models.Index(fields=["followup_sent", "created_at"]),
            models.Index(fields=["reminder_sent", "status"]),
        ]

    def __str__(self):
        return f"{self.seeker.email} -> {self.event.title} ({self.status})"
