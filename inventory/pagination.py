from rest_framework.pagination import CursorPagination, Cursor


class OrderCursorPagination(CursorPagination):
    page_size = 10
    ordering = ["-created_at", "-id"]  # Ensure uniqueness for cursor pagination

    def paginate_queryset(self, queryset, request, view=None):
        # Set ordering based on the queryset's current order_by to allow dynamic sorting
        if queryset.query.order_by:
            self.ordering = [str(f) for f in queryset.query.order_by]
        else:
            self.ordering = ["created_at", "id"]  # Default fallback
        self.base_url = request.build_absolute_uri()
        self.cursor = self.decode_cursor(request)
        # Always paginate, even without cursor (start from beginning)
        if self.cursor is None:
            # Create a cursor for the first page (offset 0, not reverse)
            self.cursor = Cursor(offset=0, reverse=False, position=None)
        return super().paginate_queryset(queryset, request, view)
