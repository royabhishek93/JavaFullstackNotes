# IoT-Connected Vending Machine Network - High-Level Design

## 1. System Overview

An IoT-Connected Vending Machine Network is a distributed system that manages thousands of smart vending machines across multiple locations. The system handles real-time inventory tracking, payment processing, predictive maintenance, dynamic pricing, remote monitoring, route optimization for restocking, telemetry data collection, machine health monitoring, and integration with mobile payment systems. It must scale to manage 100,000+ machines globally with high availability and low operational costs.

## 2. Requirements

### Functional Requirements
- **Product Selection**: User selects product, system checks availability
- **Payment Processing**: Cash, credit/debit cards, mobile payments (Apple Pay, Google Pay), QR codes
- **Inventory Management**: Real-time inventory tracking, low-stock alerts
- **Dispensing**: Validate payment, dispense product, verify dispensing
- **Refund Handling**: Automatic refund if product not dispensed
- **Remote Monitoring**: Real-time machine status, telemetry data
- **Dynamic Pricing**: Adjust prices based on demand, time of day, expiry
- **Maintenance Alerts**: Detect malfunctions (coin jam, temperature issues)
- **Restocking Optimization**: Route planning, inventory forecasting
- **Sales Analytics**: Track sales by product, location, time
- **Promotions**: Apply discounts, loyalty programs
- **Temperature Control**: Monitor refrigeration for perishables

### Non-Functional Requirements
- **Availability**: 99.9% uptime per machine
- **Latency**: Payment processing < 3 seconds
- **Scalability**: Support 100K+ machines globally
- **Reliability**: Offline operation capability, sync when online
- **Security**: Encrypted payments, secure firmware updates
- **Maintainability**: Remote diagnostics, OTA updates
- **Cost Efficiency**: Optimize restocking routes, reduce waste

## 3. Capacity Estimation

### Scale Assumptions
- **Total Machines**: 100,000 vending machines
- **Transactions per Day**: 5M transactions = 58 transactions/sec (peak: 500/sec)
- **Average Transaction Value**: $2.50
- **Products per Machine**: 40 SKUs
- **Telemetry Data Rate**: 1 reading per minute per machine
- **Total Telemetry**: 100K machines × 1/min = 1667 readings/sec
- **Restocking Events**: 10K events/day = 0.12 events/sec

### Storage Estimation
- **Machine Metadata**: 100K machines × 10KB = 1GB
- **Product Catalog**: 1000 products × 5KB = 5MB
- **Inventory**: 100K machines × 40 products × 200 bytes = 800MB
- **Transactions**: 5M/day × 1KB × 365 = 1.825TB/year
- **Telemetry Data**: 1667 readings/sec × 200 bytes × 86400 = 28.8GB/day = 10.5TB/year
- **Maintenance Logs**: 100K machines × 365 days × 500 bytes = 18.25GB/year
- **Total Storage** (5 years): ~65TB (with replicas: 195TB)

### Bandwidth
- **Telemetry Uplink**: 1667 readings/sec × 200 bytes = 333KB/s
- **Transaction Data**: 58 transactions/sec × 2KB = 116KB/s
- **Total Uplink**: ~500KB/s average

### Revenue
- **Daily Revenue**: 5M transactions × $2.50 = $12.5M/day
- **Annual Revenue**: $4.56 billion

## 4. System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    Edge Layer (Vending Machine)                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           Single Vending Machine                         │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │  │
│  │  │ Product  │  │ Payment  │  │  Temp    │              │  │
│  │  │ Sensors  │  │ Terminal │  │  Sensor  │              │  │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘              │  │
│  │       └─────────────┼─────────────┘                     │  │
│  │                     │                                    │  │
│  │          ┌──────────▼──────────┐                        │  │
│  │          │  Embedded Controller│                        │  │
│  │          │  (ARM Processor)    │                        │  │
│  │          │  - Local State      │                        │  │
│  │          │  - Offline Mode     │                        │  │
│  │          │  - Payment Queue    │                        │  │
│  │          └──────────┬──────────┘                        │  │
│  │                     │                                    │  │
│  │          ┌──────────▼──────────┐                        │  │
│  │          │ Dispenser Motor     │                        │  │
│  │          │ Controller          │                        │  │
│  │          └─────────────────────┘                        │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────┬───────────────────────────────────────────────────┘
             │ (4G/WiFi, MQTT)
             │
