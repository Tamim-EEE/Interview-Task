from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# Models for Inventory Management System


# Product Model
class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_stock = models.PositiveIntegerField()
    available_stock = models.PositiveIntegerField()
    reserved_stock = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
        ]

    def save(self, *args, **kwargs):
        # Handle None values during creation
        if self.available_stock is None:
            self.available_stock = self.total_stock - self.reserved_stock

        # Ensure non-negative values
        self.available_stock = max(0, self.available_stock)
        self.reserved_stock = max(0, self.reserved_stock)

        if self.available_stock + self.reserved_stock != self.total_stock:
            raise ValueError(
                "Invariant violated: available_stock + reserved_stock must equal total_stock"
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# Reservation Model
class Reservation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["expires_at"]),
        ]

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Reservation {self.id} for {self.product.name}"


# Order Model
class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    ]

    TRANSITIONS = {
        "pending": ["confirmed", "cancelled"],
        "confirmed": ["processing", "cancelled"],
        "processing": ["shipped"],
        "shipped": ["delivered"],
        "delivered": [],
        "cancelled": [],
    }

    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["total"]),
            models.Index(fields=["created_at", "status"]),
        ]

    def can_transition_to(self, new_status):
        return new_status in self.TRANSITIONS.get(self.status, [])

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.product.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.id}"


# AuditLog Model
class AuditLog(models.Model):
    actor = models.CharField(
        max_length=255, default="System"
    )  # Email for users, "System" for automated operations
    action = models.CharField(max_length=255)
    object_type = models.CharField(max_length=255)
    object_id = models.PositiveIntegerField()
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["timestamp"]),
            models.Index(fields=["action"]),
            models.Index(fields=["object_type"]),
        ]

    def __str__(self):
        return f"Audit {self.action} on {self.object_type} {self.object_id}"
