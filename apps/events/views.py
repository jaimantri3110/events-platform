import logging

from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsFacilitator, IsEventOwner, IsSeeker

from .models import Event
from .serializers import EventCreateSerializer, EventDetailSerializer, EventListSerializer

logger = logging.getLogger(__name__)


class EventListCreateView(APIView):
    """
    GET  — Seekers: search/list events
    POST — Facilitators: create event
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated(), IsSeeker()]
        return [IsAuthenticated(), IsFacilitator()]

    @extend_schema(
        tags=["Events"],
        summary="Search and list events (Seeker)",
        parameters=[
            OpenApiParameter("q", str, description="Text search on title/description"),
            OpenApiParameter("location", str, description="Case-insensitive exact match"),
            OpenApiParameter("language", str, description="Case-insensitive exact match"),
            OpenApiParameter("starts_after", str, description="ISO 8601 datetime filter"),
            OpenApiParameter("starts_before", str, description="ISO 8601 datetime filter"),
            OpenApiParameter("ordering", str, description="starts_at or -starts_at"),
            OpenApiParameter("page", int, description="Page number"),
        ],
    )
    def get(self, request):
        qs = Event.objects.with_counts().select_related("created_by")

        q = request.query_params.get("q")
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

        location = request.query_params.get("location")
        if location:
            qs = qs.filter(location__iexact=location)

        language = request.query_params.get("language")
        if language:
            qs = qs.filter(language__iexact=language)

        starts_after = request.query_params.get("starts_after")
        if starts_after:
            qs = qs.filter(starts_at__gte=starts_after)

        starts_before = request.query_params.get("starts_before")
        if starts_before:
            qs = qs.filter(starts_at__lte=starts_before)

        ordering = request.query_params.get("ordering", "starts_at")
        if ordering in ("starts_at", "-starts_at"):
            qs = qs.order_by(ordering)

        from rest_framework.pagination import PageNumberPagination

        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(qs, request)
        serializer = EventListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        tags=["Events"],
        summary="Create a new event (Facilitator)",
        request=EventCreateSerializer,
    )
    def post(self, request):
        serializer = EventCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = serializer.save(created_by=request.user)
        logger.info("event_created", extra={"user_id": request.user.id, "event_id": event.id})
        # Return with counts (both 0 for new event)
        event_qs = Event.objects.with_counts().get(pk=event.pk)
        return Response(EventListSerializer(event_qs).data, status=status.HTTP_201_CREATED)


class EventDetailView(APIView):
    """
    GET    — Any authenticated user
    PUT    — Facilitator (owner)
    PATCH  — Facilitator (owner)
    DELETE — Facilitator (owner)
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsFacilitator(), IsEventOwner()]

    def get_object(self, pk):
        try:
            return Event.objects.with_counts().select_related("created_by").get(pk=pk)
        except Event.DoesNotExist:
            return None

    @extend_schema(tags=["Events"], summary="Get event detail")
    def get(self, request, pk):
        event = self.get_object(pk)
        if event is None:
            return Response({"detail": "Event not found.", "code": "not_found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(EventDetailSerializer(event).data)

    @extend_schema(tags=["Events"], summary="Full update event (Facilitator owner)")
    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    @extend_schema(tags=["Events"], summary="Partial update event (Facilitator owner)")
    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def _update(self, request, pk, partial):
        try:
            event = Event.objects.get(pk=pk)
        except Event.DoesNotExist:
            return Response({"detail": "Event not found.", "code": "not_found"}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, event)
        serializer = EventCreateSerializer(event, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        event_qs = Event.objects.with_counts().get(pk=event.pk)
        return Response(EventListSerializer(event_qs).data)

    @extend_schema(tags=["Events"], summary="Delete event (Facilitator owner)")
    def delete(self, request, pk):
        try:
            event = Event.objects.get(pk=pk)
        except Event.DoesNotExist:
            return Response({"detail": "Event not found.", "code": "not_found"}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, event)
        event.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyEventsView(APIView):
    """Facilitator's own events with enrollment counts."""

    permission_classes = [IsAuthenticated, IsFacilitator]

    @extend_schema(tags=["Events"], summary="List facilitator's own events with counts")
    def get(self, request):
        qs = (
            Event.objects.with_counts()
            .select_related("created_by")
            .filter(created_by=request.user)
            .order_by("-starts_at")
        )

        from rest_framework.pagination import PageNumberPagination

        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(qs, request)
        serializer = EventListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
