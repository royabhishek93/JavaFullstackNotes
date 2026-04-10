# High-Level Design: Online Shopping Service (E-commerce like Amazon)

## System Overview
Design a large-scale e-commerce platform like Amazon that supports product catalog, search, shopping cart, checkout, order management, inventory tracking, payments, and shipping. System must handle millions of concurrent users during peak sales events.

---

## Requirements

### Functional Requirements
1. **User Management**: Registration, authentication, profile, addresses, payment methods
2. **Product Catalog**: Browse products, categories, filters, sorting
3. **Search**: Full-text search, autocomplete, filters, recommendations
4. **Shopping Cart**: Add/remove items, update quantity, save for later
5. **Checkout**: Multi-step checkout, address selection, payment, order confirmation
6. **Order Management**: Order tracking, cancellation, returns, refunds
7. **Inventory**: Real-time stock tracking, reservations, low-stock alerts
8. **Payments**: Multiple payment methods (cards, wallets, COD), PCI compliance
9. **Reviews & Ratings**: Product reviews, seller ratings, verified purchases
10. **Notifications**: Order confirmation, shipping updates, delivery alerts
11. **Seller Portal**: Product listing, inventory management, order fulfillment
12. **Recommendations**: Personalized product suggestions, frequently bought together

### Non-Functional Requirements
1. **Scalability**: 100M+ users, 10M concurrent users, 50K orders/sec (peak)
2. **Availability**: 99.99% uptime (52 minutes downtime/year)
3. **Performance**: 
   - Page load: < 2 seconds
   - Search: < 500ms
   - Checkout: < 3 seconds
4. **Consistency**: Strong consistency for inventory, eventual for catalog
5. **Reliability**: Zero data loss for orders and payments
6. **Security**: PCI DSS compliant, data encryption, fraud detection

---

## Capacity Estimation

### Traffic
- **Total Users**: 100M users
- **Daily Active Users (DAU)**: 10M (10% of total)
- **Peak Concurrent Users**: 1M (during sales)
- **Products**: 100M SKUs
- **Orders/day**: 5M orders
- **Orders/second**: 5M / 86400 ≈ 58 orders/sec (peak: 500 orders/sec)
- **Page Views**: 1B/day ≈ 11,500 requests/sec (peak: 50K req/sec)
- **Search Queries**: 100M/day ≈ 1,200 QPS (peak: 10K QPS)

### Storage
- **User Data**: 100M × 2KB = 200GB
- **Product Catalog**: 100M × 10KB = 1TB
- **Product Images**: 100M × 5 images × 200KB = 100TB (CDN)
- **Orders**: 5M orders/day × 2KB × 365 days = 3.6TB/year
- **Reviews**: 1M reviews/day × 1KB × 365 days = 365GB/year
- **Total**: ~105TB (primary data) + replicas (3x) = 315TB

### Bandwidth
- **Reads**: 50K req/sec × 50KB avg = 2.5GB/s = 20 Gbps
- **Writes**: 500 orders/sec × 2KB = 1MB/s
- **Image CDN**: 50K req/sec × 5 images × 200KB = 50GB/s = 400 Gbps (CDN handles this)

---

## System Architecture

```
                           ┌─────────────────────┐
                           │   Users (Web/App)   │
                           └──────────┬──────────┘
                                      │
                                      ▼
                           ┌─────────────────────┐
                           │   CDN (CloudFront)  │
                           │  (Static + Images)  │
                           └──────────┬──────────┘
                                      │
                                      ▼
                      ┌───────────────────────────────┐
                      │   Load Balancer (ALB/NLB)    │
                      └───────────┬───────────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
              ▼                   ▼                   ▼
    ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
    │   API Gateway    │ │  GraphQL Server  │ │  Mobile Gateway  │
    │   (REST APIs)    │ │   (Frontend)     │ │    (BFF)         │
    └────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
             │                    │                    │
             └────────────────────┼────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   User       │         │   Product    │         │   Cart       │
│   Service    │         │   Service    │         │   Service    │
└──────────────┘         └──────────────┘         └──────────────┘
        │                         │                         │
        ▼                         ▼                         ▼
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Order      │         │  Inventory   │         │  Payment     │
│   Service    │         │   Service    │         │   Service    │
└──────────────┘         └──────────────┘         └──────────────┘
        │                         │                         │
        ▼                         ▼                         ▼
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│  Shipping    │         │   Search     │         │Recommendation│
│   Service    │         │  Service     │         │   Service    │
└──────────────┘         └──────────────┘         └──────────────┘

────────────────────── Data Layer ──────────────────────

┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  PostgreSQL  │  │  MongoDB     │  │ Elasticsearch│  │    Redis     │
│ (Orders/Users│  │  (Catalog)   │  │  (Search)    │  │  (Cache/     │
│  Payments)   │  │              │  │              │  │   Sessions)  │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘

┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│    Kafka     │  │      S3      │  │  DynamoDB    │  │   Cassandra  │
│  (Events)    │  │  (Images)    │  │ (Cart/Sess)  │  │ (Analytics)  │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
```

---

## Core Components

### 1. User Service

**Responsibilities**:
- User registration, login, authentication
- Profile management
- Address book, payment methods
- Wishlist

