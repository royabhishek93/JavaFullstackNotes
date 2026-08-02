# ATM System - High-Level Design

## 1. System Overview

An Automated Teller Machine (ATM) system is a distributed banking network that enables customers to perform financial transactions (withdrawals, deposits, balance inquiries, transfers) without human tellers. The system must handle thousands of ATMs globally, process millions of transactions daily, ensure strong consistency for account balances, maintain 99.99% uptime, and provide secure authentication and fraud detection mechanisms.

## 2. Requirements

### Functional Requirements
- **Authentication**: Card + PIN verification, biometric support
- **Cash Withdrawal**: Dispense cash with denomination selection
- **Cash Deposit**: Accept cash/check deposits with validation
- **Balance Inquiry**: Display current account balance
- **Fund Transfer**: Transfer between accounts
- **Mini Statement**: Print last 5-10 transactions
- **PIN Change**: Update PIN securely
- **Bill Payment**: Pay utilities, credit cards
- **Receipt Printing**: Transaction receipts

### Non-Functional Requirements
- **Availability**: 99.99% uptime per ATM
- **Consistency**: Strong consistency for account balances (ACID)
- **Security**: Encrypted communication, tamper detection
- **Performance**: Transaction completion < 10 seconds
- **Fault Tolerance**: Offline mode for limited operations
- **Compliance**: PCI-DSS, banking regulations
- **Scalability**: Support 100K+ ATMs, 10M+ transactions/day

## 3. Capacity Estimation

### Scale Assumptions
- **Total ATMs**: 100,000 ATMs globally
- **Transactions/Day**: 20M transactions = 231 TPS (peak 1000 TPS)
- **Average Transaction Time**: 45 seconds
- **Concurrent Sessions**: ~15,000 active sessions
- **Card Records**: 500M active cards
- **Transaction Size**: 2KB per transaction

### Storage Estimation
- **Card Data**: 500M cards × 500 bytes = 250GB
- **Account Data**: 200M accounts × 1KB = 200GB
- **Transaction Logs**: 20M/day × 2KB × 365 = 14.6TB/year
- **ATM Metadata**: 100K ATMs × 5KB = 500MB
- **Total Storage** (5 years): ~75TB (with replicas: 225TB)

### Bandwidth
- **ATM to Backend**: 231 TPS × 2KB = 462KB/s
- **Peak Bandwidth**: 1000 TPS × 2KB = 2MB/s
- **Per ATM**: ~200 transactions/day × 2KB = 400KB/day

### Cash Management
- **Average Withdrawal**: $120
- **Daily Cash Dispensed**: $120 × 15M withdrawals = $1.8B/day
- **Refill Frequency**: Every 2-3 days per ATM

## 4. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          ATM Terminal Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │  ATM #1      │  │  ATM #2      │  │  ATM #N      │             │
│  │  - Card      │  │  - Cash      │  │  - Receipt   │             │
│  │    Reader    │  │    Dispenser │  │    Printer   │             │
│  │  - PIN Pad   │  │  - Sensors   │  │  - Camera    │             │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘             │
└─────────┼──────────────────┼──────────────────┼─────────────────────┘
          │                  │                  │
          │         ┌────────▼──────────┐       │
          └─────────►   Load Balancer   ◄───────┘
                    │  (Geo-Distributed) │
                    └────────┬───────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
    ┌─────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
    │   ATM      │   │   Auth      │   │   Fraud     │
    │ Controller │   │  Service    │   │  Detection  │
    │  Service   │   │  (HSM)      │   │   Service   │
    └─────┬──────┘   └──────┬──────┘   └──────┬──────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
              ┌──────────────▼──────────────┐
              │    Transaction Service      │
              │   (Account Operations)      │
              └──────────────┬──────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
  ┌─────▼──────┐    ┌───────▼────────┐   ┌──────▼──────┐
  │  Account   │    │   Card         │   │  Settlement │
  │  Service   │    │   Service      │   │   Service   │
  └─────┬──────┘    └───────┬────────┘   └──────┬──────┘
        │                   │                    │
        └───────────────────┼────────────────────┘
                            │
              ┌─────────────▼─────────────┐
              │   Message Queue (Kafka)   │
              │  - Transactions           │
              │  - ATM Events             │
              │  - Audit Logs             │
              └─────────────┬─────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
  ┌─────▼──────┐   ┌───────▼────────┐  ┌──────▼──────┐
  │ Analytics  │   │   Notification │  │   Audit     │
  │  Service   │   │    Service     │  │   Service   │
  └────────────┘   └────────────────┘  └─────────────┘

