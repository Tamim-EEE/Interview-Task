from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .models import Product, Reservation, Order, AuditLog
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

# Tests for Product Model
class ProductModelTest(TestCase):
    def test_invariant(self):
        product = Product(
            name="Test", total_stock=10, available_stock=5, reserved_stock=5
        )
        product.save()

        product.available_stock = 6
        with self.assertRaises(ValueError):
            product.save()

# Tests for Product Serializer
class ProductSerializerTest(TestCase):
    def test_valid_data(self):
        from .serializers import ProductSerializer

        data = {
            "name": "Test Product",
            "total_stock": 10,
            "available_stock": 7,
            "reserved_stock": 3,
        }
        serializer = ProductSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_invalid_invariant(self):
        from .serializers import ProductSerializer

        data = {
            "name": "Test Product",
            "total_stock": 10,
            "available_stock": 8,
            "reserved_stock": 4,  # 8 + 4 = 12 != 10
        }
        serializer = ProductSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)
        self.assertIn("Invariant violated", str(serializer.errors))

    def test_partial_update_invalid_invariant(self):
        from .serializers import ProductSerializer

        product = Product.objects.create(
            name="Test", total_stock=10, available_stock=7, reserved_stock=3
        )
        # Try to update available_stock to 5, which would make 5 + 3 = 8 != 10
        data = {"available_stock": 5}
        serializer = ProductSerializer(instance=product, data=data, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)
        self.assertIn("Invariant violated", str(serializer.errors))

# Tests for Reservation Model
class ReservationModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("testuser", "test@example.com", "password")
        self.product = Product.objects.create(
            name="Test", total_stock=10, available_stock=10, reserved_stock=0
        )

    def test_reservation_expiry(self):
        reservation = Reservation.objects.create(
            product=self.product,
            user=self.user,
            quantity=5,
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        self.assertTrue(reservation.is_expired())

# Tests for Order Model
class OrderModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("testuser", "test@example.com", "password")
        self.product = Product.objects.create(
            name="Test", total_stock=10, available_stock=10, reserved_stock=0
        )

    def test_valid_transitions(self):
        order = Order.objects.create(
            user=self.user, product=self.product, quantity=1, total=10.00
        )
        self.assertTrue(order.can_transition_to("confirmed"))
        self.assertFalse(order.can_transition_to("delivered"))

    def test_invalid_transitions(self):
        order = Order.objects.create(
            user=self.user,
            product=self.product,
            quantity=1,
            total=10.00,
            status="shipped",
        )
        self.assertFalse(order.can_transition_to("cancelled"))

# Tests for Reservation API
class ReservationAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("testuser", "test@example.com", "password")
        self.product = Product.objects.create(
            name="Test", total_stock=10, available_stock=10, reserved_stock=0
        )
        self.client.force_authenticate(user=self.user)

    def test_create_reservation_success(self):
        data = {"product": self.product.id, "quantity": 5}
        response = self.client.post(reverse("reservation-list"), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("request_id", response.data)
        self.product.refresh_from_db()
        self.assertEqual(self.product.available_stock, 5)
        self.assertEqual(self.product.reserved_stock, 5)

    def test_create_reservation_insufficient_stock(self):
        data = {"product": self.product.id, "quantity": 15}
        response = self.client.post(reverse("reservation-list"), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

# Tests for Order API
class OrderAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("testuser", "test@example.com", "password")
        self.product = Product.objects.create(
            name="Test", total_stock=10, available_stock=10, reserved_stock=0
        )
        self.order = Order.objects.create(
            user=self.user, product=self.product, quantity=1, total=10.00
        )
        self.client.force_authenticate(user=self.user)

    def test_change_status_valid(self):
        data = {"status": "confirmed"}
        response = self.client.patch(
            reverse("order-detail", args=[self.order.id]), data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "confirmed")

    def test_change_status_invalid(self):
        data = {"status": "delivered"}
        response = self.client.patch(
            reverse("order-detail", args=[self.order.id]), data
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

# Tests for AuditLog Model
class AuditLogTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("testuser", "test@example.com", "password")

    def test_audit_log_creation(self):
        log = AuditLog.objects.create(
            actor="System",
            action="test_action",
            object_type="Test",
            object_id=1,
            old_value={"old": "value"},
            new_value={"new": "value"},
        )
        self.assertEqual(AuditLog.objects.count(), 1)