┌────────────▼───────────────────────────────────────────────────┐
│                      Cloud Platform                            │
│                                                                 │
│          ┌──────────────────────┐                              │
│          │  IoT Hub (AWS IoT)   │                              │
│          │  - Device Registry   │                              │
│          │  - Message Routing   │                              │
│          └──────────┬───────────┘                              │
│                     │                                           │
│        ┌────────────┼────────────────────┐                     │
│        │            │                    │                     │
│   ┌────▼─────┐ ┌───▼──────┐  ┌──────▼──────┐                 │
│   │ Vending  │ │ Payment  │  │  Inventory  │                 │
│   │ Machine  │ │ Service  │  │   Service   │                 │
│   │ Service  │ │          │  │             │                 │
│   └────┬─────┘ └───┬──────┘  └──────┬──────┘                 │
│        │           │                 │                         │
│        └───────────┼─────────────────┘                         │
│                    │                                           │
│        ┌───────────┼──────────────────────┐                   │
│        │           │                      │                   │
│   ┌────▼─────┐ ┌──▼────────┐  ┌──────▼──────┐               │
│   │  Route   │ │Maintenance│  │   Dynamic   │               │
│   │Optimizer │ │  Service  │  │   Pricing   │               │
│   │          │ │  (Alert)  │  │   Engine    │               │
│   └────┬─────┘ └──┬────────┘  └──────┬──────┘               │
│        │          │                   │                       │
│        └──────────┼───────────────────┘                       │
│                   │                                           │
│        ┌──────────▼──────────────────────┐                   │
│        │   Message Queue (Kafka)         │                   │
│        │  - machine.telemetry            │                   │
│        │  - transaction.completed        │                   │
│        │  - inventory.updated            │                   │
│        └──────────┬──────────────────────┘                   │
│                   │                                           │
│        ┌──────────┼────────────┐                             │
│        │          │            │                             │
│   ┌────▼────┐ ┌──▼──────┐ ┌───▼──────┐                      │
│   │Analytics│ │  Time   │ │   ML     │                      │
│   │Dashboard│ │ Series  │ │Forecasting│                     │
│   │         │ │   DB    │ │  Service │                      │
│   └─────────┘ └─────────┘ └──────────┘                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    Data Layer                                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐              │
│  │PostgreSQL  │  │  InfluxDB  │  │   Redis    │              │
│  │(Machines,  │  │(Telemetry, │  │  (Cache,   │              │
│  │ Products)  │  │ Metrics)   │  │  Sessions) │              │
│  └────────────┘  └────────────┘  └────────────┘              │
│                                                                 │
│  ┌────────────┐  ┌────────────┐                               │
│  │  MongoDB   │  │  Amazon S3 │                               │
│  │(Transactions│  │ (Firmware, │                               │
│  │   Logs)    │  │   Images)  │                               │
│  └────────────┘  └────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

## 5. Core Components

