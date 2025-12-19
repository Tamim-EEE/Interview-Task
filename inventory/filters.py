import django_filters
from .models import Order

# FilterSet for Order model to enable filtering based on various fields
class OrderFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(
        field_name="created_at__date", lookup_expr="gte"
    )
    end_date = django_filters.DateFilter(
        field_name="created_at__date", lookup_expr="lte"
    )
    status = django_filters.CharFilter(field_name="status", lookup_expr="iexact")
    min_total = django_filters.NumberFilter(field_name="total", lookup_expr="gte")
    max_total = django_filters.NumberFilter(field_name="total", lookup_expr="lte")
    sort = django_filters.OrderingFilter(
        fields=(
            ("created_at", "created_at"),
            ("-created_at", "newest"),
            ("-total", "highest_value"),
        ),
        field_labels={
            "created_at": "Oldest first",
            "-created_at": "Newest first",
            "-total": "Highest value first",
        },
    )

    class Meta:
        model = Order
        fields = [
            "start_date",
            "end_date",
            "status",
            "min_total",
            "max_total",
            "sort",
        ]
