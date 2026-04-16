from django.utils import timezone
from rest_framework import serializers

from .models import Event


class CreatedBySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()


class EventListSerializer(serializers.ModelSerializer):
    created_by = CreatedBySerializer(read_only=True)
    enrolled_count = serializers.IntegerField(read_only=True, default=0)
    available_seats = serializers.IntegerField(read_only=True, allow_null=True, default=None)

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "description",
            "language",
            "location",
            "starts_at",
            "ends_at",
            "capacity",
            "enrolled_count",
            "available_seats",
            "created_by",
            "created_at",
        ]


class EventCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "description",
            "language",
            "location",
            "starts_at",
            "ends_at",
            "capacity",
        ]
        read_only_fields = ["id"]

    def validate_starts_at(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("starts_at must be in the future.")
        return value

    def validate(self, attrs):
        # For partial updates (PATCH), fall back to the instance's existing values
        # when only one of starts_at/ends_at is provided.
        instance = getattr(self, "instance", None)
        starts_at = attrs.get("starts_at", instance.starts_at if instance else None)
        ends_at = attrs.get("ends_at", instance.ends_at if instance else None)

        if starts_at and ends_at and ends_at <= starts_at:
            raise serializers.ValidationError({"ends_at": "ends_at must be after starts_at."})
        capacity = attrs.get("capacity")
        if capacity is not None and capacity <= 0:
            raise serializers.ValidationError({"capacity": "capacity must be greater than 0."})
        return attrs


class EventDetailSerializer(EventListSerializer):
    """Full detail — same fields as list for now, extended here if needed."""
    pass
