import os
import sys
import django
import multiprocessing


# Chaos test script to simulate concurrent purchase attempts
def setup_django():
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    os.chdir(os.path.dirname(os.path.dirname(__file__)))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    django.setup()


# Function to attempt a purchase
def attempt_purchase(product_id, user_id):
    setup_django()
    from django.contrib.auth.models import User
    from django.db import transaction
    from django.utils import timezone
    from datetime import timedelta
    from inventory.models import Product, Reservation

    try:
        with transaction.atomic():
            prod = Product.objects.select_for_update().get(id=product_id)
            if prod.available_stock >= 1:
                prod.available_stock -= 1
                prod.reserved_stock += 1
                prod.save()
                user = User.objects.get(id=user_id)
                Reservation.objects.create(
                    product=prod,
                    user=user,
                    quantity=1,
                    expires_at=timezone.now() + timedelta(minutes=10),
                )
                return "success"
            else:
                return "fail"
    except Exception as e:
        return "fail"


if __name__ == "__main__":
    setup_django()

    from django.contrib.auth.models import User
    from inventory.models import Product

    # Seed DB
    user, created = User.objects.get_or_create(
        username="testuser", defaults={"email": "test@example.com"}
    )
    if created:
        user.set_password("password")
        user.save()

    product, created = Product.objects.get_or_create(
        name="Test Product",
        defaults={"total_stock": 5, "available_stock": 5, "reserved_stock": 0},
    )
    # Reset stock for test
    product.total_stock = 5
    product.available_stock = 5
    product.reserved_stock = 0
    product.save()

    with multiprocessing.Pool(processes=50) as pool:  # 50 parallel processes
        results = pool.starmap(
            attempt_purchase, [(product.id, user.id) for _ in range(50)]
        )

    success_count = results.count("success")
    fail_count = results.count("fail")

    product.refresh_from_db()

    print(f"Succeeded: {success_count}")
    print(f"Failed: {fail_count}")
    print(f"Final available_stock: {product.available_stock}")
    print("Deleting test data...")

    # Clean up test data
    product.delete()
    print("The test data has been deleted.")
