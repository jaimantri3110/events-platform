from rest_framework import serializers

from apps.events.serializers import EventListSerializer

from .models import Enrollment


class EnrollmentSerializer(serializers.ModelSerializer):
    event = EventListSerializer(read_only=True)
    event_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Enrollment
        fields = ["id", "event", "event_id", "status", "created_at", "updated_at"]
        read_only_fields = ["id", "status", "created_at", "updated_at"]


class EnrollmentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""

    event = EventListSerializer(read_only=True)

    class Meta:
        model = Enrollment
        fields = ["id", "event", "status", "created_at", "updated_at"]