### Embedded Controller (Vending Machine)
```python
class VendingMachineController:
    """Embedded software running on vending machine"""
    
    def __init__(self, machine_id):
        self.machine_id = machine_id
        self.inventory = self.load_inventory()
        self.offline_transactions = []
        self.mqtt_client = MQTTClient()
        self.payment_terminal = PaymentTerminal()
    
    def run(self):
        """Main control loop"""
        while True:
            try:
                # Check for user interaction
                selection = self.read_user_selection()
                
                if selection:
                    self.process_transaction(selection)
                
                # Send telemetry every minute
                if time.time() % 60 == 0:
                    self.send_telemetry()
                
                # Sync offline transactions
                if self.mqtt_client.is_connected() and self.offline_transactions:
                    self.sync_offline_transactions()
                
                time.sleep(0.1)  # 10 Hz loop
                
            except Exception as e:
                logging.error(f"Error in control loop: {e}")
    
    def process_transaction(self, selection):
        """Handle product purchase"""
        
        product_slot = selection['slot']
        product = self.inventory[product_slot]
        
        # Check availability
        if product['quantity'] <= 0:
            self.display_message("PRODUCT OUT OF STOCK")
            return
        
        # Display price
        price = product['price']
        self.display_message(f"PRICE: ${price}")
        
        # Process payment
        payment_result = self.payment_terminal.process_payment(price)
        
        if payment_result['success']:
            # Dispense product
            dispense_result = self.dispense_product(product_slot)
            
            if dispense_result['success']:
                # Update inventory
                self.inventory[product_slot]['quantity'] -= 1
                
                # Record transaction
                transaction = {
                    'machine_id': self.machine_id,
                    'product_id': product['product_id'],
                    'price': price,
                    'payment_method': payment_result['method'],
                    'timestamp': datetime.now().isoformat(),
                    'status': 'COMPLETED'
                }
                
                # Send to cloud (or queue if offline)
                if self.mqtt_client.is_connected():
                    self.send_transaction(transaction)
                else:
                    self.offline_transactions.append(transaction)
                
                self.display_message("ENJOY YOUR PRODUCT!")
            else:
                # Dispense failed, refund
                self.payment_terminal.refund(payment_result['transaction_id'])
                self.display_message("DISPENSING FAILED - REFUNDED")
                
                # Alert maintenance
                self.send_alert("DISPENSE_FAILURE", product_slot)
        else:
            self.display_message("PAYMENT DECLINED")
    
    def dispense_product(self, slot):
        """Control motor to dispense product"""
        
        try:
            # Activate motor for specific slot
            self.motor_controller.dispense(slot)
            
            # Verify product dispensed (using IR sensor)
            time.sleep(2)  # Wait for product to drop
            
            if self.verify_dispense(slot):
                return {'success': True}
            else:
                return {'success': False, 'error': 'Product stuck'}
        
        except MotorException as e:
            return {'success': False, 'error': str(e)}
    
    def send_telemetry(self):
        """Send machine telemetry to cloud"""
        
        telemetry = {
            'machine_id': self.machine_id,
            'timestamp': datetime.now().isoformat(),
            'temperature': self.temperature_sensor.read(),
            'door_status': self.door_sensor.read(),
            'cash_level': self.cash_counter.get_amount(),
            'power_status': self.power_monitor.get_status(),
            'inventory_levels': {
                slot: product['quantity']
                for slot, product in self.inventory.items()
            }
        }
        
        self.mqtt_client.publish(
            topic=f"vending/telemetry/{self.machine_id}",
            payload=json.dumps(telemetry)
        )
    
    def send_alert(self, alert_type, details):
        """Send maintenance alert"""
        
        alert = {
            'machine_id': self.machine_id,
            'alert_type': alert_type,
            'details': details,
            'timestamp': datetime.now().isoformat(),
            'severity': self.get_alert_severity(alert_type)
        }
        
        self.mqtt_client.publish(
            topic=f"vending/alerts/{self.machine_id}",
            payload=json.dumps(alert)
        )
```

