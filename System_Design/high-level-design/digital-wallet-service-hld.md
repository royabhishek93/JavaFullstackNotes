# Digital Wallet Service - High Level Design

## System Overview

A comprehensive digital wallet service similar to PayPal, Venmo, or Paytm that enables users to store money digitally, send and receive payments peer-to-peer (P2P), pay at merchants, link bank accounts and cards, maintain transaction history, handle multi-currency support, implement fraud detection, ensure PCI-DSS compliance, support QR code payments, provide instant settlements, and integrate with external payment gateways. The system must handle millions of daily transactions, ensure zero money loss, maintain strong consistency for account balances, provide real-time notifications, support international transfers, and comply with financial regulations (KYC, AML).

## Requirements

### Functional Requirements

1. **User Management**
   - User registration with KYC verification
   - Profile management
   - Link bank accounts and debit/credit cards
   - Set transaction PINs and security questions
   - Multi-factor authentication (MFA)

2. **Wallet Operations**
   - Add money to wallet (bank transfer, card)
   - Withdraw money to bank account
   - Check wallet balance
   - Transaction history and statements
   - Multi-currency support

3. **P2P Transfers**
   - Send money to other users (phone, email, wallet ID, QR code)
   - Request money from other users
   - Split bills among groups
   - Recurring payments and standing orders

4. **Merchant Payments**
   - Pay at online merchants
   - QR code-based payments at physical stores
   - Payment links for businesses
   - Subscription management

5. **Transaction Management**
   - Transaction confirmation and receipts
   - Transaction disputes and chargebacks
   - Refund processing
   - Transaction search and filtering

6. **Notifications**
   - Push notifications for transactions
   - Email and SMS alerts
   - Payment reminders
   - Promotional offers

7. **Rewards & Offers**
   - Cashback on transactions
   - Referral bonuses
   - Loyalty points
   - Promotional campaigns

### Non-Functional Requirements

1. **Performance**
   - Transaction processing < 3 seconds
   - Balance check < 200ms
   - Handle 10K+ transactions per second (TPS)
   - Support 100M+ active users

2. **Availability**
   - 99.99% uptime (< 1 hour downtime per year)
   - Zero data loss
   - Disaster recovery in < 1 hour

3. **Consistency**
   - Strong consistency for wallet balances
   - ACID transactions for money transfers
   - Idempotency for all payment operations
   - Exactly-once processing

4. **Security**
   - PCI-DSS Level 1 compliance
   - End-to-end encryption
   - Secure card storage (tokenization)
   - Fraud detection and prevention
   - AML (Anti-Money Laundering) monitoring

5. **Scalability**
   - Horizontal scaling for all services
   - Database sharding by user_id
   - Auto-scaling during peak loads

6. **Compliance**
   - KYC (Know Your Customer) verification
   - AML monitoring
   - GDPR compliance (data privacy)
   - Financial regulations (PSD2, RBI guidelines)

## Capacity Estimation

### Traffic Estimates

**Assumptions:**
- Total users: 100 million
- Daily Active Users (DAU): 20 million
- Transactions per user per day: 2
- Total daily transactions: 40 million
- Average transaction value: $50
- Daily transaction volume: $2 billion

**Calculations:**

**Transactions Per Second (TPS):**
- Average TPS: 40M transactions / 86400 seconds = ~463 TPS
- Peak TPS (assume 3x average): ~1,400 TPS
- Design for: 5,000 TPS (with safety margin)

**API Queries Per Second (QPS):**
- Balance checks: 20M users * 5 checks/day / 86400 = ~1,200 QPS
- Transaction history: 20M * 3 views/day / 86400 = ~700 QPS
- Send money API: 463 TPS
- Add money API: ~200 TPS
- Total QPS: ~2,500 QPS (average), ~7,500 QPS (peak)

### Storage Estimates

**Users:**
- 100M users * 5KB per user (profile, KYC, preferences) = 500GB

**Wallets:**
- 100M wallets * 2KB (balance, currency, status) = 200GB

**Transactions:**
- 40M transactions/day * 2KB per transaction = 80GB/day
- Annual: 80GB * 365 = 29TB
- 5-year retention: ~145TB

**Linked Accounts (Cards/Banks):**
- 100M users * 2 accounts average * 1KB = 200GB

**Audit Logs:**
- 40M transactions/day * 1KB audit log = 40GB/day = 14.6TB/year

**Total Storage:**
- Primary data: ~150TB (5 years)
- With replicas (3x): ~450TB
- Backups: ~150TB
- **Total: ~600TB**

### Bandwidth Estimates

**Incoming:**
- Transaction requests: 463 TPS * 2KB = ~1 MB/s
- Add money: 200 TPS * 2KB = ~400 KB/s
- Total incoming: ~1.5 MB/s

**Outgoing:**
- Transaction confirmations: 463 TPS * 3KB = ~1.4 MB/s
- Balance checks: 1200 QPS * 1KB = ~1.2 MB/s
- Transaction history: 700 QPS * 20KB = ~14 MB/s
- Notifications: 463 TPS * 1KB = ~500 KB/s
- Total outgoing: ~17 MB/s

