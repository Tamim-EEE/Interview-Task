from celery import shared_task
from django.utils import timezone
from django.db import transaction
from .models import Reservation, Product, AuditLog

# Task to clean up expired reservations
@shared_task
def cleanup_expired_reservations():
    expired_reservations = Reservation.objects.filter(expires_at__lt=timezone.now())
    for reservation in expired_reservations:
        with transaction.atomic():
            product = Product.objects.select_for_update().get(id=reservation.product.id)
            old_available = product.available_stock
            old_reserved = product.reserved_stock
            product.available_stock += reservation.quantity
            product.reserved_stock -= reservation.quantity
            product.save()

            # Audit log for stock adjustment
            AuditLog.objects.create(
                actor="System",
                action="stock_adjusted",
                object_type="Product",
                object_id=product.id,
                old_value={"available_stock": old_available, "reserved_stock": old_reserved},
                new_value={"available_stock": product.available_stock, "reserved_stock": product.reserved_stock},
            )

            # Audit log for expired reservation
            AuditLog.objects.create(
                actor="System",  # System action
                action="reservation_expired",
                object_type="Reservation",
                object_id=reservation.id,
                old_value={"status": "active"},
                new_value={"status": "expired"},
            )

            reservation.delete()
