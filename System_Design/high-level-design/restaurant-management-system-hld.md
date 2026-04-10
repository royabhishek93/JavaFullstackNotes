# High-Level Design: Restaurant Management System (POS & Operations)

## System Overview
Design a comprehensive restaurant management system that handles point-of-sale (POS), inventory management, table reservations, kitchen operations, staff management, and reporting. System serves restaurants ranging from small cafes to multi-location chains.

---

## Requirements

### Functional Requirements
1. **Table Management**: Table layout, status (occupied, reserved, available), party size
2. **Reservations**: Online/phone reservations, waitlist, seating optimization
3. **Order Management**: Dine-in, takeout, delivery orders
4. **Menu Management**: Items, categories, pricing, modifiers, availability
5. **Kitchen Display System (KDS)**: Order routing, preparation tracking, timing
6. **Payment Processing**: Split bills, tips, multiple payment methods
7. **Inventory Management**: Stock tracking, supplier orders, wastage
8. **Staff Management**: Schedules, time tracking, performance, tips distribution
9. **Reporting & Analytics**: Sales, top items, peak hours, staff performance
10. **Multi-location**: Support chains with centralized management

### Non-Functional Requirements
1. **Availability**: 99.9% uptime during service hours
2. **Low Latency**: < 500ms for order placement, < 1s for payment
3. **Reliability**: Zero order loss, accurate inventory tracking
4. **Offline Mode**: POS works offline, syncs when online
5. **Scalability**: Support 10,000+ locations, 100K orders/day per location
6. **Security**: PCI DSS compliance, role-based access
7. **Usability**: Touch-friendly UI, minimal training needed

---

## Capacity Estimation

### Traffic
- **Total Locations**: 10,000 restaurants
- **Average orders/location/day**: 200 orders
- **Peak hours**: 12-2 PM, 6-9 PM (70% of daily orders)
- **Orders/second (system-wide)**: 10K × 200 / 86400 ≈ 23 orders/sec (peak: 200 orders/sec)
- **Concurrent users (staff)**: 10K locations × 5 staff = 50K users
- **Reservations**: 50K/day system-wide

### Storage
- **Menus**: 10K locations × 100 items × 2KB = 2GB
- **Orders**: 2M orders/day × 5KB × 365 days = 3.6TB/year
- **Inventory**: 10K locations × 500 items × 1KB = 5GB
- **Reservations**: 50K/day × 500 bytes × 365 days = 9GB/year
- **Staff**: 50K users × 10KB = 500MB
- **Total**: ~4TB/year with replicas (3x) = 12TB

### Bandwidth
- **Order writes**: 200 orders/sec × 5KB = 1MB/s
- **KDS updates**: 200 orders/sec × 2KB = 400KB/s
- **Reports/analytics**: 100 req/sec × 50KB = 5MB/s

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Client Layer                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   POS App    │  │     KDS      │  │  Mobile App  │          │
│  │  (Tablet)    │  │   (Kitchen)  │  │ (Customers)  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└──────────┬────────────────┬────────────────┬───────────────────┘
           │                │                │
           ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│              API Gateway / Load Balancer                         │
│              (Offline-first sync layer)                          │
└──────────┬────────────────┬────────────────┬───────────────────┘
           │                │                │
           ▼                ▼                ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Microservices Layer                            │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐   │
│  │   Order    │ │   Table    │ │ Reservation│ │   Menu     │   │
│  │  Service   │ │  Service   │ │  Service   │ │  Service   │   │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘   │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐   │
│  │  Payment   │ │ Inventory  │ │   Staff    │ │ Analytics  │   │
│  │  Service   │ │  Service   │ │  Service   │ │  Service   │   │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘   │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐                  │
│  │  Kitchen   │ │Notification│ │  Reporting │                  │
│  │  Service   │ │  Service   │ │  Service   │                  │
│  └────────────┘ └────────────┘ └────────────┘                  │
└──────────┬────────────────┬────────────────┬───────────────────┘
           │                │                │
           ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  PostgreSQL  │  │    Redis     │  │    Kafka     │
│  (Primary)   │  │  (Cache/RT)  │  │  (Events)    │
└──────────────┘  └──────────────┘  └──────────────┘
           │                │
           ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│Elasticsearch │  │      S3      │  │  QuickSight  │
