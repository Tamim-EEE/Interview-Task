from rest_framework import serializers
from .models import Product, Reservation, Order, AuditLog


class SimpleProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ("id", "name")


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        available_stock = attrs.get(
            "available_stock", instance.available_stock if instance else None
        )
        reserved_stock = attrs.get(
            "reserved_stock", instance.reserved_stock if instance else None
        )
        total_stock = attrs.get(
            "total_stock", instance.total_stock if instance else None
        )

        if (
            available_stock is not None
            and reserved_stock is not None
            and total_stock is not None
        ):
            if available_stock + reserved_stock != total_stock:
                raise serializers.ValidationError(
                    "Invariant violated: available_stock + reserved_stock must equal total_stock"
                )

        return attrs


class ReservationReadSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    product = SimpleProductSerializer()

    class Meta:
        model = Reservation
        fields = "__all__"


class ReservationWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = "__all__"
        read_only_fields = ("id", "user", "expires_at", "created_at")


class OrderReadSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    product = SimpleProductSerializer()

    class Meta:
        model = Order
        fields = "__all__"


class OrderWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = "__all__"
        read_only_fields = ("id", "user", "created_at", "updated_at", "total")


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = "__all__"