**Total Bandwidth: ~20 MB/s (~160 Mbps)**

## System Architecture

```
                                  [DNS]
                                    |
                             [Load Balancer]
                          (AWS ALB / Nginx)
                                    |
                    +---------------+----------------+
                    |                                |
              [Web Clients]                   [Mobile Apps]
                    |                                |
                    +---------------+----------------+
                                    |
                              [API Gateway]
                        (Auth, Rate Limit, Routing)
                                    |
        +-----------+---------------+---------------+-----------+
        |           |               |               |           |
   [Auth      [User         [Wallet        [Transaction  [Payment
   Service]   Service]       Service]       Service]      Gateway
        |           |               |               |       Service]
        +-----+-----+-----+---------+---------------+-----------+
              |           |                     |
        [Message Queue - Kafka]          [Ledger Service]
        Topics: transactions,            (Double-entry bookkeeping)
        notifications, events                    |
              |                                   |
        +-----+-----------+-----------------------+----------+
        |                 |                       |          |
   [Notification   [Fraud Detection]      [Settlement  [Reporting
    Service]        Service (ML)]          Service]    Service]
        |                 |                       |          |
        +-----+-----------+-----------------------+----------+
                          |
        +-----------------+------------------+
        |                 |                  |
   [PostgreSQL      [Redis Cache]      [MongoDB]
   (Users, Wallets, (Balance cache,    (Transaction logs,
   Transactions)]   Sessions, Locks)]  Audit trails)]
        |                                    |
   [Read Replicas]                    [Elasticsearch]
   (For reporting)                    (Transaction search)

   [External Services]
   - Payment Gateways (Stripe, Razorpay)
   - Bank APIs (for account linking)
   - KYC providers (Aadhaar, ID verification)
   - SMS/Email (Twilio, SendGrid)
   - S3 (Document storage)
```

## Core Components

### 1. Authentication Service

**Responsibilities:**
- User registration and login
- JWT token generation and validation
- Multi-factor authentication (MFA)
- Session management
- Password reset and account recovery
- Device fingerprinting

**Security Measures:**
```
- Passwords hashed with Argon2
- JWT tokens with 15-minute expiry
- Refresh tokens with 30-day expiry
- MFA via SMS OTP or authenticator app
- Rate limiting: 5 failed login attempts = account lock
- Device-based authentication for high-value transactions
```

**API Endpoints:**
```
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/verify-otp
POST /api/v1/auth/refresh-token
POST /api/v1/auth/logout
```

### 2. User Service

**Responsibilities:**
- User profile management
- KYC verification workflow
- Document upload and verification
- Linked accounts management (bank, cards)
- User preferences and settings

**KYC Levels:**
```
Level 0: Basic registration (phone/email)
- Transaction limit: $100/month
- No withdrawal

Level 1: Email + Phone verified
- Transaction limit: $1,000/month
- Withdrawal: $500/month

Level 2: Government ID verified (Aadhaar, PAN, Passport)
- Transaction limit: $10,000/month
- Withdrawal: Unlimited

Level 3: Full KYC (address proof, income proof)
- Transaction limit: Unlimited
- Business account eligible
```

**Card Tokenization:**
```
Never store raw card numbers!

Process:
1. User enters card details
2. Send to payment gateway (Stripe, Razorpay)
3. Receive token: "tok_visa_1234abcd"
4. Store only token in database
5. For future payments, use token

Database:
{
  "card_id": "card_xyz123",
  "user_id": 12345,
  "token": "tok_visa_1234abcd",
  "card_last4": "4242",
  "card_brand": "VISA",
  "expiry_month": 12,
  "expiry_year": 2028,
  "card_holder_name": "John Doe"
}
```

### 3. Wallet Service

**Responsibilities:**
- Create and manage user wallets
- Check wallet balance (real-time)
- Multi-currency support
- Wallet freezing/unfreezing
- Balance holds for pending transactions

**Wallet Schema:**
```sql
CREATE TABLE wallets (
    wallet_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL REFERENCES users(user_id),
    balance DECIMAL(15,2) DEFAULT 0.00,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE, FROZEN, SUSPENDED
    available_balance DECIMAL(15,2) DEFAULT 0.00, -- balance - holds
    on_hold_balance DECIMAL(15,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INT DEFAULT 0, -- For optimistic locking
    INDEX idx_user (user_id),
    INDEX idx_status (status)
);
```

**Balance Caching:**
```python
def get_balance(user_id):
    cache_key = f"balance:{user_id}"
    
    # Try cache first
    cached_balance = redis.get(cache_key)
    if cached_balance:
        return float(cached_balance)
    
    # Cache miss - fetch from database
    balance = db.query("""
        SELECT balance FROM wallets WHERE user_id = %s
    """, (user_id,))[0]['balance']
    
    # Cache for 5 minutes
    redis.setex(cache_key, 300, str(balance))
    
    return balance

def invalidate_balance_cache(user_id):
    redis.delete(f"balance:{user_id}")
```

### 4. Transaction Service

