# Coffee Vending Machine (IoT Connected) - High-Level Design

## 1. System Overview

An IoT-connected coffee vending machine system manages a distributed network of smart vending machines that dispense various coffee beverages, track inventory in real-time, process cashless payments, monitor machine health, optimize supply chain logistics, and provide analytics on consumption patterns. The system must support thousands of machines globally, handle hundreds of transactions per machine daily, enable remote configuration and troubleshooting, predict maintenance needs, and ensure 99% machine uptime.

## 2. Requirements

### Functional Requirements
- **Beverage Selection**: Offer espresso, cappuccino, latte, americano, etc.
- **Payment Processing**: Accept cards, mobile wallets, QR codes
- **Inventory Management**: Track coffee beans, milk, cups, sugar in real-time
- **Recipe Management**: Customize beverage recipes remotely
- **Remote Monitoring**: Monitor machine status, temperature, pressure
- **Maintenance Alerts**: Predict and alert when maintenance needed
- **User Interface**: Touch screen with multilingual support
- **Loyalty Programs**: Integrate with customer loyalty apps
- **Usage Analytics**: Track sales, popular beverages, peak times
- **Firmware Updates**: OTA (Over-The-Air) updates

### Non-Functional Requirements
- **Availability**: 99% machine uptime
- **Latency**: Payment processing < 2s, machine response < 500ms
- **Scalability**: Support 10K+ machines globally
- **Reliability**: Zero payment loss, accurate inventory
- **Security**: Encrypted communication, secure payments
- **Connectivity**: Operate offline with sync when online

## 3. Capacity Estimation

### Scale Assumptions
- **Total Machines**: 10,000 vending machines
- **Transactions/Machine/Day**: 200 transactions = 2M total/day
- **Average Transaction**: 1 coffee = $3
- **Daily Revenue**: $6M/day
- **Telemetry Frequency**: Every 60 seconds per machine
- **Transaction Size**: 2KB
- **Telemetry Size**: 500 bytes

### Storage Estimation
- **Machine Metadata**: 10K machines × 10KB = 100MB
- **Transaction Data**: 2M/day × 2KB × 365 = 1.46TB/year
- **Telemetry Data**: 10K × 1440/day × 500B × 365 = 2.628TB/year
- **Historical Data** (3 years): ~12TB
- **Total Storage**: ~15TB (with replicas: 45TB)

### Bandwidth
- **Telemetry**: 10K machines × 500B/60s = 83.3KB/s
- **Transactions**: 2M/day / 86400s × 2KB = 46.3KB/s
- **Total Bandwidth**: ~150KB/s (peak 500KB/s)

### QPS Estimation
- **Transaction QPS**: 2M/day / 86400s = 23 TPS (peak 100 TPS)
- **Telemetry QPS**: 10K machines / 60s = 167 QPS
- **Payment Gateway QPS**: 23 TPS

## 4. System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    Coffee Vending Machine                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  Touch       │  │  Payment     │  │  Brewing     │        │
│  │  Screen UI   │  │  Terminal    │  │  Unit        │        │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘        │
│         │                 │                 │                 │
│  ┌──────▼─────────────────▼─────────────────▼──────┐         │
│  │        Embedded Controller (Raspberry Pi)        │         │
│  │  - Local Transaction Queue                       │         │
│  │  - Offline Mode Support                          │         │
│  │  - Sensor Data Collection                        │         │
│  └──────┬───────────────────────────────────────────┘         │
│         │ 4G/5G/WiFi                                          │
└─────────┼──────────────────────────────────────────────────────┘
          │
          │ MQTT over TLS
          │
┌─────────▼─────────────────────────────────────────────────────┐
│                    IoT Gateway / Edge Server                   │
│  - Message Routing                                            │
│  - Protocol Translation (MQTT → HTTP)                         │
│  - Certificate Management                                     │
│  - Load Balancing                                             │
└─────────┬─────────────────────────────────────────────────────┘
          │
          │
