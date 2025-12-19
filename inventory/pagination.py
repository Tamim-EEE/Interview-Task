from rest_framework.pagination import CursorPagination

# Custom cursor pagination for Order model
class OrderCursorPagination(CursorPagination):
    page_size = 10
    ordering = ["-created_at", "-id"]

    def paginate_queryset(self, queryset, request, view=None):
        # Set ordering based on the queryset's current order_by to allow dynamic sorting
        if queryset.query.order_by:
            self.ordering = [str(f) for f in queryset.query.order_by]
        else:
            self.ordering = ["created_at", "id"]  # Default ordering

        return super().paginate_queryset(queryset, request, view)
