from rest_framework.permissions import BasePermission


class IsSeeker(BasePermission):
    message = "Only seekers can perform this action."
    code = "seeker_required"

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, "profile")
            and request.user.profile.role == "seeker"
        )


class IsFacilitator(BasePermission):
    message = "Only facilitators can perform this action."
    code = "facilitator_required"

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, "profile")
            and request.user.profile.role == "facilitator"
        )


class IsEventOwner(BasePermission):
    message = "You can only modify your own events."
    code = "not_event_owner"

    def has_object_permission(self, request, view, obj):
        return obj.created_by == request.user


class IsEnrollmentOwner(BasePermission):
    message = "You can only modify your own enrollments."
    code = "not_enrollment_owner"

    def has_object_permission(self, request, view, obj):
        return obj.seeker == request.user
