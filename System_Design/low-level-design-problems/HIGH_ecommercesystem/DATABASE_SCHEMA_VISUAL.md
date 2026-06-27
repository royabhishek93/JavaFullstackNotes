# Database Schema Visual Guide - E-commerce System

## Complete ER Diagram

```
┌─────────────────────────────────┐
│            USERS                │
│─────────────────────────────────│
│ PK id (UUID)                    │
│    name                         │
│    email                        │
│    phone                        │
│    created_at                   │
└──────────────┬──────────────────┘
               │ owns
               ▼
┌─────────────────────────────────┐         ┌─────────────────────────────────┐
│            CARTS                │         │          PRODUCTS               │
│─────────────────────────────────│         │─────────────────────────────────│
│ PK id (UUID)                    │         │ PK id (UUID)                    │
│ FK user_id -> users.id          │         │    sku                         │
│    status                       │         │    name                        │
│    created_at                   │         │    brand                       │
└──────────────┬──────────────────┘         │    price                       │
               │ has many                   │    status                      │
               ▼                            │    created_at                  │
┌─────────────────────────────────┐         └──────────────┬──────────────────┘
│          CART_ITEMS             │                        │ tracked by
│─────────────────────────────────│                        ▼
│ PK id (UUID)                    │         ┌─────────────────────────────────┐
│ FK cart_id -> carts.id          │         │          INVENTORY              │
│ FK product_id -> products.id    │         │─────────────────────────────────│
│    quantity                     │         │ PK id (UUID)                    │
│    unit_price_snapshot          │         │ FK product_id -> products.id    │
│    created_at                   │         │    available_qty                │
└─────────────────────────────────┘         │    reserved_qty                 │
                                            │    sold_qty                     │
                                            │    version                      │
                                            │    updated_at                   │
                                            └──────────────┬──────────────────┘
                                                           │ reserved into
                                                           ▼
┌─────────────────────────────────┐         ┌─────────────────────────────────┐
│            ORDERS               │         │         ORDER_ITEMS             │
│─────────────────────────────────│         │─────────────────────────────────│
│ PK id (UUID)                    │         │ PK id (UUID)                    │
│ FK user_id -> users.id          │         │ FK order_id -> orders.id        │
│    total_amount                 │         │ FK product_id -> products.id    │
│    status                       │         │    quantity                     │
│    idempotency_key              │         │    unit_price_snapshot          │
│    created_at                   │         │    created_at                   │
└──────────────┬──────────────────┘         └──────────────┬──────────────────┘
               │ paid by                                   │ shipped via
               ▼                                           ▼
┌─────────────────────────────────┐         ┌─────────────────────────────────┐
│           PAYMENTS              │         │          SHIPMENTS              │
│─────────────────────────────────│         │─────────────────────────────────│
│ PK id (UUID)                    │         │ PK id (UUID)                    │
│ FK order_id -> orders.id        │         │ FK order_id -> orders.id        │
│    amount                       │         │    carrier                      │
│    status                       │         │    tracking_number              │
│    transaction_ref              │         │    status                       │
│    paid_at                      │         │    created_at                   │
│    created_at                   │         └─────────────────────────────────┘
└─────────────────────────────────┘
```

## Constraints
- UNIQUE `(user_id, idempotency_key)` on `orders`
- UNIQUE `(cart_id, product_id)` on `cart_items`
- UNIQUE `(order_id, product_id)` on `order_items` when one row per product
- CHECK `available_qty >= 0`, `reserved_qty >= 0`, `sold_qty >= 0`

## Status Enums
- carts.status: ACTIVE, CHECKED_OUT, ABANDONED
- products.status: ACTIVE, OUT_OF_STOCK, DISCONTINUED
- orders.status: CREATED, PAYMENT_PENDING, CONFIRMED, CANCELLED, SHIPPED, DELIVERED
- payments.status: PENDING, SUCCESS, FAILED, REFUNDED
- shipments.status: CREATED, PACKED, SHIPPED, DELIVERED, LOST
