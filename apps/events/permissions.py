# Event-specific RBAC permissions are defined in apps.users.permissions:
#   - IsFacilitator  — only facilitators can create/update/delete events
#   - IsEventOwner   — only the event creator can modify their own event
#
# Re-exported here so event views can import from a single local module.
from apps.users.permissions import IsFacilitator, IsEventOwner  # noqa: F401