┌─────────▼─────────────────────────────────────────────────────┐
│                       Cloud Backend                            │
│                                                                │
│  ┌────────────┐  ┌─────────────┐  ┌──────────────┐           │
│  │   API      │  │   Device    │  │  Transaction │           │
│  │  Gateway   │  │  Management │  │   Service    │           │
│  └─────┬──────┘  └──────┬──────┘  └──────┬───────┘           │
│        │                │                 │                   │
│  ┌─────▼────────────────▼─────────────────▼──────┐            │
│  │        Message Queue (Kafka)                  │            │
│  │  Topics: transactions, telemetry, alerts      │            │
│  └─────┬────────────────┬─────────────────┬──────┘            │
│        │                │                 │                   │
│  ┌─────▼──────┐  ┌─────▼──────┐  ┌──────▼────────┐          │
│  │ Inventory  │  │  Payment   │  │  Analytics    │          │
│  │  Service   │  │  Service   │  │   Service     │          │
│  └─────┬──────┘  └─────┬──────┘  └──────┬────────┘          │
│        │                │                 │                   │
│  ┌─────▼────────────────▼─────────────────▼──────┐            │
│  │           Time-Series Database                │            │
│  │             (InfluxDB/TimescaleDB)            │            │
│  └────────────────────────────────────────────────┘            │
│                                                                │
│  ┌────────────────────────────────────────────────┐            │
│  │           PostgreSQL (Transactions, Machines)  │            │
│  └────────────────────────────────────────────────┘            │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                  External Services                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   Payment    │  │   SMS/Email  │  │   Dashboard  │        │
│  │   Gateway    │  │   Service    │  │   (Admin)    │        │
│  │  (Stripe)    │  │   (Twilio)   │  │   (Grafana)  │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└────────────────────────────────────────────────────────────────┘
```

## 5. Core Components

### Embedded Controller (Edge Device)
- **Local Processing**: Handle beverage dispensing logic locally
- **Offline Mode**: Queue transactions, sync when connectivity restored
- **Sensor Management**: Read temperature, pressure, inventory sensors
- **MQTT Client**: Publish telemetry, subscribe to commands
- **Local Cache**: Store recipes, pricing, configuration

### IoT Gateway
- **AWS IoT Core / Azure IoT Hub**: Manage device connections
- **Device Registry**: Track registered machines, certificates
- **Message Broker**: MQTT broker for pub/sub communication
- **Device Shadows**: Maintain desired vs reported state
- **Authentication**: X.509 certificates for mutual TLS

### Device Management Service
- **Provisioning**: Register new machines, issue certificates
- **Configuration**: Push recipe updates, pricing changes
- **Firmware Updates**: OTA updates with rollback capability
- **Health Monitoring**: Track machine status, uptime
- **Remote Control**: Trigger cleaning cycles, diagnostics

### Transaction Service
- **Order Processing**: Validate order, check inventory
- **Payment Integration**: Process payments via Stripe/Square
- **Receipt Generation**: Generate digital receipts
- **Idempotency**: Prevent duplicate charges
- **Reconciliation**: Daily reconciliation of transactions vs payments

### Inventory Service
- **Real-Time Tracking**: Monitor ingredient levels per machine
- **Predictive Alerts**: ML model predicts when refill needed
- **Auto-Replenishment**: Trigger supply orders automatically
- **Waste Tracking**: Monitor expired ingredients, cleaning cycles
- **Optimization**: Suggest optimal stock levels per location

### Analytics Service
- **Sales Analytics**: Revenue, popular beverages, trends
- **Machine Performance**: Uptime, transaction volume, errors
- **Customer Insights**: Peak hours, seasonal patterns
- **Anomaly Detection**: Detect unusual consumption patterns
- **Reporting**: Generate daily/weekly/monthly reports

## 6. Database Design

### Schema Design

```sql
-- Machines Table
CREATE TABLE machines (
    machine_id VARCHAR(50) PRIMARY KEY,
    machine_name VARCHAR(100),
    location VARCHAR(255),
    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),
    installation_date DATE,
    model VARCHAR(50),
    firmware_version VARCHAR(20),
    status VARCHAR(20) DEFAULT 'ONLINE', -- ONLINE, OFFLINE, MAINTENANCE, ERROR
    last_seen TIMESTAMP,
    owner_id INT,
    INDEX idx_status (status),
    INDEX idx_location (latitude, longitude)
);

-- Machine Configuration Table
CREATE TABLE machine_config (
    config_id SERIAL PRIMARY KEY,
    machine_id VARCHAR(50) REFERENCES machines(machine_id),
    recipes JSONB, -- {"espresso": {"beans": 18, "water": 30, "time": 25}}
    prices JSONB, -- {"espresso": 2.50, "cappuccino": 3.50}
    settings JSONB, -- {"temperature": 93, "pressure": 9}
    updated_at TIMESTAMP DEFAULT NOW(),
    version INT DEFAULT 1
);