**Responsibilities:**
- Process P2P transfers
- Merchant payments
- Add money to wallet
- Withdraw money to bank
- Transaction validation and authorization
- Idempotency handling

**Transaction Flow (P2P Transfer):**
```
1. User A initiates transfer to User B ($100)
2. Validate:
   - User A has sufficient balance ($100 + fees)
   - User B account is active and can receive
   - Transaction limits not exceeded
   - No fraud flags
3. Create transaction record (status: PENDING)
4. Place hold on User A's wallet ($100)
5. Process via Ledger Service (double-entry)
   - Debit User A wallet: -$100
   - Credit User B wallet: +$100
6. Update transaction status: COMPLETED
7. Release hold on User A
8. Send notifications to both users
9. Invalidate balance caches
```

**Idempotency:**
```python
def transfer_money(transfer_request):
    idempotency_key = transfer_request['idempotency_key']
    
    # Check if already processed
    existing_txn = db.query("""
        SELECT transaction_id, status 
        FROM transactions 
        WHERE idempotency_key = %s
    """, (idempotency_key,))
    
    if existing_txn:
        if existing_txn['status'] == 'COMPLETED':
            # Already processed - return cached result
            return {"status": "SUCCESS", "transaction_id": existing_txn['transaction_id']}
        elif existing_txn['status'] == 'PENDING':
            # Still processing
            return {"status": "PROCESSING", "message": "Transaction in progress"}
        else:
            # Failed previously - can retry
            pass
    
    # Process new transaction
    transaction_id = process_transfer(transfer_request)
    
    return {"status": "SUCCESS", "transaction_id": transaction_id}
```

### 5. Ledger Service (Double-Entry Bookkeeping)

**Responsibilities:**
- Maintain accurate financial records
- Double-entry bookkeeping for all transactions
- Ensure sum of all debits = sum of all credits
- Immutable transaction log
- Audit trail

**Ledger Entries:**
```sql
CREATE TABLE ledger_entries (
    entry_id BIGSERIAL PRIMARY KEY,
    transaction_id VARCHAR(50) NOT NULL,
    account_type VARCHAR(20), -- 'WALLET', 'BANK', 'REVENUE', 'FEE'
    account_id BIGINT, -- wallet_id or bank_account_id
    entry_type VARCHAR(10), -- 'DEBIT', 'CREDIT'
    amount DECIMAL(15,2) NOT NULL,
    balance_after DECIMAL(15,2),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_transaction (transaction_id),
    INDEX idx_account (account_id, created_at DESC)
);
```

**Example: P2P Transfer ($100 from User A to User B)**
```
Ledger Entries:
1. DEBIT  User A Wallet: -$100 (Balance: $400)
2. CREDIT User B Wallet: +$100 (Balance: $600)
3. DEBIT  User A Wallet: -$1 (Fee, Balance: $399)
4. CREDIT Revenue Account: +$1

Invariant: Sum of debits = Sum of credits ($101 = $101)
```

**Transaction Implementation:**
```python
def process_transfer(from_user_id, to_user_id, amount, transaction_id):
    with db.transaction():
        # 1. Debit sender
        sender_wallet = db.query_for_update("""
            SELECT wallet_id, balance, version 
            FROM wallets 
            WHERE user_id = %s
        """, (from_user_id,))
        
        if sender_wallet['balance'] < amount:
            raise InsufficientBalanceError()
        
        new_sender_balance = sender_wallet['balance'] - amount
        
        db.execute("""
            UPDATE wallets 
            SET balance = %s, version = version + 1, updated_at = NOW()
            WHERE wallet_id = %s AND version = %s
        """, (new_sender_balance, sender_wallet['wallet_id'], sender_wallet['version']))
        
        # Record ledger entry
        db.execute("""
            INSERT INTO ledger_entries 
            (transaction_id, account_type, account_id, entry_type, amount, balance_after)
            VALUES (%s, 'WALLET', %s, 'DEBIT', %s, %s)
        """, (transaction_id, sender_wallet['wallet_id'], amount, new_sender_balance))
        
        # 2. Credit receiver
        receiver_wallet = db.query_for_update("""
            SELECT wallet_id, balance, version 
            FROM wallets 
            WHERE user_id = %s
        """, (to_user_id,))
        
        new_receiver_balance = receiver_wallet['balance'] + amount
        
        db.execute("""
            UPDATE wallets 
            SET balance = %s, version = version + 1, updated_at = NOW()
            WHERE wallet_id = %s AND version = %s
        """, (new_receiver_balance, receiver_wallet['wallet_id'], receiver_wallet['version']))
        
        # Record ledger entry
        db.execute("""
            INSERT INTO ledger_entries 
            (transaction_id, account_type, account_id, entry_type, amount, balance_after)
            VALUES (%s, 'WALLET', %s, 'CREDIT', %s, %s)
        """, (transaction_id, receiver_wallet['wallet_id'], amount, new_receiver_balance))
        
        # 3. Update transaction status
        db.execute("""
            UPDATE transactions 
            SET status = 'COMPLETED', completed_at = NOW()
            WHERE transaction_id = %s
        """, (transaction_id,))
    
    # Outside transaction: invalidate caches
    invalidate_balance_cache(from_user_id)
    invalidate_balance_cache(to_user_id)
    
    # Send notifications
    notify_transaction_success(from_user_id, to_user_id, amount)
```

