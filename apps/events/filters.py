import django_filters

from .models import Event


class EventFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method="filter_q", label="Search")
    location = django_filters.CharFilter(field_name="location", lookup_expr="iexact")
    language = django_filters.CharFilter(field_name="language", lookup_expr="iexact")
    starts_after = django_filters.IsoDateTimeFilter(field_name="starts_at", lookup_expr="gte")
    starts_before = django_filters.IsoDateTimeFilter(field_name="starts_at", lookup_expr="lte")

    class Meta:
        model = Event
        fields = ["location", "language"]

    def filter_q(self, queryset, name, value):
        from django.db.models import Q

        return queryset.filter(Q(title__icontains=value) | Q(description__icontains=value))
