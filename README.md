# Inventory Reservation System

This Django project implements an inventory reservation system with order state machine, concurrency handling, and audit logging.

## Features

- Product inventory management with available and reserved stock
- Reservation system with 10-minute expiration
- Order state machine with validation
- Concurrency-safe operations using database locks
- Audit logging for key actions
- Performance optimized queries with indexes

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

3. Run tests:
   ```bash
   python manage.py test
   ```

## API Endpoints

- `POST /api/reservations/` - Create a reservation
- `GET /api/orders/` - List orders with filters (date range, status, min/max total) and sorting (newest, highest value)
- `POST /api/orders/{id}/change_status/` - Change order status

All responses include a `request_id` UUID for tracing.

## Cleanup Strategy

Expired reservations are cleaned up using Celery Beat every 1 minutes.

To run the Celery worker:
```bash
celery -A core worker -l info -P eventlet
```

To run the Celery Beat scheduler:
```bash
celery -A core beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

Alternatively, run the management command manually:
```bash
python manage.py cleanup_reservations
```

For production, ensure Redis is running and configure the broker URL in settings.py.

## Performance Optimization

### Indexes Added

- `created_at` on Order
- `status` on Order
- `total` on Order
- Composite index on `(created_at, status)` on Order

### Query Optimization

- Used `select_related` for foreign keys in Order queries
- Cursor pagination for large result sets

### EXPLAIN Notes

The indexes on `created_at`, `status`, and `total` allow efficient filtering and sorting:
- Date range filters use the `created_at` index
- Status filtering uses the `status` index
- Total range filters use the `total` index
- Sorting by newest uses `created_at DESC`
- Sorting by highest value uses `total DESC`

The composite index on `(created_at, status)` optimizes queries filtering by both date and status.

## Design Questions

1. **Crash recovery after reservation**: Use database transactions with rollback on failure. For partial failures, implement compensation logic to release reserved stock.

2. **Cleanup strategy + frequency**: Celery beat every 1 minutes for cleanup. Frequency based on reservation duration (10 minutes) - clean more often than expiration time.

3. **Multi-warehouse design**: Use a Warehouse model with many-to-many relationship to products. Stock levels per warehouse, reservation locks per warehouse.

4. **Caching strategy**: Cache product stock levels in Redis with TTL. Invalidate on stock changes. Use write-through for consistency.

## Concurrency Chaos Test

Run the chaos test script:

```bash
python scripts/chaos_test.py
```

Seeds 1 product with stock=5, fires 50 parallel attempts. Exactly 5 succeed, demonstrating concurrency safety.

## Audit Log

Logs include:
- Reservation creation/expiration
- Order creation
- Status changes
- Stock adjustments

## State Machine

Transition map:
```
pending → confirmed → processing → shipped → delivered
pending/confirmed → cancelled
```

No cancel after shipped, delivered immutable.

## Diagram

```
Reservation Created
    ↓
Stock Reserved
    ↓
Order Confirmed
    ↓
Stock Deducted
    ↓
Audit Logged
```