**Database Schema** (PostgreSQL):
```sql
CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    date_of_birth DATE,
    gender VARCHAR(10),
    email_verified BOOLEAN DEFAULT FALSE,
    phone_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    loyalty_points INT DEFAULT 0,
    membership_tier VARCHAR(20), -- BASIC, PRIME, PREMIUM
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

CREATE TABLE addresses (
    address_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    address_type VARCHAR(20), -- HOME, WORK, OTHER
    full_name VARCHAR(200),
    phone VARCHAR(20),
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    postal_code VARCHAR(20),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE payment_methods (
    payment_method_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    type VARCHAR(20), -- CARD, UPI, WALLET, NET_BANKING
    card_last4 VARCHAR(4),
    card_brand VARCHAR(20), -- VISA, MASTERCARD, AMEX
    stripe_payment_method_id VARCHAR(100),
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**APIs**:
```
POST   /api/v1/users/register
POST   /api/v1/users/login
GET    /api/v1/users/me
PUT    /api/v1/users/me
POST   /api/v1/users/me/addresses
GET    /api/v1/users/me/addresses
PUT    /api/v1/users/me/addresses/{id}
DELETE /api/v1/users/me/addresses/{id}
```

---

### 2. Product Service

**Responsibilities**:
- Product CRUD operations
- Category management
- Product variants (size, color, etc.)
- Pricing and discounts
- Product metadata

**Database Schema** (MongoDB - flexible schema for varied products):
```javascript
// Products Collection
{
    "_id": ObjectId("..."),
    "product_id": "PROD123456",
    "title": "Apple iPhone 15 Pro",
    "brand": "Apple",
    "category_id": "electronics/phones/smartphones",
    "description": "Latest iPhone with A17 chip...",
    "specifications": {
        "screen_size": "6.1 inches",
        "storage": "256GB",
        "color": "Titanium Blue",
        "ram": "8GB"
    },
    "images": [
        "https://cdn.example.com/iphone15-1.jpg",
        "https://cdn.example.com/iphone15-2.jpg"
    ],
    "variants": [
        {
            "sku": "IPH15-256-BLUE",
            "color": "Blue",
            "storage": "256GB",
            "price": 999.00,
            "discount_price": 899.00,
            "stock": 150
        },
        {
            "sku": "IPH15-512-BLACK",
            "color": "Black",
            "storage": "512GB",
            "price": 1199.00,
            "stock": 80
        }
    ],
    "seller_id": "SELLER789",
    "average_rating": 4.5,
    "review_count": 1234,
    "tags": ["smartphone", "5g", "apple", "premium"],
    "is_active": true,
    "created_at": ISODate("2024-01-15T00:00:00Z"),
    "updated_at": ISODate("2024-04-01T00:00:00Z")
}

// Categories Collection
{
    "_id": ObjectId("..."),
    "category_id": "electronics",
    "name": "Electronics",
    "parent_id": null,
    "slug": "electronics",
    "image_url": "https://cdn.example.com/cat-electronics.jpg",
    "children": ["electronics/phones", "electronics/laptops"],
    "attributes": ["brand", "warranty", "color"]
}
```

**Caching Strategy**:
```java
// Product details - hot cache
@Cacheable(value = "products", key = "#productId", ttl = 3600)
public Product getProduct(String productId) {
    return productRepository.findById(productId);
}

// Category tree - rarely changes
@Cacheable(value = "categories", key = "'all'", ttl = 86400)
public List<Category> getAllCategories() {
    return categoryRepository.findAll();
}
```

**APIs**:
```
GET    /api/v1/products/{id}
GET    /api/v1/products
  ?category=electronics
  &brand=apple
  &minPrice=500
  &maxPrice=1500
  &sort=price_asc
  &page=1
  &limit=20