-- Transactions Table (Partitioned by date)
CREATE TABLE transactions (
    transaction_id BIGSERIAL,
    machine_id VARCHAR(50) REFERENCES machines(machine_id),
    beverage_type VARCHAR(50),
    quantity INT DEFAULT 1,
    amount DECIMAL(10,2),
    currency CHAR(3) DEFAULT 'USD',
    payment_method VARCHAR(50), -- CARD, MOBILE_WALLET, QR_CODE
    payment_status VARCHAR(20), -- SUCCESS, FAILED, PENDING
    transaction_token VARCHAR(100),
    transaction_date TIMESTAMP DEFAULT NOW(),
    idempotency_key VARCHAR(100) UNIQUE,
    PRIMARY KEY (transaction_id, transaction_date),
    INDEX idx_machine_date (machine_id, transaction_date),
    INDEX idx_status (payment_status)
) PARTITION BY RANGE (transaction_date);

-- Create partitions
CREATE TABLE transactions_2026_04 PARTITION OF transactions
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

-- Inventory Table
CREATE TABLE inventory (
    inventory_id SERIAL PRIMARY KEY,
    machine_id VARCHAR(50) REFERENCES machines(machine_id),
    ingredient VARCHAR(50), -- COFFEE_BEANS, MILK, SUGAR, CUPS
    current_level INT, -- in grams or units
    capacity INT,
    unit VARCHAR(20), -- GRAMS, LITERS, UNITS
    last_refill_date TIMESTAMP,
    low_threshold INT, -- Alert when level drops below
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(machine_id, ingredient),
    INDEX idx_machine (machine_id),
    INDEX idx_low_stock (machine_id, current_level)
);

-- Alerts Table
CREATE TABLE alerts (
    alert_id BIGSERIAL PRIMARY KEY,
    machine_id VARCHAR(50) REFERENCES machines(machine_id),
    alert_type VARCHAR(50), -- LOW_INVENTORY, MAINTENANCE_DUE, ERROR, CONNECTIVITY
    severity VARCHAR(20), -- INFO, WARNING, CRITICAL
    message TEXT,
    resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    INDEX idx_machine_unresolved (machine_id, resolved, created_at)
);

-- Maintenance Records Table
CREATE TABLE maintenance_records (
    maintenance_id SERIAL PRIMARY KEY,
    machine_id VARCHAR(50) REFERENCES machines(machine_id),
    maintenance_type VARCHAR(50), -- CLEANING, DESCALING, REPAIR, REFILL
    description TEXT,
    cost DECIMAL(10,2),
    technician VARCHAR(100),
    scheduled_date TIMESTAMP,
    completed_date TIMESTAMP,
    status VARCHAR(20), -- SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED
    INDEX idx_machine (machine_id, scheduled_date)
);

-- Telemetry Data (Time-Series DB - InfluxDB)
-- Measurement: machine_telemetry
-- Tags: machine_id, location
-- Fields: temperature, pressure, water_level, bean_level, milk_level
-- Timestamp: time

-- Example InfluxDB query
SELECT mean(temperature), mean(pressure) 
FROM machine_telemetry 
WHERE machine_id = 'VM001' 
AND time > now() - 24h 
GROUP BY time(1h)
```

## 7. API Design

### Register Machine (Provisioning)
```http
POST /api/v1/machines/register
Authorization: Bearer <admin_token>

{
  "machine_id": "VM001",
  "machine_name": "Coffee Shop A - Machine 1",
  "location": "123 Main St, New York, NY",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "model": "CoffeeMaster 3000",
  "owner_id": 12345
}

Response: 201 Created
{
  "machine_id": "VM001",
  "certificate": "-----BEGIN CERTIFICATE-----...",
  "private_key": "-----BEGIN PRIVATE KEY-----...",
  "mqtt_endpoint": "mqtt://iot.coffeemachine.com:8883",
  "topics": {
    "telemetry": "machines/VM001/telemetry",
    "commands": "machines/VM001/commands"
  }
}
```

### Process Transaction
```http
POST /api/v1/transactions
Content-Type: application/json
X-Machine-ID: VM001
Idempotency-Key: <unique_key>

{
  "machine_id": "VM001",
  "beverage_type": "cappuccino",
  "quantity": 1,
  "amount": 3.50,
  "payment_method": "CARD",
  "payment_token": "tok_visa_1234"
}