┌───────────────────────────────────────────────────────────────┐
│                    Data Layer                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ PostgreSQL   │  │    Redis     │  │  Cassandra   │       │
│  │ (Accounts,   │  │  (Sessions,  │  │ (Transaction │       │
│  │  Cards)      │  │   Cache)     │  │   Logs)      │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└───────────────────────────────────────────────────────────────┘
```

## 5. Core Components

### ATM Controller Service
- **Device Management**: Monitor ATM hardware status (cash level, paper, etc.)
- **Session Management**: Handle user session lifecycle
- **Command Processing**: Translate user actions to backend commands
- **Offline Mode**: Cache-aside pattern for basic operations during network outage
- **Heartbeat**: Periodic health check to backend (every 30 seconds)

### Authentication Service (HSM)
- **Hardware Security Module (HSM)**: Store and validate PINs securely
- **Card Validation**: Verify card authenticity, check expiry, block status
- **PIN Verification**: Hash PIN with salt, compare with stored hash
- **Biometric Auth**: Fingerprint/facial recognition integration
- **Token Generation**: Issue JWT tokens for authenticated sessions

### Transaction Service
- **ACID Guarantees**: Two-phase commit for distributed transactions
- **Idempotency**: Prevent duplicate withdrawals (idempotency keys)
- **Balance Check**: Verify sufficient funds before withdrawal
- **Locking**: Pessimistic locking on account balance during transaction
- **Rollback**: Automatic rollback on failure (cash dispense error)

### Fraud Detection Service
- **Real-Time Analysis**: ML models detect anomalous patterns
- **Rule Engine**: Block transactions exceeding daily limits
- **Geo-Fencing**: Alert if card used in unusual location
- **Velocity Checks**: Block rapid successive withdrawals
- **Blacklist Service**: Check card against stolen/blocked list

### Cash Management Service
- **Inventory Tracking**: Monitor cash levels per denomination
- **Predictive Refill**: ML predicts when ATM needs refill
- **Denomination Optimization**: Suggest optimal cash mix
- **Alerts**: Notify CIT (Cash-in-Transit) when cash < 20%

## 6. Database Design

### Schema Design

```sql
-- Cards Table
CREATE TABLE cards (
    card_id BIGSERIAL PRIMARY KEY,
    card_number VARCHAR(16) UNIQUE NOT NULL,
    card_hash VARCHAR(64) UNIQUE NOT NULL, -- Tokenized
    account_id BIGINT NOT NULL,
    card_type VARCHAR(20), -- DEBIT, CREDIT
    expiry_date DATE NOT NULL,
    cvv_hash VARCHAR(64),
    status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE, BLOCKED, EXPIRED
    daily_withdrawal_limit DECIMAL(10,2) DEFAULT 1000.00,
    pin_hash VARCHAR(128), -- Bcrypt hash
    pin_attempts INT DEFAULT 0,
    issued_date DATE,
    last_used TIMESTAMP,
    INDEX idx_card_number_hash (card_hash),
    INDEX idx_account (account_id),
    INDEX idx_status (status)
);