### 6. Payment Gateway Service

**Responsibilities:**
- Integration with external payment gateways (Stripe, Razorpay)
- Card payments processing
- Bank transfers (ACH, NEFT, RTGS, IMPS)
- Payment status reconciliation
- Webhook handling

**Add Money Flow:**
```
1. User initiates "Add Money" ($500 via card)
2. Create payment intent with gateway
3. Gateway returns checkout URL
4. User completes payment on gateway
5. Gateway sends webhook to our system
6. Verify webhook signature
7. Credit user's wallet
8. Record in ledger
9. Send confirmation to user
```

**Webhook Handling:**
```python
@app.route('/webhooks/stripe', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError:
        return 'Invalid signature', 400
    
    # Handle event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        
        # Credit user's wallet
        user_id = payment_intent['metadata']['user_id']
        amount = payment_intent['amount'] / 100  # Convert cents to dollars
        
        credit_wallet(user_id, amount, payment_intent['id'])
    
    return 'Success', 200
```

### 7. Fraud Detection Service

**Responsibilities:**
- Real-time fraud detection using ML
- Anomaly detection (unusual transaction patterns)
- Velocity checks (too many transactions)
- Device fingerprinting
- IP reputation checking
- AML monitoring

**Fraud Detection Rules:**
```python
def detect_fraud(transaction):
    risk_score = 0
    
    # Rule 1: Velocity check (>10 transactions in 1 hour)
    recent_txns = get_recent_transactions(transaction.user_id, hours=1)
    if len(recent_txns) > 10:
        risk_score += 30
    
    # Rule 2: Large amount (>$5000 in single transaction)
    if transaction.amount > 5000:
        risk_score += 25
    
    # Rule 3: New account (<7 days old)
    account_age_days = get_account_age_days(transaction.user_id)
    if account_age_days < 7:
        risk_score += 20
    
    # Rule 4: Device mismatch (different device than usual)
    if not is_trusted_device(transaction.user_id, transaction.device_id):
        risk_score += 15
    
    # Rule 5: Unusual time (3 AM - 6 AM)
    hour = datetime.now().hour
    if 3 <= hour <= 6:
        risk_score += 10
    
    # Rule 6: Recipient is new (never transacted before)
    if not has_previous_transaction(transaction.user_id, transaction.recipient_id):
        risk_score += 15
    
    # ML Model prediction
    ml_fraud_score = ml_model.predict([transaction.features])[0]
    risk_score += ml_fraud_score * 50
    
    # Decision
    if risk_score > 70:
        return {"fraud": "HIGH_RISK", "action": "BLOCK"}
    elif risk_score > 40:
        return {"fraud": "MEDIUM_RISK", "action": "REQUIRE_OTP"}
    else:
        return {"fraud": "LOW_RISK", "action": "ALLOW"}
```

### 8. Notification Service

**Responsibilities:**
- Push notifications (mobile)
- SMS notifications
- Email notifications
- In-app notifications
- Notification preferences management

**Event Triggers:**
- Money sent/received
- Money added/withdrawn
- Failed transaction
- Login from new device
- Password reset
- Low balance alert
- Promotional offers

**Technology:** Firebase Cloud Messaging (FCM), Twilio SMS, SendGrid Email

### 9. Settlement Service

**Responsibilities:**
- Batch settlement with banks
- Merchant payouts
- International remittances
- Currency conversion
- Settlement reconciliation

**Settlement Process:**
```
Daily Settlement (End of Day):
1. Aggregate all completed transactions for the day
2. Calculate net position per bank/payment gateway
3. Initiate bank transfers for net amounts
4. Update settlement status
5. Generate settlement reports
6. Reconcile with bank statements
```

## Database Schema

### Users Table

```sql
CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    full_name VARCHAR(255),
    date_of_birth DATE,
    kyc_level INT DEFAULT 0, -- 0, 1, 2, 3
    kyc_status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, VERIFIED, REJECTED
    kyc_verified_at TIMESTAMP,
    email_verified BOOLEAN DEFAULT FALSE,
    phone_verified BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE, SUSPENDED, CLOSED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_phone (phone),
    INDEX idx_kyc (kyc_level, kyc_status)
);
```

### Wallets Table

```sql
CREATE TABLE wallets (
    wallet_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL REFERENCES users(user_id),
    balance DECIMAL(15,2) DEFAULT 0.00 CHECK (balance >= 0),
    currency VARCHAR(3) DEFAULT 'USD',
    available_balance DECIMAL(15,2) DEFAULT 0.00,
    on_hold_balance DECIMAL(15,2) DEFAULT 0.00,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INT DEFAULT 0,
    INDEX idx_user (user_id)
);
```

### Transactions Table (Partitioned by created_at)