### Vending Machine Service
```python
class VendingMachineService:
    """Cloud service managing vending machines"""
    
    def __init__(self):
        self.db = PostgreSQL()
        self.redis = Redis()
    
    def register_machine(self, machine_data):
        """Register new vending machine"""
        
        machine = VendingMachine(
            machine_id=machine_data['machine_id'],
            location=machine_data['location'],
            model=machine_data['model'],
            capacity=machine_data['capacity'],
            payment_methods=machine_data['payment_methods'],
            installed_date=datetime.now(),
            status='ACTIVE'
        )
        
        self.db.save(machine)
        
        # Initialize inventory
        for slot_config in machine_data['slot_configuration']:
            inventory = MachineInventory(
                machine_id=machine.machine_id,
                slot_number=slot_config['slot'],
                product_id=slot_config['product_id'],
                capacity=slot_config['capacity'],
                quantity=0  # Start empty, fill during restocking
            )
            self.db.save(inventory)
        
        return machine
    
    def update_machine_status(self, machine_id, status_data):
        """Update machine status from telemetry"""
        
        # Store in Redis for real-time access
        self.redis.hset(
            f"machine_status:{machine_id}",
            mapping={
                'temperature': status_data['temperature'],
                'door_status': status_data['door_status'],
                'cash_level': status_data['cash_level'],
                'last_updated': datetime.now().isoformat()
            }
        )
        
        # Store in InfluxDB for historical analysis
        influxdb.write_point(
            measurement='machine_telemetry',
            tags={'machine_id': machine_id},
            fields=status_data,
            time=datetime.now()
        )
        
        # Check for issues
        self.check_machine_health(machine_id, status_data)
    
    def check_machine_health(self, machine_id, status_data):
        """Detect potential issues"""
        
        issues = []
        
        # Temperature check (for refrigerated machines)
        if status_data['temperature'] > 10:  # °C
            issues.append({
                'type': 'TEMPERATURE_HIGH',
                'severity': 'HIGH',
                'message': f"Temperature {status_data['temperature']}°C exceeds safe limit"
            })
        
        # Cash full check
        if status_data['cash_level'] > 500:  # dollars
            issues.append({
                'type': 'CASH_FULL',
                'severity': 'MEDIUM',
                'message': f"Cash level ${status_data['cash_level']} requires collection"
            })
        
        # Door open alert
        if status_data['door_status'] == 'OPEN':
            issues.append({
                'type': 'DOOR_OPEN',
                'severity': 'HIGH',
                'message': "Machine door is open"
            })
        
        # Create maintenance tickets
        for issue in issues:
            maintenance_service.create_ticket(machine_id, issue)
```

### Payment Service
```python
class PaymentService:
    """Handle payment processing"""
    
    def __init__(self):
        self.stripe = StripeClient()
        self.redis = Redis()
    
    def process_payment(self, payment_data):
        """Process payment transaction"""
        
        payment_method = payment_data['payment_method']
        amount = payment_data['amount']
        machine_id = payment_data['machine_id']
        
        try:
            if payment_method == 'CASH':
                # Cash handled by machine, just record
                transaction = self.record_cash_transaction(payment_data)
            
            elif payment_method in ['CARD', 'CONTACTLESS']:
                # Process card payment via Stripe
                charge = self.stripe.charges.create(
                    amount=int(amount * 100),  # cents
                    currency='usd',
                    source=payment_data['token'],
                    description=f"Vending machine {machine_id}"
                )
                
                transaction = self.record_card_transaction(payment_data, charge)
            
            elif payment_method == 'MOBILE':
                # Mobile payment (Apple Pay, Google Pay)
                transaction = self.process_mobile_payment(payment_data)
            
            elif payment_method == 'QR_CODE':
                # QR code payment (WeChat Pay, Alipay)
                transaction = self.process_qr_payment(payment_data)
            
            # Update machine revenue
            self.update_revenue(machine_id, amount)
            
            return {
                'success': True,
                'transaction_id': transaction.id
            }
        
        except PaymentException as e:
            logging.error(f"Payment failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_refund(self, transaction_id):
        """Issue refund for failed dispense"""
        
        transaction = self.db.query(
            "SELECT * FROM transactions WHERE transaction_id = ?",
            transaction_id
        ).first()
        
        if transaction.payment_method == 'CARD':
            # Refund via Stripe
            self.stripe.refunds.create(charge=transaction.payment_gateway_id)
        
        elif transaction.payment_method == 'MOBILE':
            # Refund via mobile payment provider
            self.mobile_payment_client.refund(transaction.payment_gateway_id)
        
        # Update transaction status
        transaction.status = 'REFUNDED'
        transaction.refunded_at = datetime.now()
        self.db.save(transaction)
```