-- Accounts Table
CREATE TABLE accounts (
    account_id BIGSERIAL PRIMARY KEY,
    account_number VARCHAR(20) UNIQUE NOT NULL,
    customer_id BIGINT NOT NULL,
    account_type VARCHAR(20), -- SAVINGS, CHECKING
    balance DECIMAL(15,2) NOT NULL DEFAULT 0.00,
    currency CHAR(3) DEFAULT 'USD',
    status VARCHAR(20) DEFAULT 'ACTIVE',
    overdraft_limit DECIMAL(10,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    version INT DEFAULT 0, -- Optimistic locking
    INDEX idx_customer (customer_id),
    INDEX idx_account_number (account_number),
    CHECK (balance >= -overdraft_limit)
);

-- Customers Table
CREATE TABLE customers (
    customer_id BIGSERIAL PRIMARY KEY,
    customer_number VARCHAR(20) UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(20),
    date_of_birth DATE,
    address TEXT,
    kyc_status VARCHAR(20) DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Transactions Table (Partitioned by date)
CREATE TABLE transactions (
    transaction_id BIGSERIAL,
    transaction_uuid UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    atm_id VARCHAR(20),
    card_id BIGINT REFERENCES cards(card_id),
    account_id BIGINT REFERENCES accounts(account_id),
    transaction_type VARCHAR(20), -- WITHDRAWAL, DEPOSIT, BALANCE_INQUIRY
    amount DECIMAL(10,2),
    currency CHAR(3) DEFAULT 'USD',
    balance_before DECIMAL(15,2),
    balance_after DECIMAL(15,2),
    status VARCHAR(20), -- SUCCESS, FAILED, PENDING
    failure_reason TEXT,
    transaction_date TIMESTAMP DEFAULT NOW(),
    idempotency_key VARCHAR(100) UNIQUE,
    PRIMARY KEY (transaction_id, transaction_date),
    INDEX idx_card_date (card_id, transaction_date),
    INDEX idx_account_date (account_id, transaction_date),
    INDEX idx_atm (atm_id, transaction_date)
) PARTITION BY RANGE (transaction_date);

-- Create partitions for each month
CREATE TABLE transactions_2026_04 PARTITION OF transactions
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

-- ATM Devices Table
CREATE TABLE atm_devices (
    atm_id VARCHAR(20) PRIMARY KEY,
    atm_location VARCHAR(255),
    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),
    bank_id INT,
    status VARCHAR(20) DEFAULT 'ONLINE', -- ONLINE, OFFLINE, MAINTENANCE
    cash_available DECIMAL(12,2),
    last_refill_date TIMESTAMP,
    last_heartbeat TIMESTAMP,
    cash_denominations JSONB, -- {"20": 500, "50": 200, "100": 100}
    device_metadata JSONB,
    INDEX idx_status (status),
    INDEX idx_location (latitude, longitude)
);

-- Session Management Table
CREATE TABLE atm_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    atm_id VARCHAR(20) REFERENCES atm_devices(atm_id),
    card_hash VARCHAR(64),
    session_token VARCHAR(255),
    started_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    ip_address INET,
    INDEX idx_card_session (card_hash, started_at),
    INDEX idx_expires (expires_at)
);

-- Fraud Alerts Table
CREATE TABLE fraud_alerts (
    alert_id BIGSERIAL PRIMARY KEY,
    transaction_id BIGINT,
    card_id BIGINT,
    alert_type VARCHAR(50), -- VELOCITY, GEO_ANOMALY, AMOUNT_ANOMALY
    risk_score DECIMAL(3,2), -- 0.00 to 1.00
    alert_time TIMESTAMP DEFAULT NOW(),
    resolved BOOLEAN DEFAULT FALSE,
    resolution_notes TEXT,
    INDEX idx_card_alert (card_id, alert_time)
);
```

## 7. API Design

### Authenticate User
```http
POST /api/v1/atm/authenticate
Content-Type: application/json

{
  "atm_id": "ATM001NYC",
  "card_number_hash": "a1b2c3d4...", // Client-side hashed
  "pin_hash": "xyz123...", // Client-side hashed
  "device_fingerprint": "..."
}

Response: 200 OK
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_at": "2026-04-07T10:05:00Z",
  "customer_name": "John Doe",
  "available_operations": ["WITHDRAWAL", "BALANCE_INQUIRY", "TRANSFER"]
}
```

### Get Balance
```http
GET /api/v1/atm/balance
Authorization: Bearer <session_token>
ATM-ID: ATM001NYC

Response: 200 OK
{
  "account_id": 123456,
  "balance": 5420.50,
  "currency": "USD",
  "available_balance": 5420.50,
  "account_type": "SAVINGS"
}
```

### Withdraw Cash
```http
POST /api/v1/atm/withdraw
Authorization: Bearer <session_token>
ATM-ID: ATM001NYC
Idempotency-Key: <unique_key>

{
  "amount": 200.00,
  "account_id": 123456,
  "denominations_requested": {
    "100": 2
  }
}

Response: 200 OK
{
  "transaction_id": "txn_abc123xyz",
  "amount": 200.00,
  "balance_after": 5220.50,
  "denominations_dispensed": {
    "100": 2
  },
  "receipt": {
    "atm_id": "ATM001NYC",
    "transaction_date": "2026-04-07T10:02:30Z",
    "transaction_type": "WITHDRAWAL",
    "amount": 200.00,
    "balance": 5220.50
  }
}
```

### Transfer Funds
```http
POST /api/v1/atm/transfer
Authorization: Bearer <session_token>
ATM-ID: ATM001NYC
Idempotency-Key: <unique_key>