GET    /api/v1/categories
GET    /api/v1/categories/{id}/products
```

---

### 3. Search Service

**Technology**: Elasticsearch

**Index Schema**:
```json
{
  "settings": {
    "number_of_shards": 10,
    "number_of_replicas": 2,
    "analysis": {
      "analyzer": {
        "product_analyzer": {
          "type": "custom",
          "tokenizer": "standard",
          "filter": ["lowercase", "stop", "snowball"]
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "product_id": {"type": "keyword"},
      "title": {
        "type": "text",
        "analyzer": "product_analyzer",
        "fields": {
          "keyword": {"type": "keyword"},
          "completion": {"type": "completion"}
        }
      },
      "brand": {"type": "keyword"},
      "category": {"type": "keyword"},
      "description": {"type": "text"},
      "price": {"type": "double"},
      "discount_price": {"type": "double"},
      "average_rating": {"type": "float"},
      "review_count": {"type": "integer"},
      "stock": {"type": "integer"},
      "tags": {"type": "keyword"},
      "is_active": {"type": "boolean"},
      "created_at": {"type": "date"}
    }
  }
}
```

**Search Query Example**:
```json
POST /products/_search
{
  "query": {
    "function_score": {
      "query": {
        "bool": {
          "must": [
            {
              "multi_match": {
                "query": "wireless headphones",
                "fields": ["title^3", "description", "tags^2"],
                "type": "best_fields",
                "fuzziness": "AUTO"
              }
            }
          ],
          "filter": [
            {"term": {"is_active": true}},
            {"range": {"stock": {"gt": 0}}},
            {"range": {"price": {"gte": 50, "lte": 300}}}
          ],
          "should": [
            {"term": {"brand": "sony"}},
            {"range": {"average_rating": {"gte": 4.0}}}
          ]
        }
      },
      "functions": [
        {
          "filter": {"range": {"average_rating": {"gte": 4.5}}},
          "weight": 1.5
        },
        {
          "filter": {"range": {"review_count": {"gte": 100}}},
          "weight": 1.2
        },
        {
          "gauss": {
            "created_at": {
              "origin": "now",
              "scale": "30d",
              "decay": 0.5
            }
          }
        }
      ],
      "score_mode": "multiply",
      "boost_mode": "multiply"
    }
  },
  "aggs": {
    "brands": {
      "terms": {"field": "brand", "size": 20}
    },
    "price_ranges": {
      "range": {
        "field": "price",
        "ranges": [
          {"to": 50},
          {"from": 50, "to": 100},
          {"from": 100, "to": 200},
          {"from": 200}
        ]
      }
    }
  },
  "sort": [
    {"_score": {"order": "desc"}},
    {"average_rating": {"order": "desc"}}
  ],
  "from": 0,
  "size": 20
}
```

**Autocomplete**:
```json
POST /products/_search
{
  "suggest": {
    "product-suggest": {
      "prefix": "wireless head",
      "completion": {
        "field": "title.completion",
        "size": 10,
        "fuzzy": {
          "fuzziness": 2
        }
      }
    }
  }
}
```

**Data Sync** (CDC - Change Data Capture):
```
MongoDB → Debezium → Kafka → Elasticsearch Connector
```

---

### 4. Shopping Cart Service

**Challenges**:
- High read/write ratio (users add/remove items frequently)
- Session management (guest users)
- Cart abandonment tracking
- Merge cart on login

**Storage**: Redis + DynamoDB (for persistence)

**Data Model** (Redis):
```
Key: cart:{user_id}
Value: Hash
  {
    "item:{sku}": {
      "product_id": "PROD123",
      "sku": "IPH15-256-BLUE",
      "quantity": 2,
      "price": 899.00,
      "added_at": 1680000000
    },
    "item:{sku2}": {...}
  }

TTL: 30 days (auto-expire abandoned carts)
```

**Implementation**:
```java
@Service
public class CartService {
    
    @Autowired
    private RedisTemplate<String, Object> redis;
    
    public Cart addToCart(Long userId, String sku, int quantity) {
        String cartKey = "cart:" + userId;
        String itemKey = "item:" + sku;
        
        // Get product details
        Product product = productService.getProductBySku(sku);
        
        // Check inventory
        if (product.getStock() < quantity) {
            throw new InsufficientStockException();
        }
        
        // Add to cart
        CartItem item = new CartItem(
            product.getProductId(),
            sku,
            quantity,
            product.getPrice(),
            System.currentTimeMillis()
        );
        
        redis.opsForHash().put(cartKey, itemKey, item);
        redis.expire(cartKey, 30, TimeUnit.DAYS);
        
        return getCart(userId);
    }
    
    public Cart getCart(Long userId) {
        String cartKey = "cart:" + userId;
        Map<Object, Object> items = redis.opsForHash().entries(cartKey);
        
        Cart cart = new Cart();
        cart.setUserId(userId);
        cart.setItems(items.values().stream()
            .map(obj -> (CartItem) obj)
            .collect(Collectors.toList()));
        
        // Calculate totals
        BigDecimal subtotal = cart.getItems().stream()
            .map(item -> item.getPrice().multiply(new BigDecimal(item.getQuantity())))
            .reduce(BigDecimal.ZERO, BigDecimal::add);
        
        cart.setSubtotal(subtotal);
        cart.setTax(calculateTax(subtotal));
        cart.setTotal(subtotal.add(cart.getTax()));
        
        return cart;
    }
    
    public void removeFromCart(Long userId, String sku) {
        String cartKey = "cart:" + userId;
        String itemKey = "item:" + sku;
        redis.opsForHash().delete(cartKey, itemKey);
    }
    
    public void clearCart(Long userId) {
        String cartKey = "cart:" + userId;
        redis.delete(cartKey);
    }
    
    // Merge guest cart with user cart on login
    public void mergeCart(String sessionId, Long userId) {
        String guestCartKey = "cart:guest:" + sessionId;
        String userCartKey = "cart:" + userId;
        
        Map<Object, Object> guestItems = redis.opsForHash().entries(guestCartKey);
        Map<Object, Object> userItems = redis.opsForHash().entries(userCartKey);
        
        // Merge items (user cart takes precedence)
        for (Map.Entry<Object, Object> entry : guestItems.entrySet()) {
            if (!userItems.containsKey(entry.getKey())) {
                redis.opsForHash().put(userCartKey, entry.getKey(), entry.getValue());
            }
        }
        
        // Delete guest cart
        redis.delete(guestCartKey);
    }
}
```

**Persistence** (DynamoDB for durability):
```javascript
// Async backup to DynamoDB every 5 minutes
@Scheduled(fixedRate = 300000)
public void backupCarts() {
    Set<String> cartKeys = redis.keys("cart:*");
    for (String key : cartKeys) {
        Cart cart = getCartFromRedis(key);
        dynamoDBMapper.save(cart);
    }
}
```

**APIs**:
```
GET    /api/v1/cart
POST   /api/v1/cart/items
PUT    /api/v1/cart/items/{sku}
DELETE /api/v1/cart/items/{sku}
DELETE /api/v1/cart
```

---

### 5. Inventory Service

**Critical Requirements**:
- Real-time stock updates
- Prevent overselling
- Handle concurrent checkouts
- Inventory reservation during checkout

**Storage**: PostgreSQL (strong consistency) + Redis (caching)

**Database Schema**:
```sql
CREATE TABLE inventory (
    sku VARCHAR(50) PRIMARY KEY,
    product_id VARCHAR(50) NOT NULL,
    warehouse_id VARCHAR(50) NOT NULL,
    available_quantity INT NOT NULL CHECK (available_quantity >= 0),
    reserved_quantity INT NOT NULL DEFAULT 0,
    reorder_level INT DEFAULT 10,
    reorder_quantity INT DEFAULT 100,
    last_restocked_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_product_warehouse (product_id, warehouse_id)
);

CREATE TABLE inventory_reservations (
    reservation_id BIGSERIAL PRIMARY KEY,
    sku VARCHAR(50) REFERENCES inventory(sku),
    order_id BIGINT,
    user_id BIGINT,
    quantity INT NOT NULL,
    reserved_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP, -- Auto-release after 10 mins
    status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE, CONFIRMED, RELEASED
    INDEX idx_expires (expires_at, status)
);

CREATE TABLE inventory_transactions (
    transaction_id BIGSERIAL PRIMARY KEY,
    sku VARCHAR(50) NOT NULL,
    transaction_type VARCHAR(20), -- PURCHASE, RETURN, RESTOCK, ADJUSTMENT
    quantity INT NOT NULL,
    reference_id VARCHAR(50), -- order_id or return_id
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Inventory Check & Reserve** (Critical Path):
```java
@Service
public class InventoryService {
    
    // Reserve inventory during checkout (pessimistic locking)
    @Transactional(isolation = Isolation.SERIALIZABLE)
    public Reservation reserveInventory(String sku, int quantity, Long userId) {
        // Lock the row for update
        Inventory inventory = inventoryRepo.findBySkuForUpdate(sku);
        
        if (inventory == null) {
            throw new ProductNotFoundException();
        }
        
        int availableQty = inventory.getAvailableQuantity() - inventory.getReservedQuantity();
        if (availableQty < quantity) {
            throw new InsufficientStockException(
                String.format("Only %d units available", availableQty)
            );
        }
        
        // Create reservation
        Reservation reservation = new Reservation();
        reservation.setSku(sku);
        reservation.setQuantity(quantity);
        reservation.setUserId(userId);
        reservation.setReservedAt(Instant.now());
        reservation.setExpiresAt(Instant.now().plus(10, ChronoUnit.MINUTES));
        reservation.setStatus("ACTIVE");
        
        reservationRepo.save(reservation);
        
        // Update reserved quantity
        inventory.setReservedQuantity(inventory.getReservedQuantity() + quantity);
        inventoryRepo.save(inventory);
        
        return reservation;
    }
    
    // Confirm reservation on successful payment
    @Transactional
    public void confirmReservation(Long reservationId) {
        Reservation reservation = reservationRepo.findById(reservationId);
        
        if (reservation.getStatus().equals("ACTIVE")) {
            reservation.setStatus("CONFIRMED");
            reservationRepo.save(reservation);
            
            // Deduct from available quantity
            Inventory inventory = inventoryRepo.findBySku(reservation.getSku());
            inventory.setAvailableQuantity(
                inventory.getAvailableQuantity() - reservation.getQuantity()
            );
            inventory.setReservedQuantity(
                inventory.getReservedQuantity() - reservation.getQuantity()
            );
            inventoryRepo.save(inventory);
            
            // Log transaction
            logTransaction(reservation.getSku(), "PURCHASE", 
                -reservation.getQuantity(), reservation.getOrderId());
        }
    }
    
    // Release expired reservations (background job)
    @Scheduled(fixedRate = 60000) // Run every minute
    public void releaseExpiredReservations() {
        List<Reservation> expired = reservationRepo.findByStatusAndExpiresAtBefore(
            "ACTIVE", Instant.now()
        );
        
        for (Reservation reservation : expired) {
            releaseReservation(reservation.getReservationId());
        }
    }
    
    @Transactional
    public void releaseReservation(Long reservationId) {
        Reservation reservation = reservationRepo.findById(reservationId);
        
        if (reservation.getStatus().equals("ACTIVE")) {
            reservation.setStatus("RELEASED");
            reservationRepo.save(reservation);
            
            // Release reserved quantity
            Inventory inventory = inventoryRepo.findBySku(reservation.getSku());
            inventory.setReservedQuantity(
                inventory.getReservedQuantity() - reservation.getQuantity()
            );
            inventoryRepo.save(inventory);
        }
    }
}
```

**Optimistic Approach** (Alternative for high throughput):
```java
// Use version field for optimistic locking
@Entity
public class Inventory {
    @Version
    private Long version;
    
    // other fields...
}

public boolean reserveInventoryOptimistic(String sku, int quantity) {
    int maxRetries = 3;
    for (int i = 0; i < maxRetries; i++) {
        try {
            Inventory inventory = inventoryRepo.findBySku(sku);
            
            if (inventory.getAvailableQuantity() >= quantity) {
                inventory.setReservedQuantity(
                    inventory.getReservedQuantity() + quantity
                );
                inventoryRepo.save(inventory); // Throws OptimisticLockException if version changed
                return true;
            } else {
                return false;
            }
        } catch (OptimisticLockException e) {
            // Retry
            if (i == maxRetries - 1) {
                throw new ConcurrencyException();
            }
        }
    }
    return false;
}
```

**Low Stock Alerts**:
```java
@Scheduled(cron = "0 0 8 * * *") // Daily at 8 AM
public void checkLowStock() {
    List<Inventory> lowStock = inventoryRepo.findByAvailableQuantityLessThan(
        "reorder_level"
    );
    
    for (Inventory inv : lowStock) {
        // Send alert to inventory manager
        notificationService.sendLowStockAlert(inv);
        
        // Auto-reorder if enabled
        if (inv.isAutoReorderEnabled()) {
            createPurchaseOrder(inv.getSku(), inv.getReorderQuantity());
        }
    }
}
```

---

### 6. Order Service

**Responsibilities**:
- Order creation (checkout)
- Order status management
- Order history
- Cancellations and returns

**Database Schema**:
```sql
CREATE TABLE orders (
    order_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    order_number VARCHAR(50) UNIQUE NOT NULL, -- ORD-2024-04-001234
    status VARCHAR(20) NOT NULL, -- PENDING, CONFIRMED, PROCESSING, SHIPPED, DELIVERED, CANCELLED
    subtotal DECIMAL(10, 2) NOT NULL,
    tax DECIMAL(10, 2) NOT NULL,
    shipping_cost DECIMAL(10, 2) NOT NULL,
    discount DECIMAL(10, 2) DEFAULT 0,
    total DECIMAL(10, 2) NOT NULL,
    
    -- Shipping details
    shipping_address_id BIGINT,
    shipping_method VARCHAR(50), -- STANDARD, EXPRESS, OVERNIGHT
    estimated_delivery_date DATE,
    tracking_number VARCHAR(100),
    
    -- Payment details
    payment_method VARCHAR(20), -- CARD, UPI, WALLET, COD
    payment_status VARCHAR(20), -- PENDING, PAID, FAILED, REFUNDED
    payment_id VARCHAR(100),
    
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    
    INDEX idx_user_created (user_id, created_at DESC),
    INDEX idx_status (status),
    INDEX idx_order_number (order_number)
);

CREATE TABLE order_items (
    order_item_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT REFERENCES orders(order_id),
    product_id VARCHAR(50) NOT NULL,
    sku VARCHAR(50) NOT NULL,
    product_name VARCHAR(200),
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    discount DECIMAL(10, 2) DEFAULT 0,
    total DECIMAL(10, 2) NOT NULL,
    INDEX idx_order (order_id)
);

CREATE TABLE order_status_history (
    history_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT REFERENCES orders(order_id),
    status VARCHAR(20) NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Checkout Flow** (Critical Transaction):
```java
@Service
public class OrderService {
    
    @Transactional(isolation = Isolation.READ_COMMITTED)
    public OrderResponse createOrder(CheckoutRequest request) {
        Long userId = request.getUserId();
        
        // 1. Get cart
        Cart cart = cartService.getCart(userId);
        if (cart.getItems().isEmpty()) {
            throw new EmptyCartException();
        }
        
        // 2. Validate address
        Address address = addressService.getAddress(request.getAddressId());
        if (!address.getUserId().equals(userId)) {
            throw new UnauthorizedException();
        }
        
        // 3. Reserve inventory for all items
        List<Reservation> reservations = new ArrayList<>();
        try {
            for (CartItem item : cart.getItems()) {
                Reservation res = inventoryService.reserveInventory(
                    item.getSku(), item.getQuantity(), userId
                );
                reservations.add(res);
            }
        } catch (InsufficientStockException e) {
            // Release all reservations
            for (Reservation res : reservations) {
                inventoryService.releaseReservation(res.getReservationId());
            }
            throw e;
        }
        
        // 4. Create order
        Order order = new Order();
        order.setUserId(userId);
        order.setOrderNumber(generateOrderNumber());
        order.setStatus("PENDING");
        order.setSubtotal(cart.getSubtotal());
        order.setTax(cart.getTax());
        order.setShippingCost(calculateShipping(cart, address));
        order.setDiscount(applyDiscounts(cart, request.getCouponCode()));
        order.setTotal(cart.getTotal().add(order.getShippingCost()).subtract(order.getDiscount()));
        order.setShippingAddressId(address.getAddressId());
        order.setPaymentMethod(request.getPaymentMethod());
        order.setPaymentStatus("PENDING");
        
        orderRepo.save(order);
        
        // 5. Create order items
        for (CartItem item : cart.getItems()) {
            OrderItem orderItem = new OrderItem();
            orderItem.setOrderId(order.getOrderId());
            orderItem.setProductId(item.getProductId());
            orderItem.setSku(item.getSku());
            orderItem.setQuantity(item.getQuantity());
            orderItem.setUnitPrice(item.getPrice());
            orderItem.setTotal(item.getPrice().multiply(new BigDecimal(item.getQuantity())));
            orderItemRepo.save(orderItem);
        }
        
        // 6. Process payment
        PaymentResponse payment;
        try {
            payment = paymentService.processPayment(
                order.getOrderId(),
                order.getTotal(),
                request.getPaymentMethodId()
            );
        } catch (PaymentFailedException e) {
            // Release reservations
            for (Reservation res : reservations) {
                inventoryService.releaseReservation(res.getReservationId());
            }
            order.setStatus("CANCELLED");
            order.setPaymentStatus("FAILED");
            orderRepo.save(order);
            throw e;
        }
        
        // 7. Confirm reservations (deduct inventory)
        for (Reservation res : reservations) {
            res.setOrderId(order.getOrderId());
            inventoryService.confirmReservation(res.getReservationId());
        }
        
        // 8. Update order status
        order.setStatus("CONFIRMED");
        order.setPaymentStatus("PAID");
        order.setPaymentId(payment.getPaymentId());
        orderRepo.save(order);
        
        // 9. Clear cart
        cartService.clearCart(userId);
        
        // 10. Publish order event (async)
        kafkaProducer.send("order-events", new OrderCreatedEvent(order));
        
        // 11. Send confirmation email (async)
        notificationService.sendOrderConfirmation(order);
        
        return new OrderResponse(order.getOrderId(), order.getOrderNumber(), "SUCCESS");
    }
    
    private String generateOrderNumber() {
        // ORD-2024-04-001234
        return String.format("ORD-%s-%06d",
            LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy-MM")),
            orderRepo.countByCreatedAtBetween(
                LocalDate.now().atStartOfDay(),
                LocalDate.now().plusDays(1).atStartOfDay()
            ) + 1
        );
    }
}
```

**Order Status State Machine**:
```
PENDING → CONFIRMED → PROCESSING → SHIPPED → OUT_FOR_DELIVERY → DELIVERED
                ↓           ↓          ↓
            CANCELLED   CANCELLED  RETURN_REQUESTED → RETURNED → REFUNDED
```

**APIs**:
```
POST   /api/v1/orders                 # Create order (checkout)
GET    /api/v1/orders/{id}            # Get order details
GET    /api/v1/users/me/orders        # Order history
PUT    /api/v1/orders/{id}/cancel     # Cancel order
POST   /api/v1/orders/{id}/return     # Request return
GET    /api/v1/orders/{id}/track      # Track order
```

---

### 7. Payment Service

**Integration**: Stripe, PayPal, Razorpay

**Payment Methods**:
- Credit/Debit Cards
- UPI (India)
- Digital Wallets (PayPal, Apple Pay, Google Pay)
- Cash on Delivery (COD)
- Buy Now Pay Later (BNPL) - Klarna, Affirm

**Implementation** (Stripe):
```java
@Service
public class PaymentService {
    
    @Autowired
    private StripeClient stripeClient;
    
    public PaymentResponse processPayment(Long orderId, BigDecimal amount, String paymentMethodId) {
        try {
            // Create PaymentIntent
            PaymentIntentCreateParams params = PaymentIntentCreateParams.builder()
                .setAmount((long) (amount.doubleValue() * 100)) // Convert to cents
                .setCurrency("usd")
                .setPaymentMethod(paymentMethodId)
                .setConfirm(true) // Immediately attempt to confirm
                .putMetadata("order_id", orderId.toString())
                .setReceiptEmail(getUserEmail(orderId))
                .build();
            
            PaymentIntent intent = PaymentIntent.create(params);
            
            if (intent.getStatus().equals("succeeded")) {
                return new PaymentResponse(
                    intent.getId(),
                    "SUCCESS",
                    amount
                );
            } else if (intent.getStatus().equals("requires_action")) {
                // 3D Secure authentication required
                return new PaymentResponse(
                    intent.getId(),
                    "REQUIRES_ACTION",
                    intent.getClientSecret()
                );
            } else {
                throw new PaymentFailedException("Payment failed: " + intent.getStatus());
            }
            
        } catch (StripeException e) {
            log.error("Stripe payment failed for order {}: {}", orderId, e.getMessage());
            throw new PaymentFailedException(e.getMessage());
        }
    }
    
    // Process refund
    public RefundResponse processRefund(String paymentIntentId, BigDecimal amount) {
        try {
            RefundCreateParams params = RefundCreateParams.builder()
                .setPaymentIntent(paymentIntentId)
                .setAmount((long) (amount.doubleValue() * 100))
                .build();
            
            Refund refund = Refund.create(params);
            
            return new RefundResponse(refund.getId(), "SUCCESS", amount);
            
        } catch (StripeException e) {
            throw new RefundFailedException(e.getMessage());
        }
    }
    
    // Webhook handler for async payment updates
    @PostMapping("/webhooks/stripe")
    public ResponseEntity<String> handleStripeWebhook(
        @RequestBody String payload,
        @RequestHeader("Stripe-Signature") String sigHeader
    ) {
        Event event = Webhook.constructEvent(payload, sigHeader, webhookSecret);
        
        switch (event.getType()) {
            case "payment_intent.succeeded":
                handlePaymentSuccess(event);
                break;
            case "payment_intent.payment_failed":
                handlePaymentFailure(event);
                break;
            case "refund.created":
                handleRefund(event);
                break;
        }
        
        return ResponseEntity.ok("Received");
    }
}
```

**Payment Security**:
- PCI DSS Level 1 compliance (via Stripe - they handle card data)
- Tokenization (never store card numbers)
- 3D Secure (SCA - Strong Customer Authentication)
- Fraud detection (Stripe Radar)
- Rate limiting (prevent brute force)

---

### 8. Recommendation Service

**Recommendation Types**:
1. **Personalized**: Based on user history
2. **Collaborative Filtering**: Users like you also bought...
3. **Content-Based**: Similar products
4. **Trending**: Popular right now
5. **Frequently Bought Together**: Bundle recommendations

**Architecture**:
```
User Activity → Kafka → Spark Streaming → ML Model → Redis Cache → API
```

**Data Pipeline**:
```python
# Collect user interactions
user_interactions = [
    (user_id, product_id, action_type, timestamp)
    # action_type: VIEW, CLICK, ADD_TO_CART, PURCHASE
]

# Feature engineering
user_features = [
    'total_purchases',
    'avg_order_value',
    'favorite_categories',
    'price_sensitivity',
    'brand_preference'
]

product_features = [
    'category',
    'price_range',
    'average_rating',
    'popularity_score',
    'tags'
]

# Collaborative Filtering (Matrix Factorization)
from surprise import SVD, Dataset, Reader

# User-Item matrix
reader = Reader(rating_scale=(1, 5))
data = Dataset.load_from_df(df[['user_id', 'product_id', 'implicit_rating']], reader)

# Train SVD model
model = SVD(n_factors=100, n_epochs=20, lr_all=0.005, reg_all=0.02)
model.fit(data.build_full_trainset())

# Predict ratings for all products
predictions = model.test(test_set)

# Get top N recommendations
top_n = get_top_n(predictions, n=10)
```

**Real-time Recommendations** (Kafka Streams):
```java
@Component
public class RecommendationStream {
    
    @Bean
    public Function<KStream<String, UserAction>, KStream<String, Recommendation>> processActions() {
        return actions -> actions
            .filter((key, action) -> action.getType().equals("VIEW"))
            .groupByKey()
            .windowedBy(TimeWindows.of(Duration.ofMinutes(5)))
            .aggregate(
                UserSession::new,
                (key, action, session) -> session.addAction(action),
                Materialized.with(Serdes.String(), userSessionSerde)
            )
            .toStream()
            .mapValues(session -> generateRecommendations(session));
    }
    
    private Recommendation generateRecommendations(UserSession session) {
        // Get recently viewed products
        List<String> viewedProducts = session.getViewedProducts();
        
        // Get similar products from cache or ML model
        List<Product> recommendations = mlService.getSimilarProducts(viewedProducts);
        
        return new Recommendation(session.getUserId(), recommendations);
    }
}
```

**Caching** (Redis):
```java
// Cache recommendations for 1 hour
@Cacheable(value = "recommendations", key = "#userId", ttl = 3600)
public List<Product> getRecommendations(Long userId) {
    return mlService.getPersonalizedRecommendations(userId);
}
```

---

### 9. Notification Service

**Notification Channels**:
- Email (SendGrid, AWS SES)
- SMS (Twilio)
- Push Notifications (Firebase Cloud Messaging)
- In-app notifications

**Event-Driven Architecture**:
```
Order Service → Kafka (order-events) → Notification Consumer → Multi-channel delivery
```

**Implementation**:
```java
@Service
@KafkaListener(topics = "order-events", groupId = "notification-service")
public class NotificationConsumer {
    
    public void handleOrderEvent(OrderEvent event) {
        switch (event.getType()) {
            case ORDER_CREATED:
                sendOrderConfirmation(event.getOrder());
                break;
            case ORDER_SHIPPED:
                sendShippingNotification(event.getOrder());
                break;
            case ORDER_DELIVERED:
                sendDeliveryConfirmation(event.getOrder());
                break;
            case ORDER_CANCELLED:
                sendCancellationNotification(event.getOrder());
                break;
        }
    }
    
    private void sendOrderConfirmation(Order order) {
        User user = userService.getUser(order.getUserId());
        
        // Email
        emailService.sendTemplate(
            user.getEmail(),
            "order_confirmation",
            Map.of(
                "orderNumber", order.getOrderNumber(),
                "total", order.getTotal(),
                "estimatedDelivery", order.getEstimatedDeliveryDate()
            )
        );
        
        // Push notification
        if (user.getFcmToken() != null) {
            fcmService.send(
                user.getFcmToken(),
                "Order Confirmed!",
                "Your order " + order.getOrderNumber() + " has been confirmed"
            );
        }
        
        // SMS (optional, for high-value orders)
        if (order.getTotal().compareTo(new BigDecimal(1000)) > 0) {
            smsService.send(
                user.getPhone(),
                "Your order " + order.getOrderNumber() + " worth $" + order.getTotal() + " is confirmed"
            );
        }
    }
}
```

---

## Scalability & Performance

### 1. Caching Strategy

**Multi-Layer Caching**:
```
Client (Browser Cache) → CDN → Application Cache (Redis) → Database
```

**Cache Layers**:
```java
// L1: Product catalog (hot products)
@Cacheable(value = "products:hot", ttl = 3600)
public Product getProduct(String productId) { ... }

// L2: User sessions
@Cacheable(value = "sessions", ttl = 1800)
public UserSession getSession(String sessionId) { ... }

// L3: Search results
@Cacheable(value = "search", key = "#query + #filters", ttl = 300)
public SearchResults search(String query, Filters filters) { ... }

// L4: Recommendations
@Cacheable(value = "recommendations", key = "#userId", ttl = 3600)
public List<Product> getRecommendations(Long userId) { ... }
```

**Cache Invalidation**:
```java
// Invalidate product cache on update
@CacheEvict(value = "products", key = "#product.productId")
public void updateProduct(Product product) { ... }

// Invalidate all search caches for category
@CacheEvict(value = "search", allEntries = true)
public void updateCategory(Category category) { ... }
```

### 2. Database Sharding

**Sharding Strategy**:
```sql
-- Shard by user_id (for orders, cart, addresses)
shard_id = user_id % num_shards

-- Shard by product_id (for products, inventory)
shard_id = hash(product_id) % num_shards

-- Example: 10 shards
Shard 0: user_id ending in 0
Shard 1: user_id ending in 1
...
Shard 9: user_id ending in 9
```

**Shard Routing**:
```java
@Component
public class ShardRouter {
    
    @Autowired
    private List<DataSource> dataSources; // 10 data sources
    
    public DataSource getShardForUser(Long userId) {
        int shardId = (int) (userId % dataSources.size());
        return dataSources.get(shardId);
    }
    
    public DataSource getShardForProduct(String productId) {
        int hash = productId.hashCode();
        int shardId = Math.abs(hash) % dataSources.size();
        return dataSources.get(shardId);
    }
}
```

### 3. Read Replicas

**Read-Write Splitting**:
```
Master (Write): Orders, Payments, Inventory updates
Replica 1 (Read): Product catalog, Search
Replica 2 (Read): User profiles, Order history
Replica 3 (Read): Analytics, Reports
```

```java
@Configuration
public class DatabaseConfig {
    
    @Bean
    @Primary
    public DataSource masterDataSource() {
        return DataSourceBuilder.create()
            .url("jdbc:postgresql://master.db.example.com:5432/ecommerce")
            .build();
    }
    
    @Bean
    public DataSource replicaDataSource() {
        return DataSourceBuilder.create()
            .url("jdbc:postgresql://replica.db.example.com:5432/ecommerce")
            .build();
    }
    
    @Bean
    public DataSource routingDataSource() {
        Map<Object, Object> dataSourceMap = new HashMap<>();
        dataSourceMap.put("master", masterDataSource());
        dataSourceMap.put("replica", replicaDataSource());
        
        RoutingDataSource routingDataSource = new RoutingDataSource();
        routingDataSource.setTargetDataSources(dataSourceMap);
        routingDataSource.setDefaultTargetDataSource(masterDataSource());
        return routingDataSource;
    }
}

// Use @Transactional(readOnly = true) for read queries
@Transactional(readOnly = true)
public Product getProduct(String productId) {
    // Routes to replica
}

@Transactional
public void createOrder(Order order) {
    // Routes to master
}
```

### 4. Horizontal Scaling

**Auto-Scaling** (Kubernetes HPA):
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: product-service-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: product-service
  minReplicas: 10
  maxReplicas: 100
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
```

### 5. CDN for Static Assets

**CloudFront Configuration**:
```
Origin: S3 bucket (images.ecommerce.com)
Edge Locations: Global distribution (200+ locations)
Cache-Control: max-age=86400 (24 hours)
Gzip Compression: Enabled
HTTP/2: Enabled
SSL: Custom certificate
```

**Image Optimization**:
```
Original: https://images.ecommerce.com/products/iphone15.jpg
Thumbnail: https://images.ecommerce.com/products/iphone15_thumb.webp
Variants:
  - 100x100 (grid view)
  - 300x300 (list view)
  - 800x800 (detail view)
  - 1920x1920 (zoom view)
Format: WebP (30-50% smaller than JPEG)
Lazy loading: Load images on scroll
```

---

## Monitoring & Observability

### Key Metrics

**Business Metrics**:
```
- Orders per second (current, peak)
- Conversion rate (orders / sessions)
- Average order value (AOV)
- Cart abandonment rate
- Revenue (real-time, daily, monthly)
- Top-selling products
- Payment success rate
```

**Technical Metrics**:
```
- API latency (p50, p95, p99, p999)
- Database query time
- Cache hit ratio (target: > 85%)
- Error rate (target: < 0.1%)
- Throughput (requests/sec)
- Inventory accuracy
```

### Alerting

```yaml
alerts:
  - name: HighOrderLatency
    condition: p99(order_creation_time) > 5s
    severity: CRITICAL
    action: page_oncall
  
  - name: LowInventoryAccuracy
    condition: inventory_mismatch_rate > 1%
    severity: HIGH
    action: slack_alert
  
  - name: PaymentFailureSpike
    condition: payment_failure_rate > 5%
    severity: CRITICAL
    action: page_oncall
  
  - name: DatabaseConnectionPoolExhausted
    condition: db_connections_used / db_connections_max > 0.9
    severity: HIGH
    action: auto_scale_db_connections
```

---

## Technology Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **Backend** | Java/Spring Boot | Mature ecosystem, enterprise-grade |
| **Frontend** | React/Next.js | SEO-friendly, fast rendering |
| **Mobile** | React Native | Cross-platform, code reuse |
| **API Gateway** | Kong / AWS API Gateway | Auth, rate limiting, routing |
| **Database (OLTP)** | PostgreSQL | ACID, strong consistency |
| **Database (Catalog)** | MongoDB | Flexible schema for varied products |
| **Cache** | Redis | In-memory, session storage |
| **Search** | Elasticsearch | Full-text search, faceted filters |
| **Message Queue** | Apache Kafka | Event streaming, high throughput |
| **Object Storage** | AWS S3 | Scalable, durable image storage |
| **CDN** | CloudFront | Global content delivery |
| **Payments** | Stripe / Razorpay | PCI compliant, easy integration |
| **Recommendations** | Apache Spark + MLlib | Large-scale ML |
| **Monitoring** | Prometheus + Grafana | Metrics and dashboards |
| **Logging** | ELK Stack | Centralized log aggregation |
| **Tracing** | Jaeger / Zipkin | Distributed tracing |
| **Container** | Docker + Kubernetes | Orchestration, auto-scaling |

---

## Interview Q&A

### Q1: How do you prevent overselling (race condition in inventory)?
**Answer**:
1. **Pessimistic Locking**: `SELECT FOR UPDATE` in transaction
2. **Optimistic Locking**: Use version field, retry on conflict
3. **Distributed Lock**: Redis/Zookeeper lock on SKU
4. **Inventory Reservation**: Reserve during checkout, confirm on payment
5. **Queue-based**: Serialize inventory updates through queue

### Q2: How do you handle flash sales (traffic spikes)?
**Answer**:
1. **Auto-scaling**: Kubernetes HPA based on CPU/memory
2. **Pre-warming**: Scale up before sale starts
3. **Rate Limiting**: Per-user request limits
4. **Queue System**: Virtual waiting room (Cloudflare Waiting Room)
5. **Caching**: Aggressively cache product data
6. **CDN**: Offload static content
7. **Database**: Read replicas, connection pooling
8. **Graceful Degradation**: Disable non-critical features

### Q3: How do you ensure cart consistency across devices?
**Answer**:
1. **Session Sync**: Store cart in Redis with session ID
2. **User Login**: Merge guest cart with user cart
3. **Real-time Sync**: WebSocket for multi-device updates
4. **Persistent Storage**: DynamoDB for durability
5. **Conflict Resolution**: Last-write-wins or merge strategy

### Q4: How do you implement personalized recommendations at scale?
**Answer**:
1. **Offline Training**: Spark job runs daily to train ML model
2. **Feature Store**: Pre-compute user/product features
3. **Online Serving**: Load model in memory, serve from cache
4. **A/B Testing**: Test multiple recommendation algorithms
5. **Fallback**: Rule-based recommendations if ML fails

### Q5: How do you handle distributed transactions (order + payment + inventory)?
**Answer**:
**Saga Pattern** (preferred over 2PC):
```
1. Reserve Inventory → Success
2. Create Order → Success
3. Process Payment → Failure
4. Compensate: Release Inventory, Cancel Order
```
Each service publishes events, next service reacts. On failure, run compensating transactions in reverse.

### Q6: How do you optimize database queries for product search?
**Answer**:
1. **Indexes**: Compound indexes on (category, price, rating)
2. **Materialized Views**: Pre-aggregated data
3. **Partitioning**: Partition by category or date
4. **Elasticsearch**: Offload search to dedicated search engine
5. **Caching**: Cache popular search results
6. **Pagination**: Limit results, use cursor-based pagination

### Q7: How do you handle multi-currency and internationalization?
**Answer**:
1. **Base Currency**: Store all prices in USD
2. **Real-time Conversion**: Use forex API (e.g., Fixer.io)
3. **Display**: Show prices in user's preferred currency
4. **Payment**: Process in local currency for better rates
5. **Tax Calculation**: Country-specific tax logic
6. **Localization**: i18n for translated content

### Q8: How do you detect and prevent fraud?
**Answer**:
1. **Rule-based**: Flag suspicious patterns (multiple cards, high-value orders)
2. **ML Model**: Train on historical fraud data
3. **Device Fingerprinting**: Track device ID, IP, browser
4. **Velocity Checks**: Limit orders per user/IP per hour
5. **3D Secure**: Strong Customer Authentication (SCA)
6. **Manual Review**: High-risk orders reviewed by team

### Q9: How do you optimize checkout performance?
**Answer**:
1. **Reduce Steps**: One-page checkout
2. **Prefetch Data**: Load addresses, payment methods in parallel
3. **Async Processing**: Queue order confirmation emails
4. **Connection Pooling**: Reuse DB connections
5. **Caching**: Cache user data, tax rates
6. **CDN**: Serve checkout page from edge
7. **Database**: Optimize queries, use read replicas

### Q10: How do you ensure data consistency between MongoDB (catalog) and Elasticsearch (search)?
**Answer**:
**Change Data Capture (CDC)**:
```
MongoDB → Debezium → Kafka → Elasticsearch Connector
```
- Debezium captures MongoDB oplog changes
- Publishes to Kafka topic
- Elasticsearch connector consumes and indexes
- **Eventual Consistency**: Search may lag by 1-2 seconds
- **Reconciliation Job**: Daily batch job to fix any drift

---

## Cost Estimation (AWS - Monthly)

| Service | Specification | Cost |
|---------|--------------|------|
| **EKS** (App Servers) | 100 × m5.2xlarge (8 vCPU, 32GB) | $24,000 |
| **RDS PostgreSQL** | Multi-AZ, db.r5.4xlarge + 5 replicas | $20,000 |
| **DocumentDB** (MongoDB) | 10 × db.r5.xlarge | $8,000 |
| **ElastiCache Redis** | 20 × cache.r5.xlarge | $6,000 |
| **Elasticsearch** | 10 × r5.2xlarge | $8,000 |
| **MSK** (Kafka) | 9 brokers × kafka.m5.large | $2,000 |
| **S3** | 500TB storage + requests | $11,500 |
| **CloudFront** | 500TB transfer | $42,500 |
| **API Gateway** | 5B requests | $17,500 |
| **Lambda** | 100M invocations | $2,000 |
| **Data Transfer** | Inter-AZ & outbound | $5,000 |
| **Monitoring** | CloudWatch, X-Ray | $1,500 |
| **Total** | | **~$148,000/month** |

**Revenue Model** (assuming Amazon-scale margins):
- GMV: $1B/month
- Commission: 15% = $150M
- Infrastructure: 0.1% of revenue
- Very profitable at scale!

---

**This comprehensive HLD covers a production-grade e-commerce platform at Amazon scale!**
