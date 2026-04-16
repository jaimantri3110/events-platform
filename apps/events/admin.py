from django.contrib import admin

from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ["title", "language", "location", "starts_at", "ends_at", "capacity", "created_by"]
    list_filter = ["language", "location"]
    search_fields = ["title", "description", "created_by__email"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "starts_at"