{
  "from_account": 123456,
  "to_account": 789012,
  "amount": 500.00,
  "description": "Transfer to savings"
}

Response: 200 OK
{
  "transaction_id": "txn_def456uvw",
  "status": "SUCCESS",
  "from_balance": 4720.50,
  "to_balance": 10500.00,
  "timestamp": "2026-04-07T10:05:00Z"
}
```

### ATM Health Check
```http
POST /api/v1/atm/heartbeat
Authorization: Bearer <atm_api_key>

{
  "atm_id": "ATM001NYC",
  "status": "ONLINE",
  "cash_available": 15000.00,
  "denominations": {
    "20": 450,
    "50": 180,
    "100": 90
  },
  "device_status": {
    "card_reader": "OK",
    "cash_dispenser": "OK",
    "receipt_printer": "LOW_PAPER"
  }
}

Response: 200 OK
{
  "message": "Heartbeat received",
  "next_heartbeat": 30,
  "refill_required": false,
  "pending_updates": []
}
```

## 8. Scalability Strategy

### Horizontal Scaling
- **Stateless Services**: All services are stateless, scale horizontally
- **Load Balancer**: Route ATM requests based on geo-location
- **Service Mesh**: Istio for service discovery and load balancing

### Database Sharding
```
Shard Key Strategy:
- Accounts: Shard by account_id % 10 (10 shards)
- Transactions: Partition by date (monthly partitions)
- Cards: Shard by card_id % 10 (co-located with accounts)

Read Replicas:
- 3 read replicas per shard
- Balance inquiries → read replicas
- Withdrawals → primary database
```

### Caching Strategy
```
Redis Cache:
- Session tokens (TTL: 5 minutes)
- Card status (ACTIVE/BLOCKED) (TTL: 1 minute)
- Account balance (TTL: 30 seconds, invalidate on transaction)
- Daily withdrawal limit tracking (TTL: 24 hours)
- Blacklist cards (TTL: 1 hour, invalidate on update)

Cache-Aside Pattern:
1. Check Redis for account balance
2. If miss, query PostgreSQL
3. Update Redis with 30-second TTL
4. On withdrawal, invalidate cache immediately
```

### Geo-Distribution
```
Region          Data Centers        ATMs
North America   US-East, US-West    40,000
Europe          EU-West, EU-Central 30,000
Asia Pacific    AP-Southeast, India 25,000
Latin America   Brazil, Mexico      5,000
```

### Message Queue (Kafka)
```
Topics:
- atm.transactions: All transaction events
- atm.fraud_alerts: Fraud detection alerts
- atm.cash_alerts: Low cash warnings
- atm.heartbeats: ATM health status

Consumers:
- Analytics Service: Real-time dashboards
- Notification Service: SMS/email alerts
- Audit Service: Compliance logging
```

## 9. Fault Tolerance & High Availability

### Transaction Rollback Strategy
```python
class WithdrawalTransaction:
    def execute(self, account_id, amount, atm_id):
        try:
            # Step 1: Acquire distributed lock
            lock = redis.lock(f"account:{account_id}", timeout=10)
            
            # Step 2: Debit account
            db.execute("""
                UPDATE accounts 
                SET balance = balance - %s, version = version + 1
                WHERE account_id = %s AND balance >= %s AND version = %s
            """, (amount, account_id, amount, current_version))
            
            # Step 3: Dispense cash (send command to ATM)
            cash_dispensed = atm_controller.dispense_cash(atm_id, amount)
            
            if not cash_dispensed:
                # Rollback: Credit account back
                db.execute("""
                    UPDATE accounts 
                    SET balance = balance + %s
                    WHERE account_id = %s
                """, (amount, account_id))
                raise CashDispenseException()
            
            # Step 4: Log transaction
            log_transaction(account_id, amount, "SUCCESS")
            
            # Step 5: Invalidate cache
            redis.delete(f"balance:{account_id}")
            
        except Exception as e:
            # Compensating transaction
            rollback_transaction(account_id, amount)
            raise
        finally:
            lock.release()
```

### Offline Mode (Graceful Degradation)
```
When network is down, ATM operates in offline mode:
- Allow balance inquiry (cached balance, with disclaimer)
- Allow small withdrawals (< $100) if cached balance permits
- Store transactions locally, sync when online
- Deny high-risk operations (transfers, large withdrawals)