```sql
CREATE TABLE transactions (
    transaction_id VARCHAR(50),
    sender_user_id BIGINT REFERENCES users(user_id),
    receiver_user_id BIGINT REFERENCES users(user_id),
    amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    transaction_type VARCHAR(20), -- P2P, ADD_MONEY, WITHDRAW, MERCHANT_PAYMENT
    status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, COMPLETED, FAILED, REFUNDED
    description TEXT,
    fee DECIMAL(10,2) DEFAULT 0.00,
    idempotency_key VARCHAR(100) UNIQUE,
    payment_method VARCHAR(50), -- CARD, BANK_TRANSFER, WALLET
    external_payment_id VARCHAR(100),
    failure_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    PRIMARY KEY (transaction_id, created_at),
    INDEX idx_sender (sender_user_id, created_at DESC),
    INDEX idx_receiver (receiver_user_id, created_at DESC),
    INDEX idx_idempotency (idempotency_key),
    INDEX idx_status (status, created_at)
) PARTITION BY RANGE (created_at);

-- Monthly partitions
CREATE TABLE transactions_2026_04 PARTITION OF transactions
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

CREATE TABLE transactions_2026_05 PARTITION OF transactions
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
```

### Ledger Entries Table

```sql
CREATE TABLE ledger_entries (
    entry_id BIGSERIAL PRIMARY KEY,
    transaction_id VARCHAR(50) NOT NULL,
    account_type VARCHAR(20), -- WALLET, BANK, REVENUE, FEE
    account_id BIGINT,
    entry_type VARCHAR(10), -- DEBIT, CREDIT
    amount DECIMAL(15,2) NOT NULL,
    balance_before DECIMAL(15,2),
    balance_after DECIMAL(15,2),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_transaction (transaction_id),
    INDEX idx_account (account_id, created_at DESC)
);
```

### Linked Accounts Table (Banks & Cards)

```sql
CREATE TABLE linked_accounts (
    account_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    account_type VARCHAR(20), -- BANK_ACCOUNT, DEBIT_CARD, CREDIT_CARD
    
    -- Bank details (if applicable)
    bank_name VARCHAR(100),
    account_number_encrypted VARCHAR(255),
    account_holder_name VARCHAR(255),
    ifsc_code VARCHAR(20),
    
    -- Card details (tokenized - NEVER store raw card numbers!)
    card_token VARCHAR(255), -- Token from payment gateway
    card_last4 VARCHAR(4),
    card_brand VARCHAR(20), -- VISA, MASTERCARD, AMEX
    card_expiry_month INT,
    card_expiry_year INT,
    card_holder_name VARCHAR(255),
    
    is_primary BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id)
);
```

### Balance Holds Table

```sql
CREATE TABLE balance_holds (
    hold_id BIGSERIAL PRIMARY KEY,
    wallet_id BIGINT REFERENCES wallets(wallet_id),
    amount DECIMAL(15,2) NOT NULL,
    reason VARCHAR(100),
    related_transaction_id VARCHAR(50),
    status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE, RELEASED, EXPIRED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    released_at TIMESTAMP,
    INDEX idx_wallet (wallet_id, status)
);
```

### Fraud Alerts Table

```sql
CREATE TABLE fraud_alerts (
    alert_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    transaction_id VARCHAR(50),
    alert_type VARCHAR(50), -- VELOCITY, LARGE_AMOUNT, DEVICE_MISMATCH
    risk_score INT,
    action_taken VARCHAR(20), -- BLOCK, REQUIRE_OTP, ALLOW, MANUAL_REVIEW
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id, created_at DESC),
    INDEX idx_unresolved (resolved, created_at)
);
```

## API Design

### Wallet APIs

```
GET /api/v1/wallet/balance
Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "wallet_id": 12345,
  "balance": 1250.50,
  "available_balance": 1200.00,
  "on_hold_balance": 50.50,
  "currency": "USD",
  "last_updated": "2026-04-07T10:30:00Z"
}

POST /api/v1/wallet/add-money
Authorization: Bearer <jwt_token>

{
  "amount": 500.00,
  "payment_method": "CARD",
  "card_id": "card_abc123"
}

Response: 202 Accepted
{
  "transaction_id": "txn_xyz789",
  "status": "PENDING",
  "payment_url": "https://gateway.stripe.com/checkout/xyz",
  "message": "Complete payment to add money"
}

POST /api/v1/wallet/withdraw
Authorization: Bearer <jwt_token>

{
  "amount": 300.00,
  "bank_account_id": "bank_def456"
}

Response: 200 OK
{
  "transaction_id": "txn_abc123",
  "status": "PROCESSING",
  "estimated_time": "2-3 business days",
  "fee": 2.00,
  "net_amount": 298.00
}
```

### Transfer APIs

