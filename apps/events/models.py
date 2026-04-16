from django.conf import settings
from django.db import models
from django.db.models import Case, Count, F, IntegerField, Q, Value, When
from django.db.models.functions import Greatest


class EventQuerySet(models.QuerySet):
    def with_counts(self):
        """Annotate enrolled_count and available_seats — avoids N+1 queries."""
        return self.annotate(
            enrolled_count=Count(
                "enrollments",
                filter=Q(enrollments__status="enrolled"),
            ),
            available_seats=Case(
                When(capacity__isnull=True, then=Value(None)),
                default=Greatest(
                    F("capacity")
                    - Count(
                        "enrollments",
                        filter=Q(enrollments__status="enrolled"),
                    ),
                    Value(0),
                ),
                output_field=IntegerField(),
            ),
        )

    def upcoming(self):
        from django.utils import timezone

        return self.filter(starts_at__gt=timezone.now())


class EventManager(models.Manager):
    def get_queryset(self):
        return EventQuerySet(self.model, using=self._db)

    def with_counts(self):
        return self.get_queryset().with_counts()


class Event(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    language = models.CharField(max_length=50, db_index=True)
    location = models.CharField(max_length=255, db_index=True)
    starts_at = models.DateTimeField(db_index=True)
    ends_at = models.DateTimeField()
    capacity = models.PositiveIntegerField(null=True, blank=True)  # null = unlimited
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = EventManager()

    class Meta:
        ordering = ["starts_at"]
        indexes = [
            models.Index(fields=["starts_at"]),
            models.Index(fields=["language"]),
            models.Index(fields=["location"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["starts_at", "language", "location"]),
        ]

    def __str__(self):
        return self.title