Response: 200 OK
{
  "transaction_id": 987654,
  "status": "SUCCESS",
  "receipt_url": "https://receipts.coffeemachine.com/987654",
  "amount_charged": 3.50,
  "timestamp": "2026-04-07T10:15:30Z"
}
```

### Publish Telemetry (MQTT)
```json
// Topic: machines/VM001/telemetry
{
  "machine_id": "VM001",
  "timestamp": "2026-04-07T10:15:30Z",
  "temperature": 93.5,
  "pressure": 9.2,
  "water_level": 75,
  "bean_level": 1200,
  "milk_level": 2.5,
  "cup_count": 45,
  "error_code": null
}
```

### Send Command to Machine (MQTT)
```json
// Topic: machines/VM001/commands
{
  "command": "UPDATE_RECIPE",
  "recipe": "cappuccino",
  "parameters": {
    "coffee_beans": 18,
    "milk": 120,
    "foam_time": 15,
    "temperature": 65
  }
}

// Machine acknowledges
// Topic: machines/VM001/commands/ack
{
  "command_id": "cmd_123",
  "status": "SUCCESS",
  "timestamp": "2026-04-07T10:16:00Z"
}
```

### Get Machine Status
```http
GET /api/v1/machines/VM001/status
Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "machine_id": "VM001",
  "status": "ONLINE",
  "last_seen": "2026-04-07T10:15:30Z",
  "firmware_version": "2.5.1",
  "uptime_percentage": 99.2,
  "inventory": {
    "coffee_beans": 1200,
    "milk": 2.5,
    "cups": 45
  },
  "health": {
    "temperature": 93.5,
    "pressure": 9.2,
    "errors": []
  },
  "today_sales": {
    "transactions": 87,
    "revenue": 304.50
  }
}
```

### Get Analytics
```http
GET /api/v1/analytics/machines/VM001?period=7d

Response: 200 OK
{
  "machine_id": "VM001",
  "period": "7d",
  "total_revenue": 2135.00,
  "total_transactions": 609,
  "average_transaction": 3.51,
  "popular_beverages": [
    {"beverage": "cappuccino", "count": 245},
    {"beverage": "espresso", "count": 189},
    {"beverage": "latte", "count": 175}
  ],
  "peak_hours": [
    {"hour": 8, "transactions": 45},
    {"hour": 12, "transactions": 38},
    {"hour": 15, "transactions": 42}
  ],
  "uptime_percentage": 99.5
}
```

## 8. Scalability Strategy

### Horizontal Scaling
- **Stateless Services**: All backend services are stateless
- **Load Balancing**: Distribute MQTT connections across IoT Gateway cluster
- **Auto-Scaling**: Scale based on connected device count

### Database Sharding
```
Shard Key Strategy:
- Machines: Shard by machine_id hash
- Transactions: Partition by transaction_date (monthly)
- Telemetry: Time-series DB (InfluxDB) with retention policy

Retention Policies:
- Raw telemetry: 30 days
- 1-hour aggregates: 1 year
- 1-day aggregates: Forever
```

### Caching Strategy
```
Redis Cache:
- Machine configuration (1 hour TTL)
- Pricing rules (1 hour TTL)
- Inventory status (5 min TTL)
- Active alerts (no TTL, invalidate on resolve)

Edge Caching (on device):
- Recipes (sync every 6 hours)
- Pricing (sync every 6 hours)
- Offline transaction queue
```

### Message Queue (Kafka)
```
Topics:
- machine.telemetry: All sensor data (high throughput)
- machine.transactions: All transactions
- machine.alerts: Critical alerts
- machine.commands: Commands to devices

Consumers:
- Analytics Service: Process telemetry for dashboards
- Inventory Service: Update inventory on transactions
- Alert Service: Generate alerts on anomalies
```

## 9. Fault Tolerance & High Availability

### Offline Mode
```python
class OfflineTransactionQueue:
    def __init__(self):
        self.queue = []
        self.max_queue_size = 1000
    
    def add_transaction(self, transaction):
        if len(self.queue) < self.max_queue_size:
            self.queue.append(transaction)
            self.save_to_disk()
        else:
            # Queue full, reject transaction
            return {"error": "Offline queue full"}
    
    def sync_when_online(self):
        while self.queue:
            transaction = self.queue[0]
            try:
                response = api.post("/transactions", transaction)
                if response.status_code == 200:
                    self.queue.pop(0)
                    self.save_to_disk()
            except Exception as e:
                # Network still down, retry later
                break