```
POST /api/v1/transfers/send
Authorization: Bearer <jwt_token>
Idempotency-Key: <unique_key>

{
  "recipient": {
    "type": "USER_ID", // USER_ID, PHONE, EMAIL, QR_CODE
    "value": "user_67890"
  },
  "amount": 100.00,
  "description": "Lunch payment",
  "transaction_pin": "1234"
}

Response: 201 Created
{
  "transaction_id": "txn_transfer_123",
  "status": "COMPLETED",
  "sender": {
    "user_id": 12345,
    "name": "John Doe"
  },
  "recipient": {
    "user_id": 67890,
    "name": "Jane Smith"
  },
  "amount": 100.00,
  "fee": 0.00,
  "total_deducted": 100.00,
  "timestamp": "2026-04-07T10:45:30Z"
}

POST /api/v1/transfers/request
Authorization: Bearer <jwt_token>

{
  "from_user_id": 67890,
  "amount": 50.00,
  "description": "Split bill for dinner"
}

Response: 201 Created
{
  "request_id": "req_xyz123",
  "status": "PENDING",
  "expires_at": "2026-04-14T10:45:30Z"
}

GET /api/v1/transfers/{transactionId}
Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "transaction_id": "txn_transfer_123",
  "type": "P2P",
  "status": "COMPLETED",
  "sender": {...},
  "recipient": {...},
  "amount": 100.00,
  "timestamp": "2026-04-07T10:45:30Z",
  "receipt_url": "https://receipts.wallet.com/txn_transfer_123"
}
```

### Transaction History

```
GET /api/v1/transactions?limit=20&offset=0&type=ALL&dateFrom=2026-03-01&dateTo=2026-04-07

Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "transactions": [
    {
      "transaction_id": "txn_123",
      "type": "P2P",
      "direction": "SENT",
      "counterparty": {
        "user_id": 67890,
        "name": "Jane Smith"
      },
      "amount": 100.00,
      "status": "COMPLETED",
      "timestamp": "2026-04-07T10:45:30Z"
    },
    {
      "transaction_id": "txn_124",
      "type": "ADD_MONEY",
      "direction": "CREDIT",
      "amount": 500.00,
      "payment_method": "CARD_****4242",
      "status": "COMPLETED",
      "timestamp": "2026-04-05T14:20:00Z"
    }
  ],
  "pagination": {
    "total_count": 150,
    "limit": 20,
    "offset": 0,
    "has_more": true
  }
}
```

### QR Code Payment

```
POST /api/v1/qr/generate
Authorization: Bearer <jwt_token>

{
  "amount": 50.00, // Optional, can be left blank for variable amount
  "description": "Payment for coffee"
}

Response: 200 OK
{
  "qr_code_id": "qr_abc123",
  "qr_code_data": "wallet://pay?id=qr_abc123&amount=50.00",
  "qr_code_image_url": "https://cdn.wallet.com/qr/qr_abc123.png",
  "expires_at": "2026-04-07T11:45:30Z"
}

POST /api/v1/qr/scan-and-pay
Authorization: Bearer <jwt_token>

{
  "qr_code_data": "wallet://pay?id=qr_abc123&amount=50.00",
  "transaction_pin": "1234"
}

Response: 200 OK
{
  "transaction_id": "txn_qr_456",
  "status": "COMPLETED",
  "amount": 50.00,
  "recipient": {
    "name": "Coffee Shop"
  }
}
```

## Scalability Strategies

### 1. Database Sharding

**User & Wallet Sharding by user_id:**
```python
def get_shard_id(user_id):
    # Hash-based sharding (10 shards)
    return user_id % 10

# Route queries to appropriate shard
shard_id = get_shard_id(user_id)
db_connection = shard_connections[shard_id]
wallet = db_connection.query("SELECT * FROM wallets WHERE user_id = %s", (user_id,))
```

**Transaction Partitioning:**
- Partition by created_at (monthly partitions)
- Keep recent 3 months on fast SSD
- Archive older partitions to cold storage

### 2. Caching Strategy

**Redis Caching:**
```
Balance Cache:
- Key: balance:{user_id}
- Value: Wallet balance
- TTL: 5 minutes
- Invalidate on every transaction

User Profile Cache:
- Key: user:{user_id}
- Value: User details (name, KYC level, etc.)
- TTL: 1 hour

Transaction History Cache (first page):
- Key: txn_history:{user_id}:page:0
- Value: List of recent 20 transactions
- TTL: 2 minutes
```

### 3. Read Replicas

```
Primary (Master): All writes
- Wallet balance updates
- Transaction creation
- User updates

Read Replicas (3 replicas):
- Transaction history queries
- Reports and analytics
- Balance checks (cache miss)

Replication lag: < 1 second (acceptable for non-critical reads)
```

### 4. Asynchronous Processing

**Kafka Topics:**
```
transactions-created: New transaction events
transactions-completed: Completed transaction events
notifications: Notification events
fraud-alerts: Fraud detection events
settlements: Settlement processing

Consumers:
- Notification Service: Send emails/SMS/push
- Fraud Detection: Analyze transactions
- Analytics Service: Update metrics
- Settlement Service: Process payouts
```

### 5. Rate Limiting

```
Per User:
- Balance checks: 60/minute
- Transfers: 10/minute
- Login attempts: 5/minute

Per API Key (for merchants):
- Payment processing: 100/second
- Balance inquiry: 1000/second

Implementation: Token bucket algorithm in Redis
```

## Security

### 1. PCI-DSS Compliance

