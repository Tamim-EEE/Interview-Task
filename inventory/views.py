from django.shortcuts import render
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from .models import Product, Reservation, Order, AuditLog
from .serializers import (
    ProductSerializer,
    ReservationReadSerializer,
    ReservationWriteSerializer,
    OrderReadSerializer,
    OrderWriteSerializer,
    AuditLogSerializer,
)
from .pagination import OrderCursorPagination


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    pagination_class = OrderCursorPagination
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]


class ReservationViewSet(viewsets.ModelViewSet):
    queryset = Reservation.objects.select_related("user", "product")
    pagination_class = OrderCursorPagination
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return ReservationWriteSerializer
        return ReservationReadSerializer

    def perform_create(self, serializer):
        product_id = self.request.data.get("product")
        quantity = int(self.request.data.get("quantity"))
        user = self.request.user

        try:
            with transaction.atomic():
                product = Product.objects.select_for_update().get(id=product_id)
                if product.available_stock < quantity:
                    raise serializers.ValidationError({"error": "Insufficient stock"})
                
                old_available = product.available_stock
                old_reserved = product.reserved_stock
                product.available_stock -= quantity
                product.reserved_stock += quantity
                product.save()

                # Audit log for stock adjustment
                AuditLog.objects.create(
                    actor=user.email if user.is_authenticated else "System",
                    action="stock_adjusted",
                    object_type="Product",
                    object_id=product.id,
                    old_value={"available_stock": old_available, "reserved_stock": old_reserved},
                    new_value={"available_stock": product.available_stock, "reserved_stock": product.reserved_stock},
                )

                # Save the reservation
                instance = serializer.save(user=user, expires_at=timezone.now() + timedelta(minutes=10))

                # Audit log for reservation created
                AuditLog.objects.create(
                    actor=user.email if user.is_authenticated else "System",
                    action="reservation_created",
                    object_type="Reservation",
                    object_id=instance.id,
                    new_value={"product": product.name, "quantity": quantity},
                )

        except Product.DoesNotExist:
            raise serializers.ValidationError({"error": "Product not found"})

class OrderViewSet(viewsets.ModelViewSet):
    """
    OrderViewSet provides CRUD operations for Order objects.

    Filters available in the list view:
    - start_date: Filter orders created on or after this date (YYYY-MM-DD).
    - end_date: Filter orders created on or before this date (YYYY-MM-DD).
    - status: Filter by order status (case-insensitive).
    - min_total: Filter orders with total greater than or equal to this value.
    - max_total: Filter orders with total less than or equal to this value.
    - sort: Sort orders by 'created_at' (default), 'newest', 'highest_value'.
    """
    queryset = Order.objects.select_related("product", "user")
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = OrderCursorPagination

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return OrderWriteSerializer
        return OrderReadSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        status_filter = self.request.query_params.get("status")
        min_total = self.request.query_params.get("min_total")
        max_total = self.request.query_params.get("max_total")
        sort = self.request.query_params.get("sort", "created_at")

        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        if status_filter:
            queryset = queryset.filter(status__iexact=status_filter)
        if min_total:
            queryset = queryset.filter(total__gte=min_total)
        if max_total:
            queryset = queryset.filter(total__lte=max_total)
        if sort == "newest":
            queryset = queryset.order_by("-created_at")
        if sort == "highest_value":
            queryset = queryset.order_by("-total")


        return queryset

    def perform_create(self, serializer):
        instance = serializer.save(user=self.request.user)
        # Audit log for order creation
        AuditLog.objects.create(
            actor=self.request.user.email if self.request.user.is_authenticated else "System",
            action="order_created",
            object_type="Order",
            object_id=instance.id,
            new_value={"product": instance.product.name, "quantity": instance.quantity, "total": str(instance.total)},
        )

    def perform_update(self, serializer):
        instance = serializer.instance
        old_status = instance.status
        new_status = serializer.validated_data.get('status', old_status)
        
        if new_status != old_status:
            if not instance.can_transition_to(new_status):
                raise serializers.ValidationError({"status": f"Invalid status {old_status} → {new_status} transition"})
        
        serializer.save()
        
        if new_status != old_status:
            # Audit log for status change
            AuditLog.objects.create(
                actor=self.request.user.email if self.request.user.is_authenticated else "System",
                action="order_status_changed",
                object_type="Order",
                object_id=instance.id,
                old_value={"status": old_status},
                new_value={"status": new_status},
            )


class AuditLogViewSet(viewsets.ModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    pagination_class = OrderCursorPagination
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