│  (Search)    │  │ (Reports/Img)│  │ (Dashboard)  │
└──────────────┘  └──────────────┘  └──────────────┘
```

---

## Core Components

### 1. Table Management Service

**Responsibilities**:
- Manage table layout (floor plan)
- Track table status (available, occupied, reserved, cleaning)
- Assign tables to parties
- Optimize seating (combine/split tables)

**Database Schema**:
```sql
CREATE TABLE restaurants (
    restaurant_id BIGSERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    address TEXT,
    phone VARCHAR(20),
    timezone VARCHAR(50),
    opening_time TIME,
    closing_time TIME,
    capacity INT, -- Total seats
    avg_table_turn_time INT DEFAULT 60, -- minutes
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE floors (
    floor_id BIGSERIAL PRIMARY KEY,
    restaurant_id BIGINT REFERENCES restaurants(restaurant_id),
    floor_name VARCHAR(50), -- Main Floor, Patio, Upstairs
    layout_json JSONB, -- {tables: [{id, x, y, width, height}]}
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE tables (
    table_id BIGSERIAL PRIMARY KEY,
    restaurant_id BIGINT REFERENCES restaurants(restaurant_id),
    floor_id BIGINT REFERENCES floors(floor_id),
    table_number VARCHAR(10) NOT NULL,
    capacity INT NOT NULL,
    min_capacity INT DEFAULT 1,
    max_capacity INT,
    position_x INT, -- For floor plan visualization
    position_y INT,
    status VARCHAR(20) DEFAULT 'AVAILABLE', -- AVAILABLE, OCCUPIED, RESERVED, CLEANING
    current_order_id BIGINT,
    occupied_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE (restaurant_id, table_number)
);

CREATE TABLE table_assignments (
    assignment_id BIGSERIAL PRIMARY KEY,
    restaurant_id BIGINT REFERENCES restaurants(restaurant_id),
    table_id BIGINT REFERENCES tables(table_id),
    reservation_id BIGINT,
    party_size INT NOT NULL,
    server_id BIGINT REFERENCES staff(staff_id),
    seated_at TIMESTAMP DEFAULT NOW(),
    cleared_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE, COMPLETED
    INDEX idx_restaurant_status (restaurant_id, status)
);
```

**APIs**:
```
GET    /api/v1/restaurants/{id}/tables         # Get all tables
PUT    /api/v1/tables/{id}/status              # Update table status
POST   /api/v1/tables/{id}/assign              # Assign table to party
GET    /api/v1/restaurants/{id}/floor-plan     # Get floor plan layout
```

**Real-time Table Status** (WebSocket):
```javascript
// Kitchen staff/host sees live table status
socket.on('table-status-update', (data) => {
    // { table_id: 5, status: 'OCCUPIED', party_size: 4, time_elapsed: '15m' }
    updateTableUI(data);
});
```

---

### 2. Reservation Service

**Responsibilities**:
- Online/phone reservations
- Waitlist management
- Table availability calculation
- Reservation reminders

**Database Schema**:
```sql
CREATE TABLE reservations (
    reservation_id BIGSERIAL PRIMARY KEY,
    restaurant_id BIGINT REFERENCES restaurants(restaurant_id),
    customer_name VARCHAR(200) NOT NULL,
    customer_phone VARCHAR(20),
    customer_email VARCHAR(255),
    party_size INT NOT NULL,
    reservation_date DATE NOT NULL,
    reservation_time TIME NOT NULL,
    duration_minutes INT DEFAULT 90,
    status VARCHAR(20) DEFAULT 'CONFIRMED', -- CONFIRMED, SEATED, NO_SHOW, CANCELLED
    special_requests TEXT,
    table_id BIGINT REFERENCES tables(table_id),
    created_at TIMESTAMP DEFAULT NOW(),
    confirmed_at TIMESTAMP,
    INDEX idx_restaurant_date (restaurant_id, reservation_date, reservation_time)
);

CREATE TABLE waitlist (
    waitlist_id BIGSERIAL PRIMARY KEY,
    restaurant_id BIGINT REFERENCES restaurants(restaurant_id),
    customer_name VARCHAR(200) NOT NULL,
    customer_phone VARCHAR(20) NOT NULL,
    party_size INT NOT NULL,
    added_at TIMESTAMP DEFAULT NOW(),
    estimated_wait_minutes INT,
    notified_at TIMESTAMP,
    seated_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'WAITING', -- WAITING, NOTIFIED, SEATED, LEFT
    INDEX idx_restaurant_status (restaurant_id, status, added_at)
);
```

**Table Availability Algorithm**:
```java
@Service
public class ReservationService {
    
    public AvailabilityResponse checkAvailability(
        Long restaurantId, 
        LocalDate date, 
        LocalTime time, 
        int partySize
    ) {
        // 1. Get all tables that can accommodate party size
        List<Table> suitableTables = tableRepo.findByRestaurantIdAndMinCapacityLessThanEqualAndMaxCapacityGreaterThanEqual(
            restaurantId, partySize, partySize
        );
        
        if (suitableTables.isEmpty()) {
            return new AvailabilityResponse(false, "No suitable tables");
        }
        
        // 2. Get existing reservations for the time slot
        LocalDateTime startTime = LocalDateTime.of(date, time);
        LocalDateTime endTime = startTime.plusMinutes(90); // Average meal duration
        
        List<Reservation> existingReservations = reservationRepo.findOverlapping(
            restaurantId, startTime.minusMinutes(90), endTime
        );
        
        // 3. Get occupied tables
        Set<Long> occupiedTableIds = existingReservations.stream()
            .map(Reservation::getTableId)
            .filter(Objects::nonNull)
            .collect(Collectors.toSet());
        
        // 4. Find available tables
        List<Table> availableTables = suitableTables.stream()
            .filter(table -> !occupiedTableIds.contains(table.getTableId()))
            .collect(Collectors.toList());
        
        if (availableTables.isEmpty()) {
            // Suggest alternative times
            List<LocalTime> suggestions = findAlternativeTimes(restaurantId, date, time, partySize);
            return new AvailabilityResponse(false, "Fully booked", suggestions);
        }
        
        return new AvailabilityResponse(true, "Available");
    }
    
    @Transactional
    public Reservation createReservation(ReservationRequest request) {
        // 1. Check availability
        AvailabilityResponse availability = checkAvailability(
            request.getRestaurantId(),
            request.getDate(),
            request.getTime(),
            request.getPartySize()
        );
        
        if (!availability.isAvailable()) {
            throw new NoAvailabilityException();
        }
        
        // 2. Create reservation
        Reservation reservation = new Reservation();
        reservation.setRestaurantId(request.getRestaurantId());
        reservation.setCustomerName(request.getCustomerName());
        reservation.setCustomerPhone(request.getCustomerPhone());
        reservation.setCustomerEmail(request.getCustomerEmail());
        reservation.setPartySize(request.getPartySize());
        reservation.setReservationDate(request.getDate());
        reservation.setReservationTime(request.getTime());
        reservation.setStatus("CONFIRMED");
        
        reservationRepo.save(reservation);
        
        // 3. Send confirmation
        notificationService.sendReservationConfirmation(reservation);
        
        // 4. Schedule reminder (1 day before)
        scheduleReminder(reservation);
        
        return reservation;
    }
    
    // Waitlist management
    public WaitlistEntry addToWaitlist(Long restaurantId, String name, String phone, int partySize) {
        // Calculate estimated wait time
        int estimatedWait = calculateWaitTime(restaurantId, partySize);
        
        WaitlistEntry entry = new WaitlistEntry();
        entry.setRestaurantId(restaurantId);
        entry.setCustomerName(name);
        entry.setCustomerPhone(phone);
        entry.setPartySize(partySize);
        entry.setEstimatedWaitMinutes(estimatedWait);
        entry.setStatus("WAITING");
        
        waitlistRepo.save(entry);
        
        // Send SMS with wait time
        smsService.send(phone, 
            String.format("Added to waitlist. Estimated wait: %d minutes", estimatedWait)
        );
        
        return entry;
    }
    
    private int calculateWaitTime(Long restaurantId, int partySize) {
        // Get current occupied tables
        int occupiedCount = tableAssignmentRepo.countByRestaurantIdAndStatus(restaurantId, "ACTIVE");
        
        // Get average table turn time
        Restaurant restaurant = restaurantRepo.findById(restaurantId);
        int avgTurnTime = restaurant.getAvgTableTurnTime();
        
        // Calculate based on capacity
        int totalCapacity = restaurant.getCapacity();
        double occupancyRate = (double) occupiedCount / totalCapacity;
        
        if (occupancyRate < 0.5) {
            return 10; // Low occupancy
        } else if (occupancyRate < 0.8) {
            return avgTurnTime / 2;
        } else {
            return avgTurnTime;
        }
    }
}
```

---

### 3. Order Management Service

**Responsibilities**:
- Create orders (dine-in, takeout, delivery)
- Manage order lifecycle
- Handle order modifications
- Link orders to tables

**Database Schema**:
```sql
CREATE TABLE orders (
    order_id BIGSERIAL PRIMARY KEY,
    restaurant_id BIGINT REFERENCES restaurants(restaurant_id),
    order_number VARCHAR(20) UNIQUE NOT NULL, -- Display number (e.g., #145)
    order_type VARCHAR(20) NOT NULL, -- DINE_IN, TAKEOUT, DELIVERY
    table_id BIGINT REFERENCES tables(table_id),
    customer_name VARCHAR(200),
    customer_phone VARCHAR(20),
    server_id BIGINT REFERENCES staff(staff_id),
    status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, PREPARING, READY, SERVED, COMPLETED, CANCELLED
    subtotal DECIMAL(10, 2) NOT NULL,
    tax DECIMAL(10, 2) NOT NULL,
    tip DECIMAL(10, 2) DEFAULT 0.00,
    discount DECIMAL(10, 2) DEFAULT 0.00,
    total DECIMAL(10, 2) NOT NULL,
    payment_status VARCHAR(20) DEFAULT 'UNPAID', -- UNPAID, PAID, REFUNDED
    special_instructions TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    INDEX idx_restaurant_created (restaurant_id, created_at DESC),
    INDEX idx_table_status (table_id, status)
);

CREATE TABLE order_items (
    order_item_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT REFERENCES orders(order_id),
    menu_item_id BIGINT REFERENCES menu_items(menu_item_id),
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(10, 2) NOT NULL,
    total_price DECIMAL(10, 2) NOT NULL,
    special_instructions TEXT,
    status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, PREPARING, READY, SERVED
    sent_to_kitchen_at TIMESTAMP,
    prepared_at TIMESTAMP,
    served_at TIMESTAMP,
    modifiers JSONB, -- [{modifier_id, name, price}]
    INDEX idx_order (order_id),
    INDEX idx_status (status)
);
```

**Order Creation Flow**:
```java
@Service
public class OrderService {
    
    @Transactional
    public Order createOrder(OrderRequest request) {
        // 1. Validate table (if dine-in)
        if (request.getOrderType().equals("DINE_IN")) {
            Table table = tableService.getTable(request.getTableId());
            if (!table.getStatus().equals("OCCUPIED")) {
                // Mark table as occupied
                tableService.updateStatus(request.getTableId(), "OCCUPIED");
            }
        }
        
        // 2. Create order
        Order order = new Order();
        order.setRestaurantId(request.getRestaurantId());
        order.setOrderNumber(generateOrderNumber(request.getRestaurantId()));
        order.setOrderType(request.getOrderType());
        order.setTableId(request.getTableId());
        order.setServerId(request.getServerId());
        order.setStatus("PENDING");
        
        BigDecimal subtotal = BigDecimal.ZERO;
        
        // 3. Add order items
        for (OrderItemRequest itemReq : request.getItems()) {
            MenuItem menuItem = menuService.getMenuItem(itemReq.getMenuItemId());
            
            OrderItem orderItem = new OrderItem();
            orderItem.setMenuItemId(menuItem.getMenuItemId());
            orderItem.setQuantity(itemReq.getQuantity());
            orderItem.setUnitPrice(menuItem.getPrice());
            
            // Calculate total with modifiers
            BigDecimal itemTotal = menuItem.getPrice().multiply(new BigDecimal(itemReq.getQuantity()));
            for (Modifier modifier : itemReq.getModifiers()) {
                itemTotal = itemTotal.add(modifier.getPrice().multiply(new BigDecimal(itemReq.getQuantity())));
            }
            
            orderItem.setTotalPrice(itemTotal);
            orderItem.setModifiers(itemReq.getModifiers());
            orderItem.setSpecialInstructions(itemReq.getSpecialInstructions());
            orderItem.setStatus("PENDING");
            
            order.addItem(orderItem);
            subtotal = subtotal.add(itemTotal);
        }
        
        // 4. Calculate totals
        order.setSubtotal(subtotal);
        order.setTax(calculateTax(subtotal, request.getRestaurantId()));
        order.setTotal(order.getSubtotal().add(order.getTax()).subtract(order.getDiscount()));
        
        orderRepo.save(order);
        
        // 5. Send to kitchen (publish event)
        kafkaProducer.send("kitchen-orders", new KitchenOrderEvent(order));
        
        // 6. Update inventory (deduct ingredients)
        inventoryService.deductIngredients(order);
        
        return order;
    }
    
    @Transactional
    public Order updateOrderStatus(Long orderId, String newStatus) {
        Order order = orderRepo.findById(orderId);
        order.setStatus(newStatus);
        orderRepo.save(order);
        
        // Publish event for KDS
        kafkaProducer.send("order-status-updates", new OrderStatusEvent(order));
        
        // If completed, clear table
        if (newStatus.equals("COMPLETED") && order.getTableId() != null) {
            tableService.updateStatus(order.getTableId(), "CLEANING");
        }
        
        return order;
    }
    
    private String generateOrderNumber(Long restaurantId) {
        // Format: R{restaurantId}-{counter}
        int counter = orderRepo.countTodayOrders(restaurantId) + 1;
        return String.format("R%d-%03d", restaurantId, counter);
    }
}
```

---

### 4. Kitchen Display System (KDS)

**Responsibilities**:
- Display orders to kitchen staff
- Track preparation status
- Order priority/timing
- Route orders to different stations (grill, cold, dessert)

**Real-time Updates** (WebSocket):
```java
@Service
public class KitchenService {
    
    @Autowired
    private SimpMessagingTemplate websocket;
    
    @KafkaListener(topics = "kitchen-orders")
    public void handleNewOrder(KitchenOrderEvent event) {
        Order order = event.getOrder();
        
        // Route items to stations
        Map<String, List<OrderItem>> stationOrders = routeToStations(order);
        
        for (Map.Entry<String, List<OrderItem>> entry : stationOrders.entrySet()) {
            String station = entry.getKey();
            List<OrderItem> items = entry.getValue();
            
            // Send to specific kitchen station
            websocket.convertAndSend(
                "/topic/kitchen/" + order.getRestaurantId() + "/" + station,
                new KitchenDisplayOrder(order, items)
            );
        }
    }
    
    private Map<String, List<OrderItem>> routeToStations(Order order) {
        Map<String, List<OrderItem>> stationOrders = new HashMap<>();
        
        for (OrderItem item : order.getItems()) {
            MenuItem menuItem = menuService.getMenuItem(item.getMenuItemId());
            String station = menuItem.getKitchenStation(); // GRILL, SALAD, DESSERT, BAR
            
            stationOrders.computeIfAbsent(station, k -> new ArrayList<>()).add(item);
        }
        
        return stationOrders;
    }
    
    public void markItemReady(Long orderItemId) {
        OrderItem item = orderItemRepo.findById(orderItemId);
        item.setStatus("READY");
        item.setPreparedAt(Instant.now());
        orderItemRepo.save(item);
        
        // Check if all items ready
        Order order = item.getOrder();
        boolean allReady = order.getItems().stream()
            .allMatch(i -> i.getStatus().equals("READY"));
        
        if (allReady) {
            // Notify server
            websocket.convertAndSend(
                "/topic/server/" + order.getServerId(),
                new OrderReadyNotification(order.getOrderId(), order.getTableId())
            );
            
            // Optionally ring bell or display on expo screen
            websocket.convertAndSend(
                "/topic/expo/" + order.getRestaurantId(),
                new ExpoNotification(order)
            );
        }
    }
}
```

**KDS UI** (kitchen screen shows):
```
┌────────────────────────────────────────────────────────┐
│  GRILL STATION                          12:45 PM       │
├────────────────────────────────────────────────────────┤
│  Order #145 | Table 12 | 5 mins ago | [URGENT]        │
│  • Burger (Medium Rare) x2                             │
│    - No onions                                         │
│  • Steak (Well Done) x1                                │
│                                    [MARK READY]        │
├────────────────────────────────────────────────────────┤
│  Order #146 | Table 8 | 2 mins ago                     │
│  • Grilled Chicken x1                                  │
│  • Salmon x1                                           │
│                                    [MARK READY]        │
└────────────────────────────────────────────────────────┘
```

---

### 5. Payment Service

**Responsibilities**:
- Process payments (card, cash, mobile wallets)
- Split bills
- Handle tips
- Generate receipts

**Database Schema**:
```sql
CREATE TABLE payments (
    payment_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT REFERENCES orders(order_id),
    payment_method VARCHAR(20), -- CASH, CARD, MOBILE_WALLET, GIFT_CARD
    amount DECIMAL(10, 2) NOT NULL,
    tip_amount DECIMAL(10, 2) DEFAULT 0.00,
    total_amount DECIMAL(10, 2) NOT NULL,
    payment_status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, COMPLETED, FAILED, REFUNDED
    card_last4 VARCHAR(4),
    transaction_id VARCHAR(100),
    processed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_order (order_id)
);

CREATE TABLE bill_splits (
    split_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT REFERENCES orders(order_id),
    split_type VARCHAR(20), -- EVEN, BY_ITEM, CUSTOM
    splits JSONB, -- [{person: 1, items: [1,2], amount: 25.50}]
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Implementation**:
```java
@Service
public class PaymentService {
    
    @Transactional
    public PaymentResponse processPayment(PaymentRequest request) {
        Order order = orderService.getOrder(request.getOrderId());
        
        if (order.getPaymentStatus().equals("PAID")) {
            throw new OrderAlreadyPaidException();
        }
        
        Payment payment = new Payment();
        payment.setOrderId(order.getOrderId());
        payment.setPaymentMethod(request.getPaymentMethod());
        payment.setAmount(order.getTotal());
        payment.setTipAmount(request.getTipAmount());
        payment.setTotalAmount(order.getTotal().add(request.getTipAmount()));
        
        if (request.getPaymentMethod().equals("CARD")) {
            // Process card payment (Stripe/Square)
            StripePaymentResponse stripeResponse = stripeClient.charge(
                request.getCardToken(),
                payment.getTotalAmount()
            );
            
            payment.setTransactionId(stripeResponse.getTransactionId());
            payment.setCardLast4(stripeResponse.getLast4());
            payment.setPaymentStatus("COMPLETED");
        } else if (request.getPaymentMethod().equals("CASH")) {
            payment.setPaymentStatus("COMPLETED");
        }
        
        payment.setProcessedAt(Instant.now());
        paymentRepo.save(payment);
        
        // Update order
        order.setPaymentStatus("PAID");
        order.setTip(request.getTipAmount());
        order.setCompletedAt(Instant.now());
        orderRepo.save(order);
        
        // Distribute tips to staff
        tipDistributionService.distributeTip(order, request.getTipAmount());
        
        // Generate receipt
        Receipt receipt = receiptService.generateReceipt(order, payment);
        
        return new PaymentResponse(payment.getPaymentId(), "SUCCESS", receipt);
    }
    
    // Split bill
    public SplitBillResponse splitBill(Long orderId, SplitBillRequest request) {
        Order order = orderService.getOrder(orderId);
        
        List<PaymentSplit> splits = new ArrayList<>();
        
        if (request.getSplitType().equals("EVEN")) {
            // Split evenly among N people
            int numPeople = request.getNumPeople();
            BigDecimal amountPerPerson = order.getTotal()
                .divide(new BigDecimal(numPeople), 2, RoundingMode.HALF_UP);
            
            for (int i = 0; i < numPeople; i++) {
                splits.add(new PaymentSplit(i + 1, amountPerPerson));
            }
            
        } else if (request.getSplitType().equals("BY_ITEM")) {
            // Assign specific items to each person
            Map<Integer, List<Long>> personItems = request.getPersonItems();
            
            for (Map.Entry<Integer, List<Long>> entry : personItems.entrySet()) {
                int person = entry.getKey();
                List<Long> itemIds = entry.getValue();
                
                BigDecimal personTotal = order.getItems().stream()
                    .filter(item -> itemIds.contains(item.getOrderItemId()))
                    .map(OrderItem::getTotalPrice)
                    .reduce(BigDecimal.ZERO, BigDecimal::add);
                
                // Add proportional tax/tip
                BigDecimal proportion = personTotal.divide(order.getSubtotal(), 4, RoundingMode.HALF_UP);
                BigDecimal personTax = order.getTax().multiply(proportion);
                
                splits.add(new PaymentSplit(person, personTotal.add(personTax)));
            }
        }
        
        // Save split configuration
        BillSplit billSplit = new BillSplit();
        billSplit.setOrderId(orderId);
        billSplit.setSplitType(request.getSplitType());
        billSplit.setSplits(splits);
        billSplitRepo.save(billSplit);
        
        return new SplitBillResponse(splits);
    }
}
```

---

### 6. Inventory Management Service

**Responsibilities**:
- Track ingredient stock levels
- Alert on low stock
- Supplier order management
- Recipe costing

**Database Schema**:
```sql
CREATE TABLE ingredients (
    ingredient_id BIGSERIAL PRIMARY KEY,
    restaurant_id BIGINT REFERENCES restaurants(restaurant_id),
    name VARCHAR(200) NOT NULL,
    unit VARCHAR(20), -- kg, liters, pieces
    quantity_on_hand DECIMAL(10, 2) DEFAULT 0,
    reorder_level DECIMAL(10, 2) DEFAULT 10,
    unit_cost DECIMAL(10, 2),
    supplier VARCHAR(200),
    last_ordered_at TIMESTAMP,
    INDEX idx_restaurant (restaurant_id)
);

CREATE TABLE recipes (
    recipe_id BIGSERIAL PRIMARY KEY,
    menu_item_id BIGINT REFERENCES menu_items(menu_item_id),
    ingredient_id BIGINT REFERENCES ingredients(ingredient_id),
    quantity_required DECIMAL(10, 2) NOT NULL,
    unit VARCHAR(20)
);

CREATE TABLE inventory_transactions (
    transaction_id BIGSERIAL PRIMARY KEY,
    restaurant_id BIGINT REFERENCES restaurants(restaurant_id),
    ingredient_id BIGINT REFERENCES ingredients(ingredient_id),
    transaction_type VARCHAR(20), -- PURCHASE, USAGE, WASTE, ADJUSTMENT
    quantity DECIMAL(10, 2) NOT NULL,
    unit_cost DECIMAL(10, 2),
    reference_id BIGINT, -- order_id or purchase_order_id
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Implementation**:
```java
@Service
public class InventoryService {
    
    @Transactional
    public void deductIngredients(Order order) {
        for (OrderItem item : order.getItems()) {
            // Get recipe for menu item
            List<Recipe> recipes = recipeRepo.findByMenuItemId(item.getMenuItemId());
            
            for (Recipe recipe : recipes) {
                Ingredient ingredient = ingredientRepo.findById(recipe.getIngredientId());
                
                // Calculate quantity needed
                BigDecimal qtyNeeded = recipe.getQuantityRequired()
                    .multiply(new BigDecimal(item.getQuantity()));
                
                // Deduct from stock
                if (ingredient.getQuantityOnHand().compareTo(qtyNeeded) < 0) {
                    // Low stock warning
                    notificationService.sendLowStockAlert(ingredient);
                }
                
                ingredient.setQuantityOnHand(
                    ingredient.getQuantityOnHand().subtract(qtyNeeded)
                );
                ingredientRepo.save(ingredient);
                
                // Log transaction
                InventoryTransaction transaction = new InventoryTransaction();
                transaction.setRestaurantId(order.getRestaurantId());
                transaction.setIngredientId(ingredient.getIngredientId());
                transaction.setTransactionType("USAGE");
                transaction.setQuantity(qtyNeeded);
                transaction.setReferenceId(order.getOrderId());
                inventoryTransactionRepo.save(transaction);
            }
        }
    }
    
    @Scheduled(cron = "0 0 8 * * *") // Daily at 8 AM
    public void checkLowStock() {
        List<Ingredient> lowStockItems = ingredientRepo.findByQuantityOnHandLessThan("reorder_level");
        
        for (Ingredient ingredient : lowStockItems) {
            // Send alert to manager
            notificationService.sendLowStockAlert(ingredient);
            
            // Auto-create purchase order (if enabled)
            if (ingredient.isAutoReorderEnabled()) {
                createPurchaseOrder(ingredient);
            }
        }
    }
}
```

---

### 7. Staff Management Service

**Database Schema**:
```sql
CREATE TABLE staff (
    staff_id BIGSERIAL PRIMARY KEY,
    restaurant_id BIGINT REFERENCES restaurants(restaurant_id),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(20),
    role VARCHAR(20), -- MANAGER, SERVER, COOK, HOST, BARTENDER
    hourly_rate DECIMAL(10, 2),
    hire_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE shifts (
    shift_id BIGSERIAL PRIMARY KEY,
    restaurant_id BIGINT REFERENCES restaurants(restaurant_id),
    staff_id BIGINT REFERENCES staff(staff_id),
    shift_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    clock_in_time TIMESTAMP,
    clock_out_time TIMESTAMP,
    break_minutes INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'SCHEDULED', -- SCHEDULED, CLOCKED_IN, CLOCKED_OUT, ABSENT
    INDEX idx_staff_date (staff_id, shift_date)
);

CREATE TABLE tips (
    tip_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT REFERENCES orders(order_id),
    staff_id BIGINT REFERENCES staff(staff_id),
    amount DECIMAL(10, 2) NOT NULL,
    tip_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### 8. Analytics & Reporting Service

**Key Metrics**:
- Daily/weekly/monthly sales
- Top-selling items
- Average check size
- Table turnover rate
- Server performance
- Peak hours
- Food cost percentage

**Reports**:
```java
@Service
public class ReportingService {
    
    public SalesReport generateDailySalesReport(Long restaurantId, LocalDate date) {
        List<Order> orders = orderRepo.findByRestaurantIdAndDateBetween(
            restaurantId, 
            date.atStartOfDay(), 
            date.plusDays(1).atStartOfDay()
        );
        
        BigDecimal totalSales = orders.stream()
            .map(Order::getTotal)
            .reduce(BigDecimal.ZERO, BigDecimal::add);
        
        BigDecimal totalTips = orders.stream()
            .map(Order::getTip)
            .reduce(BigDecimal.ZERO, BigDecimal::add);
        
        int orderCount = orders.size();
        BigDecimal avgCheck = orderCount > 0 
            ? totalSales.divide(new BigDecimal(orderCount), 2, RoundingMode.HALF_UP)
            : BigDecimal.ZERO;
        
        // Top selling items
        Map<String, Long> itemCounts = orders.stream()
            .flatMap(order -> order.getItems().stream())
            .collect(Collectors.groupingBy(
                item -> menuService.getMenuItem(item.getMenuItemId()).getName(),
                Collectors.counting()
            ));
        
        List<TopItem> topItems = itemCounts.entrySet().stream()
            .sorted((e1, e2) -> e2.getValue().compareTo(e1.getValue()))
            .limit(10)
            .map(e -> new TopItem(e.getKey(), e.getValue()))
            .collect(Collectors.toList());
        
        return new SalesReport(
            date,
            totalSales,
            totalTips,
            orderCount,
            avgCheck,
            topItems
        );
    }
}
```

---

## Offline-First Architecture

**Challenge**: Restaurant POS must work even when internet is down

**Solution**: Local-first with sync

```java
// Local SQLite database on POS tablet
public class OfflineOrderService {
    
    private SQLiteDatabase localDb;
    private SyncService syncService;
    
    public Order createOrderOffline(OrderRequest request) {
        // 1. Save to local database
        Order order = buildOrder(request);
        order.setSyncStatus("PENDING");
        localDb.insert("orders", order);
        
        // 2. Try to sync immediately
        if (isOnline()) {
            syncService.syncOrder(order);
        }
        
        return order;
    }
    
    @Scheduled(fixedRate = 30000) // Every 30 seconds
    public void syncPendingOrders() {
        if (isOnline()) {
            List<Order> pendingOrders = localDb.query("orders WHERE sync_status = 'PENDING'");
            
            for (Order order : pendingOrders) {
                try {
                    // Sync to server
                    apiClient.createOrder(order);
                    
                    // Mark as synced
                    order.setSyncStatus("SYNCED");
                    localDb.update("orders", order);
                } catch (Exception e) {
                    // Will retry next sync
                    log.error("Sync failed: {}", e.getMessage());
                }
            }
        }
    }
}
```

---

## Technology Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **Backend** | Java/Spring Boot | Enterprise-grade, mature |
| **POS Client** | Electron + React | Cross-platform desktop app |
| **Mobile** | React Native | Cross-platform mobile |
| **Database** | PostgreSQL | ACID, relational data |
| **Local DB** | SQLite | Offline storage on POS |
| **Cache** | Redis | Session, real-time data |
| **Message Queue** | Kafka | Event streaming |
| **Payments** | Stripe/Square | POS integration |
| **Monitoring** | Prometheus + Grafana | Metrics |

---

## Interview Q&A

### Q1: How do you handle table turnover optimization?
**Answer**:
- Track historical turn times per table size
- Predict busy periods
- Suggest table combinations (merge/split)
- Alert staff when tables are idle too long

### Q2: How do you prevent order loss when offline?
**Answer**:
- Local SQLite database on POS
- Queue orders for sync
- Retry with exponential backoff
- Manual conflict resolution UI

### Q3: How do you handle split bills?
**Answer**:
- Even split: Total / N people
- By item: Assign items to people
- Custom: Manual entry
- Handle proportional tax/tip

### Q4: How do you ensure food safety compliance?
**Answer**:
- Temperature logging
- Expiration date tracking
- Allergen warnings
- FIFO inventory rotation

### Q5: How do you calculate food cost percentage?
**Answer**:
```
Food Cost % = (Cost of Ingredients / Menu Price) × 100
Target: 25-35%

Track:
- Recipe costs (ingredients × unit cost)
- Wastage
- Portion sizes
```

---

**This comprehensive HLD covers a production-grade restaurant management system!**