**Never store raw card numbers!**
```
Process:
1. User enters card on frontend (HTTPS)
2. Frontend sends directly to payment gateway (Stripe, Razorpay)
3. Gateway returns token
4. Store only token in our database
5. For future payments, use token
```

### 2. Encryption

```
Data at Rest:
- Database encryption (AES-256)
- Sensitive fields encrypted (bank account numbers)
- Encryption keys in AWS KMS

Data in Transit:
- TLS 1.3 for all API calls
- Certificate pinning for mobile apps
```

### 3. Transaction PIN

```
PIN Setup:
- User sets 4-6 digit PIN
- Hashed with Argon2 (never stored plaintext)
- Required for all money transfers
- 3 failed attempts = PIN locked (require OTP reset)

2FA for High-Value:
- Transactions > $1000 require SMS OTP
- Withdraw money requires email + SMS OTP
```

## Technology Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **Backend** | Java Spring Boot / Node.js | Strong transaction support, mature ecosystem |
| **API Gateway** | Kong / AWS API Gateway | Rate limiting, auth, routing |
| **Primary Database** | PostgreSQL 14+ | ACID, strong consistency, partitioning |
| **Cache** | Redis Cluster | Low latency, distributed locks |
| **Message Queue** | Apache Kafka | High throughput, event streaming |
| **Search** | Elasticsearch | Transaction search, analytics |
| **Document Store** | MongoDB | Audit logs, flexible schema |
| **Payment Gateway** | Stripe / Razorpay | PCI-compliant, easy integration |
| **KYC Provider** | Jumio / Onfido | Identity verification |
| **SMS/Email** | Twilio / SendGrid | Notifications |
| **Object Storage** | AWS S3 | Document storage (KYC docs) |
| **CDN** | CloudFlare | Static assets |
| **Monitoring** | Prometheus + Grafana | Metrics and dashboards |
| **Logging** | ELK Stack | Centralized logging |
| **Container Orchestration** | Kubernetes | Auto-scaling, self-healing |

## Interview Q&A

### Question 1: How do you ensure exactly-once processing for money transfers to prevent duplicate charges?

**Answer:**

Use **idempotency keys** combined with **database transactions**:

```python
def transfer_money(transfer_request):
    # Idempotency key (generated by client)
    idempotency_key = transfer_request['idempotency_key']
    
    # Check if already processed
    existing = db.query("""
        SELECT transaction_id, status 
        FROM transactions 
        WHERE idempotency_key = %s
    """, (idempotency_key,))
    
    if existing:
        # Already processed - return cached result
        return {"transaction_id": existing['transaction_id'], "status": existing['status']}
    
    # Not processed yet - create new transaction
    transaction_id = generate_unique_id()
    
    try:
        with db.transaction(isolation_level='SERIALIZABLE'):
            # 1. Insert transaction record with idempotency key
            db.execute("""
                INSERT INTO transactions 
                (transaction_id, sender_user_id, receiver_user_id, amount, 
                 status, idempotency_key, created_at)
                VALUES (%s, %s, %s, %s, 'PENDING', %s, NOW())
            """, (transaction_id, sender_id, receiver_id, amount, idempotency_key))
            
            # 2. Debit sender with optimistic locking
            rows_affected = db.execute("""
                UPDATE wallets 
                SET balance = balance - %s, 
                    version = version + 1,
                    updated_at = NOW()
                WHERE user_id = %s 
                  AND balance >= %s
                  AND version = %s
            """, (amount, sender_id, amount, sender_version))
            
            if rows_affected == 0:
                raise InsufficientBalanceError()
            
            # 3. Credit receiver
            db.execute("""
                UPDATE wallets 
                SET balance = balance + %s, 
                    version = version + 1,
                    updated_at = NOW()
                WHERE user_id = %s
            """, (amount, receiver_id))
            
            # 4. Create ledger entries
            db.execute("""
                INSERT INTO ledger_entries 
                (transaction_id, account_id, entry_type, amount, created_at)
                VALUES 
                (%s, %s, 'DEBIT', %s, NOW()),
                (%s, %s, 'CREDIT', %s, NOW())
            """, (transaction_id, sender_id, amount, transaction_id, receiver_id, amount))
            
            # 5. Update transaction status
            db.execute("""
                UPDATE transactions 
                SET status = 'COMPLETED', completed_at = NOW()
                WHERE transaction_id = %s
            """, (transaction_id,))
        
        # Transaction committed successfully
        return {"transaction_id": transaction_id, "status": "COMPLETED"}
    
    except Exception as e:
        # Transaction rolled back
        logger.error(f"Transfer failed: {e}")
        raise
```

**Key Points:**
1. **Idempotency Key:** Client generates unique key per transfer attempt
2. **Database Transaction:** All operations in single ACID transaction
3. **Optimistic Locking:** Version field prevents concurrent updates
4. **Unique Constraint:** idempotency_key has unique constraint (DB-level protection)
5. **Retry Safety:** If request retries, returns cached result

### Question 2: How do you maintain strong consistency for wallet balances in a distributed system?

**Answer:**

Use **single source of truth** with **pessimistic/optimistic locking**:

