from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from inventory.models import Reservation, Product, AuditLog

# Management command to clean up expired reservations
class Command(BaseCommand):
    help = "Cleanup expired reservations"

    def handle(self, *args, **options):
        expired_reservations = Reservation.objects.filter(expires_at__lt=timezone.now())
        count = 0
        for reservation in expired_reservations:
            with transaction.atomic():
                product = Product.objects.select_for_update().get(
                    id=reservation.product.id
                )
                # Release reserved stock back to available
                released_quantity = min(reservation.quantity, product.reserved_stock)
                old_available = product.available_stock
                old_reserved = product.reserved_stock
                product.available_stock += released_quantity
                product.reserved_stock -= released_quantity
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
                    actor="System",
                    action="reservation_expired",
                    object_type="Reservation",
                    object_id=reservation.id,
                    old_value={"status": "active"},
                    new_value={"status": "expired"},
                )

                reservation.delete()
                count += 1
        self.stdout.write(f"Cleaned up {count} expired reservations")
