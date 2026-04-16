from django.urls import path

from .views import EventDetailView, EventListCreateView, MyEventsView

urlpatterns = [
    path("", EventListCreateView.as_view(), name="event-list-create"),
    path("my-events/", MyEventsView.as_view(), name="event-my-events"),
    path("<int:pk>/", EventDetailView.as_view(), name="event-detail"),
]