**Option 1: Pessimistic Locking (SELECT FOR UPDATE)**
```python
def transfer_with_pessimistic_lock(sender_id, receiver_id, amount):
    with db.transaction():
        # Lock sender's wallet row
        sender_wallet = db.query("""
            SELECT wallet_id, balance 
            FROM wallets 
            WHERE user_id = %s
            FOR UPDATE
        """, (sender_id,))
        
        if sender_wallet['balance'] < amount:
            raise InsufficientBalanceError()
        
        # Lock receiver's wallet row
        receiver_wallet = db.query("""
            SELECT wallet_id, balance 
            FROM wallets 
            WHERE user_id = %s
            FOR UPDATE
        """, (receiver_id,))
        
        # Update balances (holding locks)
        db.execute("UPDATE wallets SET balance = balance - %s WHERE user_id = %s", 
                   (amount, sender_id))
        db.execute("UPDATE wallets SET balance = balance + %s WHERE user_id = %s", 
                   (amount, receiver_id))
```

**Option 2: Optimistic Locking (Version Field)**
```python
def transfer_with_optimistic_lock(sender_id, receiver_id, amount):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with db.transaction():
                # Read with version
                sender = db.query("SELECT balance, version FROM wallets WHERE user_id = %s", 
                                (sender_id,))
                
                if sender['balance'] < amount:
                    raise InsufficientBalanceError()
                
                # Update with version check
                rows = db.execute("""
                    UPDATE wallets 
                    SET balance = balance - %s, version = version + 1
                    WHERE user_id = %s AND version = %s
                """, (amount, sender_id, sender['version']))
                
                if rows == 0:
                    # Version mismatch - concurrent update occurred
                    raise ConcurrentUpdateError()
                
                # Credit receiver
                db.execute("UPDATE wallets SET balance = balance + %s WHERE user_id = %s", 
                          (amount, receiver_id))
            
            return  # Success
        except ConcurrentUpdateError:
            if attempt == max_retries - 1:
                raise
            time.sleep(0.1)  # Backoff and retry
```

**Comparison:**

| Approach | Pros | Cons | Best For |
|----------|------|------|----------|
| **Pessimistic** | - Guaranteed success<br>- No retries | - Lower concurrency<br>- Deadlock risk | High contention scenarios |
| **Optimistic** | - High concurrency<br>- No locks | - Retry overhead<br>- May fail | Low contention scenarios |

**Recommendation:** Use **optimistic locking** for most cases, with retry logic.

### Question 3: How do you handle reconciliation if a transaction succeeds in the database but notification fails?

**Answer:**

Use **eventual consistency** with **retry mechanism** and **audit trails**:

```python
# Transaction Processing (Synchronous)
def process_transfer(sender_id, receiver_id, amount):
    # 1. Perform money transfer (critical path)
    transaction_id = execute_transfer_in_db(sender_id, receiver_id, amount)
    
    # 2. Publish event to Kafka (asynchronous, non-blocking)
    try:
        kafka_producer.send('transactions-completed', {
            'transaction_id': transaction_id,
            'sender_id': sender_id,
            'receiver_id': receiver_id,
            'amount': amount,
            'timestamp': time.time()
        })
    except Exception as e:
        # Kafka publish failed - log error
        logger.error(f"Failed to publish transaction event: {e}")
        # Don't fail the transaction - notification will be retried
    
    return {"transaction_id": transaction_id, "status": "COMPLETED"}

# Notification Service (Consumer)
class NotificationConsumer:
    def consume_transaction_events(self):
        for message in kafka_consumer:
            event = json.loads(message.value)
            
            try:
                # Send notification
                send_sms(event['sender_id'], f"You sent ${event['amount']}")
                send_push_notification(event['receiver_id'], f"You received ${event['amount']}")
                
                # Mark as sent
                mark_notification_sent(event['transaction_id'])
            
            except Exception as e:
                logger.error(f"Notification failed: {e}")
                # Kafka will retry (automatic redelivery)

# Reconciliation Worker (runs every 5 minutes)
def reconciliation_worker():
    # Find transactions completed >10 minutes ago without notifications
    pending_notifications = db.query("""
        SELECT t.transaction_id, t.sender_user_id, t.receiver_user_id, t.amount
        FROM transactions t
        LEFT JOIN notifications n ON t.transaction_id = n.transaction_id
        WHERE t.status = 'COMPLETED'
          AND t.completed_at < NOW() - INTERVAL '10 minutes'
          AND n.notification_id IS NULL
    """)
    
    for txn in pending_notifications:
        # Retry notification
        try:
            send_notification(txn)
            mark_notification_sent(txn['transaction_id'])
        except Exception as e:
            logger.error(f"Reconciliation failed for {txn['transaction_id']}: {e}")
```

**Key Points:**
1. **Transaction First:** Money transfer completes first (critical path)
2. **Async Notifications:** Notifications sent asynchronously via Kafka
3. **Retry Mechanism:** Kafka automatic redelivery on failure
4. **Reconciliation:** Background job finds missed notifications
5. **Idempotency:** Notifications use transaction_id (prevent duplicates)

---

**End of Document**