```

### Payment Failure Handling
```python
def process_payment(transaction):
    try:
        # Step 1: Authorize payment
        payment_result = stripe.charge(
            amount=transaction.amount,
            token=transaction.payment_token
        )
        
        # Step 2: Dispense beverage
        dispense_result = brewing_unit.dispense(transaction.beverage_type)
        
        if dispense_result.success:
            # Step 3: Capture payment
            stripe.capture(payment_result.charge_id)
            return {"status": "SUCCESS"}
        else:
            # Step 4: Refund if dispense failed
            stripe.refund(payment_result.charge_id)
            return {"status": "DISPENSE_FAILED", "refunded": True}
            
    except Exception as e:
        log_error(e)
        return {"status": "PAYMENT_FAILED"}
```

### Predictive Maintenance
```python
def predict_maintenance(machine_id):
    # Fetch telemetry data
    telemetry = influx.query(f"""
        SELECT mean(temperature), stddev(temperature), 
               mean(pressure), stddev(pressure)
        FROM machine_telemetry 
        WHERE machine_id = '{machine_id}' 
        AND time > now() - 7d
        GROUP BY time(1h)
    """)
    
    # ML model predicts failure probability
    failure_prob = ml_model.predict(telemetry)
    
    if failure_prob > 0.7:
        create_alert(machine_id, "MAINTENANCE_DUE", 
                    f"Predicted failure probability: {failure_prob}")
        schedule_maintenance(machine_id)
```

### Circuit Breaker for Payment Gateway
```python
class PaymentCircuitBreaker:
    def __init__(self):
        self.failure_count = 0
        self.threshold = 5
        self.timeout = 60  # seconds
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def call_payment_gateway(self, transaction):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
            else:
                return {"error": "Payment gateway unavailable"}
        
        try:
            result = stripe.charge(transaction)
            self.failure_count = 0
            self.state = "CLOSED"
            return result
        except Exception as e:
            self.failure_count += 1
            if self.failure_count >= self.threshold:
                self.state = "OPEN"
                self.last_failure_time = time.time()
            raise
```

## 10. Technology Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **Edge Device** | Raspberry Pi 4 + Python | Cost-effective, GPIO for sensors |
| **IoT Platform** | AWS IoT Core / Azure IoT Hub | Managed MQTT broker, device registry |
| **Message Protocol** | MQTT over TLS | Lightweight, pub/sub, low bandwidth |
| **API Gateway** | Kong | Rate limiting, auth |
| **Backend** | Node.js / Go | High concurrency, low latency |
| **Primary DB** | PostgreSQL 14+ | ACID, complex queries |
| **Time-Series DB** | InfluxDB / TimescaleDB | Optimized for telemetry |
| **Cache** | Redis Cluster | Low latency, session management |
| **Message Queue** | Apache Kafka | High throughput, event streaming |
| **Payment Gateway** | Stripe / Square | PCI-compliant |
| **Monitoring** | Prometheus + Grafana | Metrics, dashboards |
| **Alerting** | PagerDuty | On-call alerts |

## 11. Interview Discussion Points

### Q1: How do you handle payment processing when the machine is offline?

**Answer**: Offline transaction queue with sync:

```python
# On device (offline mode)
def handle_offline_payment(transaction):
    # Check if we have local credit available
    if has_local_credit(transaction.payment_token):
        # Dispense beverage immediately
        dispense_beverage(transaction.beverage_type)
        
        # Queue transaction for sync
        offline_queue.append(transaction)
        
        return {"status": "SUCCESS_OFFLINE"}
    else:
        # Cannot process without connectivity
        return {"error": "Payment requires internet connection"}

# When connectivity restored
def sync_offline_transactions():
    for transaction in offline_queue:
        try:
            # Submit to backend
            response = api.post("/transactions", transaction)
            
            if response.status_code == 200:
                offline_queue.remove(transaction)
            else:
                # Failed - may need to refund if beverage was dispensed
                handle_reconciliation(transaction)
        except Exception:
            break  # Retry later