Sync Logic:
1. When network recovers, ATM sends pending transactions
2. Backend validates transactions against current balance
3. If sufficient funds, approve; else mark as FAILED
4. Notify customer of any failed transactions
```

### Circuit Breaker Pattern
```yaml
Service          Threshold    Timeout    Fallback
Card Service     50% errors   3s         Deny transaction
Account Service  60% errors   5s         Use cached balance
Fraud Service    70% errors   2s         Skip fraud check (log)
```

### Data Backup & Recovery
- **PostgreSQL WAL**: Write-Ahead Logging for crash recovery
- **Daily Backups**: Full backup + PITR capability
- **Cross-Region Replication**: Async replication to DR site
- **RTO/RPO**: RTO < 30 minutes, RPO < 1 minute

### Security Measures
```
1. Encryption:
   - TLS 1.3 for all communication
   - AES-256 for data at rest
   - PIN stored as bcrypt hash (never plaintext)

2. HSM (Hardware Security Module):
   - Store PIN encryption keys
   - Generate cryptographic tokens
   - Tamper-proof hardware

3. Network Security:
   - Private VPN for ATM to backend communication
   - IP whitelisting for ATMs
   - DDoS protection

4. Physical Security:
   - Tamper detection sensors
   - Alarm on unauthorized access
   - Camera surveillance
```

## 10. Technology Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **ATM Application** | C++ / Embedded Linux | Low latency, hardware control |
| **Backend Services** | Java Spring Boot | Enterprise-grade, ACID transactions |
| **API Gateway** | Kong / NGINX | Rate limiting, SSL termination |
| **Primary Database** | PostgreSQL 14+ | ACID compliance, strong consistency |
| **Cache** | Redis Cluster | Session management, low latency |
| **Message Queue** | Apache Kafka | Event streaming, audit logs |
| **Time-Series DB** | InfluxDB | ATM metrics, device telemetry |
| **Search/Analytics** | Elasticsearch | Transaction search, fraud analysis |
| **HSM** | Thales payShield / AWS CloudHSM | Secure PIN management |
| **Load Balancer** | AWS ALB / HAProxy | Geo-routing, health checks |
| **Monitoring** | Prometheus + Grafana | Real-time dashboards |
| **Logging** | ELK Stack | Centralized logging |
| **Tracing** | Jaeger | Distributed tracing |
| **Container Orchestration** | Kubernetes | Auto-scaling, self-healing |
| **CI/CD** | Jenkins | Automated deployment |

## 11. Interview Discussion Points

### Q1: How do you prevent double withdrawal if the ATM loses network after debiting the account but before dispensing cash?

**Answer**: Idempotency and transaction state management:

1. **Idempotency Key**: Every withdrawal request includes a unique idempotency key (UUID). Backend checks if this key was already processed.

2. **Transaction States**:
```
INITIATED → ACCOUNT_DEBITED → CASH_DISPENSED → COMPLETED
```

3. **Failure Scenarios**:
```
Scenario A: Network lost after ACCOUNT_DEBITED, before CASH_DISPENSED
- ATM retries with same idempotency key
- Backend sees key exists, checks state
- If state = ACCOUNT_DEBITED, send dispense command again
- Mark as COMPLETED only after cash confirmed

Scenario B: Cash dispense fails (mechanical error)
- Backend receives failure notification
- Automatically credit account back
- Mark transaction as FAILED
```

4. **Reconciliation Job**: Daily job compares transactions marked ACCOUNT_DEBITED but not COMPLETED for > 1 hour. Manual review required.

### Q2: How do you implement PIN verification securely without storing plaintext PINs?

**Answer**: Hash-based verification with HSM:

1. **PIN Storage**:
```sql
-- Never store plaintext PIN
pin_hash = bcrypt.hashpw(pin, salt, cost=12)
-- Store only the hash
INSERT INTO cards (pin_hash) VALUES ('$2b$12$...');
```

2. **Verification Flow**:
```
User enters PIN at ATM
→ ATM sends PIN to HSM (encrypted in transit)
→ HSM hashes PIN with bcrypt
→ Compare hash with stored hash
→ Return MATCH/NO_MATCH (never return hash itself)
```

3. **Brute Force Protection**:
```python
if card.pin_attempts >= 3:
    card.status = 'BLOCKED'
    send_alert(card.customer_id, "Card blocked due to multiple failed attempts")
    return AuthenticationFailed()
