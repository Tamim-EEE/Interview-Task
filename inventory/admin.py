from django.contrib import admin
from django import forms
from .models import Product, Reservation, Order, AuditLog


# Custom form for Order to validate status transitions
class OrderAdminForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        if self.instance and self.instance.pk:
            old_status = self.instance.status
            if status != old_status:
                if not self.instance.can_transition_to(status):
                    raise forms.ValidationError(f"Invalid status transition from {old_status} → {status}")
        return cleaned_data

# Admin registrations

# Admin for Product model
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "total_stock", "available_stock", "reserved_stock")

# Admin for Reservation model
@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "user", "quantity", "expires_at", "created_at")
    readonly_fields = ("id", "created_at")

# Admin for Order model
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    form = OrderAdminForm
    list_display = (
        "id",
        "user",
        "product",
        "quantity",
        "total",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at")
    readonly_fields = ("id", "created_at", "updated_at", "total")

# Admin for AuditLog model
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "actor", "action", "object_type", "object_id", "timestamp")
    list_filter = ("action", "object_type", "timestamp")
    readonly_fields = ("id", "timestamp")