```

### Q2: How do you implement predictive inventory management?

**Answer**: ML-based forecasting with auto-replenishment:

```python
def predict_refill_date(machine_id):
    # Fetch historical consumption data
    consumption_data = db.query(f"""
        SELECT date_trunc('day', transaction_date) as day,
               beverage_type,
               COUNT(*) as count
        FROM transactions
        WHERE machine_id = '{machine_id}'
        AND transaction_date > NOW() - INTERVAL '90 days'
        GROUP BY day, beverage_type
    """)
    
    # Current inventory
    inventory = redis.get(f"inventory:{machine_id}")
    
    # ML model predicts daily consumption
    predicted_daily_consumption = ml_model.predict(
        machine_id=machine_id,
        day_of_week=today.weekday(),
        weather=get_weather(machine_location),
        historical_data=consumption_data
    )
    
    # Calculate days until refill needed
    days_until_refill = inventory['coffee_beans'] / predicted_daily_consumption
    
    if days_until_refill < 3:
        # Trigger auto-replenishment
        create_refill_order(machine_id, predicted_daily_consumption * 30)
        notify_technician(machine_id, f"Refill needed in {days_until_refill} days")
    
    return days_until_refill
```

### Q3: How do you ensure secure communication between machines and backend?

**Answer**: Mutual TLS with X.509 certificates:

```python
# Device provisioning (one-time setup)
def provision_machine(machine_id):
    # Generate unique certificate for machine
    cert, private_key = generate_certificate(machine_id)
    
    # Store certificate in device registry
    iot_registry.register_device(
        device_id=machine_id,
        certificate=cert,
        status='ACTIVE'
    )
    
    # Return credentials to machine
    return {
        "certificate": cert,
        "private_key": private_key,
        "ca_certificate": root_ca_cert,
        "mqtt_endpoint": "mqtts://iot.coffeemachine.com:8883"
    }

# Machine connects with mutual TLS
def connect_to_iot_gateway():
    mqtt_client = mqtt.Client()
    mqtt_client.tls_set(
        ca_certs="root_ca.pem",
        certfile="machine_cert.pem",
        keyfile="machine_key.pem",
        cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLSv1_2
    )
    mqtt_client.connect("iot.coffeemachine.com", 8883)
```

### Q4: How do you handle firmware updates without downtime?

**Answer**: OTA updates with rollback capability:

```python
def perform_ota_update(machine_id, firmware_version):
    # Step 1: Check machine is eligible
    machine = db.get_machine(machine_id)
    if machine.status == 'ERROR':
        return {"error": "Machine in error state"}
    
    # Step 2: Send update command
    mqtt.publish(f"machines/{machine_id}/commands", {
        "command": "FIRMWARE_UPDATE",
        "version": firmware_version,
        "download_url": f"https://firmware.coffeemachine.com/{firmware_version}.bin",
        "checksum": calculate_checksum(firmware_version)
    })
    
    # Step 3: Machine downloads firmware in background
    # Step 4: Machine updates during idle time (2 AM)
    # Step 5: Machine reboots and verifies update
    # Step 6: If verification fails, rollback to previous version
    
    # Monitor update status
    def check_update_status():
        status = redis.get(f"update_status:{machine_id}")
        if status == 'COMPLETED':
            db.update_machine(machine_id, firmware_version=firmware_version)
        elif status == 'FAILED':
            # Rollback triggered automatically by device
            log_error(f"Firmware update failed for {machine_id}")
```

### Q5: How do you detect and prevent fraud (e.g., bypassing payment)?

**Answer**: Multi-layered fraud detection:

```python
def detect_fraud(transaction):
    # Check 1: Verify payment token is valid
    if not validate_payment_token(transaction.payment_token):
        return {"fraud": True, "reason": "Invalid payment token"}
    
    # Check 2: Verify transaction amount matches beverage price
    expected_price = get_price(transaction.machine_id, transaction.beverage_type)
    if abs(transaction.amount - expected_price) > 0.01:
        return {"fraud": True, "reason": "Price mismatch"}
    
    # Check 3: Detect velocity (too many transactions in short time)
    recent_transactions = redis.get(f"velocity:{transaction.payment_token}")
    if recent_transactions > 10:  # 10 transactions in 1 minute
        return {"fraud": True, "reason": "Velocity exceeded"}
    
    # Check 4: Verify inventory was actually dispensed
    inventory_before = redis.get(f"inventory:{transaction.machine_id}")
    inventory_after = get_current_inventory(transaction.machine_id)
    
    if inventory_before['coffee_beans'] == inventory_after['coffee_beans']:
        # No inventory change, but payment processed - suspicious
        return {"fraud": True, "reason": "No inventory change"}
    
    return {"fraud": False}
```

---

**End of Document**