### Inventory Service
```python
class InventoryService:
    """Manage inventory across all machines"""
    
    def __init__(self):
        self.db = PostgreSQL()
        self.redis = Redis()
    
    def update_inventory(self, machine_id, slot, quantity_change):
        """Update inventory after transaction or restocking"""
        
        with self.db.transaction():
            inventory = self.db.query("""
                SELECT * FROM machine_inventory
                WHERE machine_id = ? AND slot_number = ?
                FOR UPDATE
            """, machine_id, slot).first()
            
            inventory.quantity += quantity_change
            inventory.last_updated = datetime.now()
            
            self.db.save(inventory)
            
            # Check if low stock
            if inventory.quantity <= LOW_STOCK_THRESHOLD:
                self.create_restocking_alert(machine_id, slot, inventory.quantity)
            
            # Invalidate cache
            self.redis.delete(f"inventory:{machine_id}")
    
    def get_machine_inventory(self, machine_id):
        """Get current inventory for a machine"""
        
        # Check cache
        cached = self.redis.get(f"inventory:{machine_id}")
        if cached:
            return json.loads(cached)
        
        # Query database
        inventory = self.db.query("""
            SELECT mi.slot_number, p.name, p.price, mi.quantity, mi.capacity
            FROM machine_inventory mi
            JOIN products p ON mi.product_id = p.product_id
            WHERE mi.machine_id = ?
        """, machine_id).all()
        
        # Cache for 5 minutes
        self.redis.setex(f"inventory:{machine_id}", 300, json.dumps(inventory))
        
        return inventory
    
    def create_restocking_alert(self, machine_id, slot, quantity):
        """Alert for low stock"""
        
        alert = RestockingAlert(
            machine_id=machine_id,
            slot=slot,
            current_quantity=quantity,
            priority=self.calculate_priority(machine_id, slot),
            created_at=datetime.now(),
            status='PENDING'
        )
        
        self.db.save(alert)
        
        # Notify route optimization service
        kafka.send('inventory.low_stock', {
            'machine_id': machine_id,
            'slot': slot,
            'quantity': quantity
        })
```

### Route Optimization Service
```python
class RouteOptimizationService:
    """Optimize restocking routes"""
    
    def generate_restocking_routes(self):
        """Generate optimal routes for restocking trucks"""
        
        # Get all machines needing restocking
        machines_needing_restock = self.get_machines_needing_restock()
        
        # Cluster machines by geographic location
        clusters = self.cluster_by_location(machines_needing_restock)
        
        # For each cluster, solve TSP (Traveling Salesman Problem)
        routes = []
        for cluster in clusters:
            route = self.solve_tsp(cluster)
            routes.append(route)
        
        return routes
    
    def solve_tsp(self, machines):
        """Solve TSP using genetic algorithm"""
        
        # Get distance matrix
        distances = self.calculate_distance_matrix(machines)
        
        # Use OR-Tools for optimization
        from ortools.constraint_solver import routing_enums_pb2
        from ortools.constraint_solver import pywrapcp
        
        manager = pywrapcp.RoutingIndexManager(
            len(machines),
            1,  # number of vehicles
            0   # depot index
        )
        
        routing = pywrapcp.RoutingModel(manager)
        
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return distances[from_node][to_node]
        
        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        # Solve
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        
        solution = routing.SolveWithParameters(search_parameters)
        
        # Extract route
        route = []
        index = routing.Start(0)
        while not routing.IsEnd(index):
            route.append(machines[manager.IndexToNode(index)])
            index = solution.Value(routing.NextVar(index))
        
        return route
```

### Dynamic Pricing Engine
```python
class DynamicPricingEngine:
    """Adjust prices based on demand, time, expiry"""
    
    def calculate_price(self, machine_id, product_id):
        """Calculate dynamic price"""
        
        base_price = self.get_base_price(product_id)
        
        # Time-based pricing (surge pricing)
        time_multiplier = self.get_time_multiplier()
        
        # Demand-based pricing
        demand_multiplier = self.get_demand_multiplier(machine_id, product_id)
        
        # Expiry-based discount (for perishables)
        expiry_discount = self.get_expiry_discount(machine_id, product_id)
        
        # Calculate final price
        price = base_price * time_multiplier * demand_multiplier * (1 - expiry_discount)
        
        # Round to nearest $0.05
        price = round(price * 20) / 20
        
        return price
    
    def get_time_multiplier(self):
        """Surge pricing during peak hours"""
        
        hour = datetime.now().hour
        
        if 7 <= hour <= 9 or 12 <= hour <= 13:
            # Peak hours
            return 1.2
        elif 22 <= hour or hour <= 6:
            # Off-peak hours
            return 0.9
        else:
            return 1.0
```

