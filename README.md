# Inventory Reservation System

A Django REST API project that implements a production-grade inventory management system with real-time stock reservations, order state management, and comprehensive audit trails. Built to handle high concurrency scenarios while maintaining data integrity.

## 📋 Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Architecture Overview](#architecture-overview)
- [Performance Optimizations](#performance-optimizations)
- [Design Decisions](#design-decisions)
- [Concurrency Test Results](#concurrency-test-results)

---

## ✨ Features

### Core Functionality
- **Stock Management**: Real-time tracking of product inventory with automatic validation
- **Time-Limited Reservations**: 10-minute reservation system that automatically releases expired stock
- **Order State Machine**: Enforced business rules for order status transitions
- **Audit Logging**: Complete audit trail of all critical operations
- **Request Tracing**: UUID-based request tracking for debugging and monitoring

### Technical Highlights
- Database-level concurrency control using `select_for_update()`
- Atomic transactions to prevent race conditions
- Cursor-based pagination for efficient large dataset handling
- Comprehensive filtering and sorting capabilities
- Automated background tasks using Celery Beat

---

## 🛠 Tech Stack

- **Framework**: Django 5.2.9 + Django REST Framework 3.16.1
- **Authentication**: JWT (djangorestframework-simplejwt)
- **Task Queue**: Celery 5.6.0 with Celery Beat
- **Database**: SQLite (development) - PostgreSQL ready for production
- **Filtering**: django-filter 25.1
- **Testing**: Django TestCase + DRF APITestCase

---

## Project Structure

```
inventory-system/
│
├── core
│   ├── __init__.py
│   ├── asgi.py
│   ├── celery.py
│   ├── middleware.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── inventory
│   ├── management
│   │   ├── commands
│   │   │   ├── __init__.py
│   │   │   └── cleanup_reservations.py
│   │   └── __init__.py
│   ├── migrations
│   │   └── __init__.py
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── filters.py
│   ├── models.py
│   ├── pagination.py
│   ├── serializers.py
│   ├── tasks.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── scripts
│   └── chaos_test.py
├── .gitignore
├── Makefile
├── README.md
├── manage.py
└── requirements.txt
```

---

## 📦 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd inventory-system
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply database migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create a superuser** (optional, for admin access)
   ```bash
   python manage.py createsuperuser
   ```

---

## 🚀 Running the Application

### Start the Django development server
```bash
python manage.py runserver
```

### Start Celery worker (for background tasks)
```bash
celery -A core worker -l info -P eventlet
```

### Start Celery Beat scheduler (for periodic cleanup)
```bash
celery -A core beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Alternative: Use the Makefile
```bash
make migrate    # Run migrations
make test       # Run all tests cases
make chaos_test # Run chaos test
make clean      # Clean up Python cache files
```

---

## 📚 API Documentation

### Base URL
```
http://localhost:8000/api/
```

### Authentication
Most endpoints require JWT authentication. Obtain tokens via:
```bash
POST /api/token/
{
  "username": "your_username",
  "password": "your_password"
}
```

Include the token in subsequent requests:
```
Authorization: Bearer <access_token>
```

### Endpoints

#### Products
- `GET /api/products/` - List all products
- `POST /api/products/` - Create a new product
- `GET /api/products/{id}/` - Retrieve product details
- `PUT /api/products/{id}/` - Update product
- `DELETE /api/products/{id}/` - Delete product

#### Reservations
- `POST /api/reservations/` - Create a reservation (auto-expires in 10 minutes)
  ```json
  {
    "product": 1,
    "quantity": 3
  }
  ```
- `GET /api/reservations/` - List reservations
- `GET /api/reservations/{id}/` - Get reservation details

#### Orders
- `GET /api/orders/` - List orders with filtering and sorting
- `POST /api/orders/` - Create an order
- `PATCH /api/orders/{id}/` - Update order status
  ```json
  {
    "status": "confirmed"
  }
  ```

**Order Filtering Options:**
```
GET /api/orders/?start_date=2024-01-01&end_date=2024-12-31&status=pending&min_total=100&max_total=500&sort=newest
```

- `start_date`: Filter orders created on or after this date (YYYY-MM-DD)
- `end_date`: Filter orders created on or before this date (YYYY-MM-DD)
- `status`: Filter by order status (pending, confirmed, processing, shipped, delivered, cancelled)
- `min_total`: Minimum order total amount
- `max_total`: Maximum order total amount
- `sort`: Sorting options - `newest` (most recent first) or `highest_value` (highest total first)

#### Audit Logs
- `GET /api/audit-logs/` - View audit trail

### Response Format
All API responses include a unique `request_id` for tracing:
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "data": { ... }
}
```

---

## 🧪 Testing

### Run all tests
```bash
python manage.py test
```

### Test Coverage Includes:
- **Model Tests**: Product invariant validation, reservation expiry, order state transitions
- **API Tests**: Reservation creation, order status changes, validation errors
- **Concurrency Tests**: See the chaos test section below

**Test Count**: 12+ comprehensive tests covering all critical paths

---

## 🏗 Architecture Overview

### Data Integrity: The Stock Invariant

The system maintains a strict invariant at all times:
```
available_stock + reserved_stock = total_stock
```

This is enforced at multiple levels:
1. **Model level**: The `Product.save()` method validates before every save
2. **Database level**: Using atomic transactions
3. **API level**: Serializer validation

### Concurrency Control

**Problem**: Multiple users trying to reserve the same product simultaneously could lead to race conditions.

**Solution**: 
- Database row-level locking using `select_for_update()`
- Atomic transactions with `transaction.atomic()`
- Pessimistic locking strategy ensures only one transaction can modify stock at a time

**Example from code**:
```python
with transaction.atomic():
    product = Product.objects.select_for_update().get(id=product_id)
    if product.available_stock < quantity:
        raise ValidationError("Insufficient stock")
    product.available_stock -= quantity
    product.reserved_stock += quantity
    product.save()
```

### State Machine Implementation

Orders follow a strict state transition model defined in the `Order.TRANSITIONS` dictionary:

```python
TRANSITIONS = {
    "pending": ["confirmed", "cancelled"],
    "confirmed": ["processing", "cancelled"],
    "processing": ["shipped"],
    "shipped": ["delivered"],
    "delivered": [],
    "cancelled": [],
}
```

**Key Rules**:
- No if-else chains - transitions are dictionary-driven
- Invalid transitions are automatically rejected
- Once shipped, orders cannot be cancelled
- Delivered and cancelled states are terminal

### Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Reservation Flow                            │
└─────────────────────────────────────────────────────────────────┘

    User Request
         │
         ▼
    [Acquire Lock]
         │
         ▼
    Check Available Stock ──No──► Return Error
         │
        Yes
         │
         ▼
    Reserve Stock
    (available_stock ↓, reserved_stock ↑)
         │
         ▼
    Create Reservation
    (expires_at = now + 10min)
         │
         ▼
    Log Audit Entry
    (stock_adjusted + reservation_created)
         │
         ▼
    [Release Lock]
         │
         ▼
    Return Success


┌─────────────────────────────────────────────────────────────────┐
│                       Order Flow                                │
└─────────────────────────────────────────────────────────────────┘

    pending ──────► confirmed ──────► processing
       │                │                  │
       │                │                  │
       ▼                ▼                  ▼
   cancelled        cancelled          shipped
                                          │
                                          │
                                          ▼
                                      delivered


┌─────────────────────────────────────────────────────────────────┐
│                   Cleanup Process (Every 1 min)                 │
└─────────────────────────────────────────────────────────────────┘

    Celery Beat Trigger
         │
         ▼
    Find Expired Reservations
    (expires_at < now)
         │
         ▼
    [For Each Reservation]
         │
         ▼
    Acquire Product Lock
         │
         ▼
    Release Stock
    (reserved_stock ↓, available_stock ↑)
         │
         ▼
    Log Audit Entries
    (stock_adjusted + reservation_expired)
         │
         ▼
    Delete Reservation
         │
         ▼
    [Release Lock]
```

---

## ⚡ Performance Optimizations

### Database Indexes

I've added strategic indexes to improve query performance on the `Order` model:

```python
class Meta:
    indexes = [
        models.Index(fields=["created_at"]),      # For date filtering and sorting
        models.Index(fields=["status"]),          # For status filtering
        models.Index(fields=["total"]),           # For min/max total filtering
        models.Index(fields=["created_at", "status"]),  # Composite for combined filters
    ]
```

**Why these indexes?**

1. **`created_at` index**: 
   - Supports `start_date` and `end_date` range queries
   - Enables fast sorting by `newest` 
   - Most common filter in real-world scenarios

2. **`status` index**:
   - Status filtering is case-insensitive but still benefits from indexing
   - Frequently used to show orders by state (e.g., "all pending orders")

3. **`total` index**:
   - Supports `min_total` and `max_total` range queries
   - Enables efficient sorting by `highest_value`
   - Critical for financial reporting queries

4. **Composite `(created_at, status)` index**:
   - Optimizes the common pattern of "show me pending orders from last week"
   - Reduces index lookups when both filters are applied
   - PostgreSQL can use this for partial matches (just `created_at`)

### Query Optimization

**N+1 Query Problem Solved**:
```python
queryset = Order.objects.select_related("product", "user")
```

- `select_related` performs SQL JOINs to fetch related objects in a single query
- Without this, each order would trigger 2 additional queries (one for product, one for user)
- For 100 orders: 201 queries → 1 query

**Cursor Pagination**:
- Uses indexed fields for efficient pagination
- Avoids OFFSET performance degradation with large datasets
- Constant-time pagination regardless of page number

### Query Count Example

**Without optimization**:
```
GET /api/orders/ (100 orders)
- 1 query to fetch orders
- 100 queries to fetch products
- 100 queries to fetch users
Total: 201 queries
```

**With optimization**:
```
GET /api/orders/ (100 orders)
- 1 query with JOINs to fetch orders + products + users
Total: 1 query
```

**Performance gain**: 200x reduction in database roundtrips

---

## 🤔 Design Decisions

### 1. Crash Recovery After Reservation

**Challenge**: What happens if the system crashes after creating a reservation but before the user completes checkout?

**My Approach**:
- **Automatic expiration**: All reservations have a 10-minute TTL
- **Periodic cleanup**: Celery Beat runs every 1 minute to release expired stock
- **Atomic operations**: Stock adjustments use database transactions - either everything succeeds or everything rolls back
- **Audit trail**: Every stock movement is logged, making post-crash analysis possible

**Trade-offs**:
- ✅ Pro: Zero manual intervention needed for crash recovery
- ✅ Pro: Stock is never locked permanently
- ❌ Con: 10-minute window where stock might be reserved but not purchased
- ❌ Con: Celery adds infrastructure complexity

**Alternative considered**: Make reservations permanent until explicitly released. Rejected because it requires manual cleanup and can lead to stock being locked indefinitely if users abandon carts.

### 2. Cleanup Strategy + Frequency

**Why Celery Beat?**
- Runs independently of web requests
- Distributed execution capability (important for scaling)
- Built-in retry and error handling
- Persistent schedule in database

**Frequency choice (1 minute)**:
- Reservations expire in 10 minutes
- Cleaning every 1 minute means max 1-minute delay before stock becomes available again
- More frequent = faster stock release but higher DB load
- Less frequent = lower DB load but stock stays locked longer

**Math**: With 1000 reservations/hour, cleaning every minute processes ~17 expirations per run (manageable). Running every 10 seconds would process ~2 per run (overhead not worth it).

**Production considerations**:
- Monitor queue length to adjust frequency
- Consider time-based batching for off-peak optimization
- Add query timeout protection for large-scale cleanup

### 3. Multi-Warehouse Design Choices

**If I were to extend this system to support multiple warehouses:**

**Model Structure**:
```python
class Warehouse(models.Model):
    name = models.CharField(max_length=255)
    location = models.TextField()
    
class WarehouseStock(models.Model):
    warehouse = models.ForeignKey(Warehouse)
    product = models.ForeignKey(Product)
    available_stock = models.PositiveIntegerField()
    reserved_stock = models.PositiveIntegerField()
    
    class Meta:
        unique_together = ['warehouse', 'product']
```

**Key Design Choices**:

1. **Stock per warehouse**: Each warehouse maintains its own available/reserved counts
2. **Separate locking**: Lock at the warehouse-product level, not global product level
3. **Routing strategy**: API would need `warehouse_id` parameter or intelligent routing based on user location
4. **Aggregated views**: Product API would sum across warehouses for total availability

**Trade-offs**:
- ✅ Pro: True distributed inventory
- ✅ Pro: Better geographic distribution
- ✅ Pro: Independent warehouse operations
- ❌ Con: More complex reservation logic (which warehouse to reserve from?)
- ❌ Con: Cross-warehouse transfers need workflow
- ❌ Con: Reporting becomes more complex

**What I would avoid**: Treating warehouses as a simple tag on reservations. Stock needs to be physically tracked per location.

### 4. Caching Strategy

**What to cache**:
- ✅ Product catalog (names, prices, descriptions) - changes infrequently
- ✅ User permissions and authentication tokens - read-heavy
- ❌ Stock levels - changes too frequently, inconsistency risk

**Where to cache**:
- **Redis** for distributed caching across multiple app servers
- TTL-based expiration with manual invalidation hooks

**Caching Pattern**:
```python
# Cache-aside pattern
def get_product_catalog():
    cache_key = f"product:{product_id}:details"
    data = cache.get(cache_key)
    if data is None:
        data = Product.objects.get(id=product_id)
        cache.set(cache_key, data, timeout=3600)  # 1 hour TTL
    return data
```

**Invalidation Strategy**:
- **Write-through** for product updates:
  ```python
  def update_product(product_id, data):
      product = Product.objects.get(id=product_id)
      product.name = data['name']
      product.save()
      cache.delete(f"product:{product_id}:details")  # Invalidate immediately
  ```

**Why NOT cache stock levels**:
- Stock changes on every reservation and order
- Cache invalidation becomes a bottleneck
- Stale cache = overselling (critical bug)
- Database with proper indexes is fast enough for stock reads

**Trade-offs**:
- ✅ Pro: 90% cache hit rate for product catalog reads
- ✅ Pro: Reduced database load significantly
- ❌ Con: Redis adds operational complexity
- ❌ Con: Cache invalidation bugs can show stale data

---

## 🧨 Concurrency Test Results

### The Chaos Test

I built a specific test to prove the system handles race conditions correctly.

**Test Setup**:
```bash
python scripts/chaos_test.py
```

**Scenario**:
1. Seed database with 1 product, `total_stock=5`, `available_stock=5`
2. Spawn 50 parallel processes
3. Each process attempts to reserve 1 unit simultaneously
4. Verify exactly 5 succeed, 45 fail
5. Confirm `available_stock=0`, `reserved_stock=5`

**Actual Results**:
```
Succeeded: 5
Failed: 45
Final available_stock: 0
Final reserved_stock: 5
```

**What this proves**:
- ✅ No race conditions - exactly 5 purchases succeeded (not 6, not 4)
- ✅ Stock never went negative
- ✅ Invariant maintained: `0 + 5 = 5 (total_stock)`
- ✅ The system correctly handles 10x oversubscription

### How It Works Under the Hood

The key is `select_for_update()` with `transaction.atomic()`:

```python
# Process 1 starts transaction
with transaction.atomic():
    product = Product.objects.select_for_update().get(id=1)  # Acquires row lock
    # Processes 2-50 are now WAITING at this line
    
    if product.available_stock >= 1:  # Check: 5 >= 1 ✓
        product.available_stock -= 1   # Deduct: 5 → 4
        product.reserved_stock += 1    # Reserve: 0 → 1
        product.save()
    # Lock released, Process 2 can now proceed

# Process 2 now sees available_stock=4 (not 5)
# Process 6 will see available_stock=0 and fail
```

Without locking, all 50 processes would read `available_stock=5` simultaneously and try to decrement it, resulting in -45 available stock (data corruption).

---

## 📝 Audit Log Implementation

### Why No Signal Abuse?

I chose **explicit audit logging** over Django signals for several reasons:

**What I do**:
```python
# Explicit in the view layer
AuditLog.objects.create(
    actor=user.email,
    action="order_created",
    object_type="Order",
    object_id=instance.id,
    new_value={"product": instance.product.name, "quantity": instance.quantity}
)
```

**What I avoid**:
```python
# Signal approach (NOT used)
@receiver(post_save, sender=Order)
def log_order_created(sender, instance, created, **kwargs):
    if created:
        AuditLog.objects.create(...)  # Hidden side effect
```

**Why explicit is better here**:
1. **Clarity**: Reading the code makes it obvious that logging happens
2. **Control**: Some operations shouldn't be logged (e.g., test data, system migrations)
3. **Context**: Service layer has user context, signals don't
4. **Performance**: Can batch logs in the same transaction
5. **Testing**: Easier to mock/disable in tests

**When signals would be okay**:
- Cross-app events where coupling is undesirable
- Generic audit systems applied to many models
- Plugin architectures where handlers are registered dynamically

### What Gets Logged

Every critical operation creates audit entries:

1. **Reservation Created**: When a user reserves stock
2. **Reservation Expired**: When cleanup task releases stock
3. **Stock Adjusted**: Whenever available/reserved stock changes
4. **Order Created**: New order placement
5. **Order Status Changed**: State transitions

**Example Audit Log Entry**:
```json
{
  "id": 42,
  "actor": "user@example.com",
  "action": "order_status_changed",
  "object_type": "Order",
  "object_id": 15,
  "old_value": {"status": "pending"},
  "new_value": {"status": "confirmed"},
  "timestamp": "2024-12-19T10:30:00Z"
}
```

This provides a complete paper trail for debugging, compliance, and analytics.

---

## 🔐 Security Considerations

- JWT authentication required for write operations
- Read operations open (configure with `IsAuthenticatedOrReadOnly`)
- SQL injection prevented by Django ORM
- Request ID tracking for security incident investigation

---

## 🚢 Production Readiness

Before deploying to production, consider:

1. **Database**: Switch from SQLite to PostgreSQL
2. **Caching**: Add Redis for session storage and product catalog caching
3. **Message Broker**: Configure Redis/RabbitMQ for Celery
4. **Monitoring**: Add Sentry for error tracking, DataDog/Prometheus for metrics
5. **Logging**: Centralize logs with ELK stack or CloudWatch
6. **Environment Variables**: Use `.env` files for secrets (database, JWT keys)
7. **HTTPS**: Enforce SSL in production
8. **Rate Limiting**: Add throttling to prevent API abuse

---

## 📄 License

This project is created as a technical assessment and is free to use for educational purposes.