```

4. **PIN Transmission**: Always encrypted end-to-end (ATM → HSM), never logged.

### Q3: How do you handle ATM cash management and predict when refills are needed?

**Answer**: Predictive analytics + real-time tracking:

1. **Real-Time Tracking**:
```python
class CashManagement:
    def track_cash_level(self, atm_id):
        cash_data = redis.hgetall(f"atm_cash:{atm_id}")
        total_cash = sum(int(qty) * int(denom) for denom, qty in cash_data.items())
        
        if total_cash < LOW_CASH_THRESHOLD:
            send_alert(atm_id, "Low cash warning")
        
        return total_cash
```

2. **Predictive Model**:
```python
# ML model predicts cash need based on:
- Historical withdrawal patterns (day of week, time)
- Nearby events (concerts, holidays)
- Weather (people withdraw more in bad weather)
- Geographic location (tourist area vs residential)

predicted_refill_date = model.predict(atm_id, historical_data)
```

3. **Denomination Optimization**:
```
ATM at business district: More $100, $50 bills
ATM at residential area: More $20 bills
ATM at tourist spot: Mixed denominations
```

4. **Cash-in-Transit (CIT) Routing**: Optimize CIT routes to minimize refill costs, schedule refills during predicted low-usage times.

### Q4: How do you detect and prevent fraud in real-time?

**Answer**: Multi-layered fraud detection:

1. **Velocity Checks**:
```python
# Rule: Max 3 withdrawals per hour
withdrawals_last_hour = redis.get(f"velocity:{card_id}:1h")
if withdrawals_last_hour >= 3:
    fraud_alert("VELOCITY_EXCEEDED", card_id)
    return BlockTransaction()
```

2. **Geo-Fencing**:
```python
# If card used in NYC 10 minutes ago, can't be used in London now
last_transaction_location = redis.geopos("card_locations", card_id)
current_location = get_atm_location(atm_id)

distance = calculate_distance(last_transaction_location, current_location)
time_diff = current_time - last_transaction_time

if distance / time_diff > PHYSICALLY_IMPOSSIBLE_SPEED:
    fraud_alert("GEO_ANOMALY", card_id)
    return BlockTransaction()
```

3. **Amount Anomaly**:
```python
# ML model learns user's typical withdrawal pattern
avg_withdrawal = get_avg_withdrawal(card_id)
if current_withdrawal > 3 * avg_withdrawal:
    fraud_alert("AMOUNT_ANOMALY", card_id)
    # Don't block, but request additional verification
    return RequestOTP()
```

4. **Blacklist Check**:
```python
# Real-time check against stolen cards
if redis.sismember("blacklist_cards", card_hash):
    fraud_alert("BLACKLISTED_CARD", card_id)
    notify_authorities(atm_id, card_id)
    return BlockTransaction()
```

### Q5: How do you ensure ACID properties for fund transfers between accounts?

**Answer**: Two-phase commit with distributed locks:

```python
class FundTransferTransaction:
    def transfer(self, from_account, to_account, amount):
        lock_from = redis.lock(f"account:{from_account}", timeout=10)
        lock_to = redis.lock(f"account:{to_account}", timeout=10)
        
        try:
            # Acquire both locks in order (prevent deadlock)
            lock_from.acquire()
            lock_to.acquire()
            
            # Start database transaction
            with db.transaction():
                # Step 1: Debit from source account
                db.execute("""
                    UPDATE accounts 
                    SET balance = balance - %s, version = version + 1
                    WHERE account_id = %s AND balance >= %s
                """, (amount, from_account, amount))
                
                if db.rowcount == 0:
                    raise InsufficientFundsException()
                
                # Step 2: Credit to destination account
                db.execute("""
                    UPDATE accounts 
                    SET balance = balance + %s, version = version + 1
                    WHERE account_id = %s
                """, (amount, to_account))
                
                # Step 3: Log transaction
                db.execute("""
                    INSERT INTO transactions (from_account, to_account, amount, status)
                    VALUES (%s, %s, %s, 'SUCCESS')
                """, (from_account, to_account, amount))
                
                # If any step fails, entire transaction rolls back
                db.commit()
                
        except Exception as e:
            db.rollback()
            raise
        finally:
            lock_from.release()
            lock_to.release()
```

**ACID Guarantees**:
- **Atomicity**: Either both debit and credit succeed, or neither happens
- **Consistency**: Balance constraints maintained (balance >= 0)
- **Isolation**: Locks prevent concurrent modifications
- **Durability**: Transaction logged in WAL before commit

---

**End of Document**