## 6. Database Design

```sql
-- Vending Machines Table
CREATE TABLE vending_machines (
    machine_id VARCHAR(50) PRIMARY KEY,
    location VARCHAR(255),
    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),
    model VARCHAR(100),
    capacity INT,
    payment_methods TEXT[],
    installed_date DATE,
    last_maintenance DATE,
    status VARCHAR(20), -- ACTIVE, OFFLINE, MAINTENANCE
    INDEX idx_location (latitude, longitude)
);

-- Products Table
CREATE TABLE products (
    product_id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255),
    category VARCHAR(100),
    base_price DECIMAL(5,2),
    perishable BOOLEAN DEFAULT FALSE,
    shelf_life_days INT,
    image_url VARCHAR(500)
);

-- Machine Inventory Table
CREATE TABLE machine_inventory (
    machine_id VARCHAR(50) REFERENCES vending_machines(machine_id),
    slot_number INT,
    product_id BIGINT REFERENCES products(product_id),
    quantity INT,
    capacity INT,
    last_restocked TIMESTAMP,
    last_updated TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (machine_id, slot_number),
    INDEX idx_machine (machine_id)
);

-- Transactions Table (MongoDB)
{
  "_id": ObjectId,
  "machine_id": "VM001",
  "product_id": 123,
  "price": 2.50,
  "payment_method": "CARD",
  "payment_gateway_id": "ch_...",
  "timestamp": ISODate,
  "status": "COMPLETED"
}

-- Telemetry Data (InfluxDB)
measurement: machine_telemetry
tags: machine_id, location
fields: temperature, cash_level, power_voltage
time: timestamp
```

## 7. API Design

### Get Machine Status
```http
GET /api/v1/machines/{machine_id}/status
Authorization: Bearer <token>

Response: 200 OK
{
  "machine_id": "VM001",
  "status": "ACTIVE",
  "temperature": 4.5,
  "cash_level": 245.50,
  "inventory_status": "OK",
  "last_updated": "2026-04-07T10:00:00Z"
}
```

### Process Transaction
```http
POST /api/v1/transactions
Authorization: Bearer <token>

{
  "machine_id": "VM001",
  "product_id": 123,
  "payment_method": "CARD",
  "payment_token": "tok_..."
}

Response: 200 OK
{
  "transaction_id": "txn_123",
  "status": "COMPLETED",
  "amount": 2.50
}
```

## 8. Scalability Strategy

- **Edge Computing**: Process transactions locally
- **MQTT**: Lightweight IoT protocol
- **Time-Series DB**: InfluxDB for telemetry
- **Caching**: Redis for real-time status
- **ML**: Predictive maintenance, demand forecasting

## 9. Technology Stack

| Component | Technology |
|-----------|-----------|
| **Embedded** | C/C++, Linux |
| **Backend** | Python, Django |
| **IoT Platform** | AWS IoT Core |
| **Database** | PostgreSQL |
| **Time-Series** | InfluxDB |
| **Payment** | Stripe API |
| **Analytics** | Apache Spark |

## 10. Interview Discussion Points

### Q1: How do you handle offline payments?

**Answer**: Queue transactions locally, sync when online. Use cached product prices. Cash payments always work offline.

### Q2: How do you prevent theft and tampering?

**Answer**: Physical locks, tamper sensors, encrypted firmware, video surveillance, door open alerts.

### Q3: How do you optimize restocking?

**Answer**: Predict demand using ML, cluster machines geographically, solve TSP for optimal routes, prioritize by urgency.

### Q4: How do you handle product stuck in machine?

**Answer**: IR sensors verify dispense, auto-refund if failed, alert maintenance, log incident.

### Q5: How do you implement dynamic pricing?

**Answer**: Consider time of day, demand patterns, expiry dates, competitor prices, maximize revenue while ensuring fairness.

---

**End of Document**
