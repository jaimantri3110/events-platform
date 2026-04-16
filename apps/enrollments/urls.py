from django.urls import path

from .views import CancelEnrollmentView, EnrollmentHistoryView, EnrollView, UpcomingEnrollmentsView

urlpatterns = [
    path("", EnrollView.as_view(), name="enrollment-create"),
    path("upcoming/", UpcomingEnrollmentsView.as_view(), name="enrollment-upcoming"),
    path("history/", EnrollmentHistoryView.as_view(), name="enrollment-history"),
    path("<int:pk>/cancel/", CancelEnrollmentView.as_view(), name="enrollment-cancel"),
]
