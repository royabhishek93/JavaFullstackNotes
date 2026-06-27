# Designing an E-commerce System (LLD)

## Requirements
1. Users should browse products by category, brand, and filters.
2. Users should add products to cart and place orders.
3. System should validate stock availability during checkout.
4. Support payment integration and order confirmation.
5. Support order cancellation, returns, and refunds.
6. Track shipment lifecycle.
7. Prevent duplicate order creation on retries.
8. Handle high concurrency during flash sales.

## Core Components
1. Catalog Service
- Manages products, categories, pricing, attributes.

2. Inventory Service
- Tracks available, reserved, and sold quantities.
- Ensures no oversell.

3. Cart Service
- Maintains user cart and quantities.

4. Checkout Service
- Validates cart, reserves inventory, creates order.

5. Order Service
- Persists order, items, and status changes.

6. Payment Service
- Handles payment intent, callback, and reconciliation.

7. Shipment Service
- Creates shipment and tracks package status.

## Core Entities
1. Product
- id, sku, name, brand, categoryId, price, status

2. Inventory
- productId, availableQty, reservedQty, soldQty, version

3. Cart
- id, userId, status

4. CartItem
- cartId, productId, quantity, unitPriceSnapshot

5. Order
- id, userId, totalAmount, status, idempotencyKey

6. OrderItem
- orderId, productId, quantity, unitPriceSnapshot

7. Payment
- orderId, amount, status, transactionRef

8. Shipment
- orderId, carrier, trackingNumber, status

## APIs
- GET /v1/products
- GET /v1/products/{id}
- POST /v1/carts
- POST /v1/carts/{id}/items
- POST /v1/checkout
- GET /v1/orders/{id}
- POST /v1/orders/{id}/cancel
- POST /v1/payments/webhook

## Checkout Flow
1. Fetch cart.
2. Validate product status and quantity.
3. Reserve inventory atomically.
4. Create order and order items.
5. Create payment intent.
6. Confirm payment.
7. Convert reserved -> sold.
8. Create shipment.

## State Transitions
- Order: CREATED -> PAYMENT_PENDING -> CONFIRMED -> SHIPPED -> DELIVERED
- Payment: PENDING -> SUCCESS or FAILED or REFUNDED
- Shipment: CREATED -> PACKED -> SHIPPED -> DELIVERED
- Inventory: AVAILABLE -> RESERVED -> SOLD

## Concurrency Strategy
- Use optimistic locking/version on inventory rows.
- Unique `(user_id, idempotency_key)` for order placement.
- Flash sale path uses reservation with short TTL.

## Interview One-Liner
E-commerce correctness depends on inventory reservation discipline, not just order creation logic.
