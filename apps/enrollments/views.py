import logging

from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.events.models import Event
from apps.users.permissions import IsEnrollmentOwner, IsSeeker

from .models import Enrollment, EnrollmentStatus
from .serializers import EnrollmentListSerializer, EnrollmentSerializer

logger = logging.getLogger(__name__)


class EnrollView(APIView):
    """POST /api/v1/enrollments/ — Idempotent enrollment (Seeker only)."""

    permission_classes = [IsAuthenticated, IsSeeker]

    @extend_schema(
        tags=["Enrollments"],
        summary="Enroll in an event (idempotent — returns 200 if already enrolled, 201 if new)",
    )
    def post(self, request):
        event_id = request.data.get("event_id")
        if not event_id:
            return Response(
                {"detail": "event_id is required.", "code": "event_id_required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()

        with transaction.atomic():
            try:
                event = Event.objects.select_for_update().get(id=event_id)
            except Event.DoesNotExist:
                return Response(
                    {"detail": "Event not found.", "code": "event_not_found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if event.ends_at <= now:
                return Response(
                    {"detail": "Event has already ended.", "code": "event_ended"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Idempotency: return existing active enrollment
            existing = Enrollment.objects.filter(
                event=event, seeker=request.user, status=EnrollmentStatus.ENROLLED
            ).first()
            if existing:
                return Response(EnrollmentSerializer(existing).data, status=status.HTTP_200_OK)

            # Capacity check
            if event.capacity is not None:
                enrolled_count = event.enrollments.filter(status="enrolled").count()
                if enrolled_count >= event.capacity:
                    return Response(
                        {"detail": "Event is full.", "code": "event_full"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            enrollment = Enrollment.objects.create(
                event=event,
                seeker=request.user,
                status=EnrollmentStatus.ENROLLED,
            )
            logger.info(
                "enrollment_created",
                extra={"user_id": request.user.id, "event_id": event.id},
            )
            return Response(EnrollmentSerializer(enrollment).data, status=status.HTTP_201_CREATED)


class CancelEnrollmentView(APIView):
    """PATCH /api/v1/enrollments/{id}/cancel/ — Cancel enrollment (owner only)."""

    permission_classes = [IsAuthenticated, IsSeeker, IsEnrollmentOwner]

    @extend_schema(tags=["Enrollments"], summary="Cancel an enrollment")
    def patch(self, request, pk):
        try:
            enrollment = Enrollment.objects.select_related("event").get(pk=pk)
        except Enrollment.DoesNotExist:
            return Response(
                {"detail": "Enrollment not found.", "code": "not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        self.check_object_permissions(request, enrollment)

        if enrollment.status == EnrollmentStatus.CANCELED:
            return Response(
                {"detail": "Enrollment is already canceled.", "code": "already_canceled"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            enrollment.status = EnrollmentStatus.CANCELED
            enrollment.save(update_fields=["status", "updated_at"])

        return Response(EnrollmentListSerializer(enrollment).data, status=status.HTTP_200_OK)


class UpcomingEnrollmentsView(APIView):
    """GET /api/v1/enrollments/upcoming/ — Seeker's future enrollments."""

    permission_classes = [IsAuthenticated, IsSeeker]

    @extend_schema(tags=["Enrollments"], summary="List upcoming enrollments")
    def get(self, request):
        now = timezone.now()
        qs = (
            Enrollment.objects.filter(
                seeker=request.user,
                status=EnrollmentStatus.ENROLLED,
                event__starts_at__gt=now,
            )
            .select_related("event", "event__created_by")
            .order_by("event__starts_at")
        )

        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(qs, request)
        serializer = EnrollmentListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class EnrollmentHistoryView(APIView):
    """GET /api/v1/enrollments/history/ — Seeker's past enrollments."""

    permission_classes = [IsAuthenticated, IsSeeker]

    @extend_schema(tags=["Enrollments"], summary="List past enrollment history")
    def get(self, request):
        now = timezone.now()
        qs = (
            Enrollment.objects.filter(
                seeker=request.user,
                event__ends_at__lte=now,
            )
            .select_related("event", "event__created_by")
            .order_by("-event__ends_at")
        )

        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(qs, request)
        serializer = EnrollmentListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
