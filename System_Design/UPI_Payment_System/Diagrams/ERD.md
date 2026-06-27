# Entity Relationship Diagram (ERD) - UPI System

## Complete ERD in ASCII

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          UPI PAYMENT SYSTEM - ERD                           │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐         ┌──────────────────────┐
│       USER           │         │     UPI_HANDLE       │
├──────────────────────┤         ├──────────────────────┤
│ PK user_id           │◄────────│ PK handle_id         │
│    phone_number      │         │ FK user_id           │
│    email             │         │    vpa (user@bank)   │
│    name              │         │    bank_code         │
│    kyc_status        │         │    is_primary        │
│    created_at        │         │    is_active         │
│    updated_at        │         │    created_at        │
└──────────────────────┘         └──────────────────────┘
         │                                  │
         │                                  │
         │                                  │
         ▼                                  ▼
┌──────────────────────┐         ┌──────────────────────┐
│    BANK_ACCOUNT      │         │    USER_DEVICE       │
├──────────────────────┤         ├──────────────────────┤
│ PK account_id        │         │ PK device_id         │
│ FK user_id           │         │ FK user_id           │
│ FK handle_id         │         │    device_token      │
│    account_number    │         │    device_fingerprint│
│    ifsc_code         │         │    os_type           │
│    bank_name         │         │    is_trusted        │
│    account_type      │         │    last_login        │
│    balance (cached)  │         │    created_at        │
│    is_primary        │         └──────────────────────┘
│    created_at        │
└──────────────────────┘


┌──────────────────────────────────────────────────────────────────┐
│                         TRANSACTION                              │
├──────────────────────────────────────────────────────────────────┤
│ PK transaction_id (UUID)                                         │
│ FK sender_account_id                                             │
│ FK receiver_account_id                                           │
│    sender_vpa                                                    │
│    receiver_vpa                                                  │
│    amount (DECIMAL 18,2)                                         │
│    currency (INR)                                                │
│    transaction_type (P2P, P2M, BILL_PAY)                         │
│    status (INITIATED, PENDING, SUCCESS, FAILED, REVERSED)        │
│    npci_transaction_id                                           │
│    psp_ref_number                                                │
│    transaction_note                                              │
│    initiated_at                                                  │
│    completed_at                                                  │
│    failure_reason                                                │
│    created_at                                                    │
│    updated_at                                                    │
└──────────────────────────────────────────────────────────────────┘
         │
         │
         ├──────────────────────────┐
         │                          │
         ▼                          ▼
┌──────────────────────┐   ┌──────────────────────┐
│  TRANSACTION_LOG     │   │   SETTLEMENT         │
├──────────────────────┤   ├──────────────────────┤
│ PK log_id            │   │ PK settlement_id     │
│ FK transaction_id    │   │ FK transaction_id    │
│    previous_status   │   │    sender_bank       │
│    new_status        │   │    receiver_bank     │
│    changed_by        │   │    settlement_amount │
│    change_reason     │   │    settlement_status │
│    timestamp         │   │    settlement_date   │
└──────────────────────┘   │    settlement_ref    │
                           │    created_at        │
                           └──────────────────────┘


┌──────────────────────┐         ┌──────────────────────┐
│     MERCHANT         │         │    MERCHANT_QR       │
├──────────────────────┤         ├──────────────────────┤
│ PK merchant_id       │◄────────│ PK qr_id             │
│    merchant_name     │         │ FK merchant_id       │
│    merchant_vpa      │         │    qr_code_data      │
│    business_type     │         │    qr_type (STATIC)  │
│    gstin             │         │    amount (optional) │
│    pan_number        │         │    is_active         │
│    settlement_account│         │    created_at        │
│    mdr_rate          │         │    expires_at        │
│    is_verified       │         └──────────────────────┘
│    created_at        │
└──────────────────────┘


┌──────────────────────┐         ┌──────────────────────┐
│    PAYMENT_LIMIT     │         │   FRAUD_DETECTION    │
├──────────────────────┤         ├──────────────────────┤
│ PK limit_id          │         │ PK fraud_id          │
│ FK user_id           │         │ FK user_id           │
│    daily_limit       │         │ FK transaction_id    │
│    per_txn_limit     │         │    fraud_score       │
│    daily_usage       │         │    risk_level        │
│    monthly_limit     │         │    fraud_type        │
│    monthly_usage     │         │    action_taken      │
│    last_reset_date   │         │    detected_at       │
│    created_at        │         │    created_at        │
└──────────────────────┘         └──────────────────────┘


┌──────────────────────┐         ┌──────────────────────┐
│    NOTIFICATION      │         │    WEBHOOK_EVENT     │
├──────────────────────┤         ├──────────────────────┤
│ PK notification_id   │         │ PK event_id          │
│ FK user_id           │         │ FK transaction_id    │
│ FK transaction_id    │         │    event_type        │
│    notification_type │         │    payload (JSON)    │
│    channel (SMS/PUSH)│         │    webhook_url       │
│    message           │         │    retry_count       │
│    is_sent           │         │    delivery_status   │
│    sent_at           │         │    created_at        │
│    created_at        │         │    delivered_at      │
└──────────────────────┘         └──────────────────────┘


┌──────────────────────┐
│   IDEMPOTENCY_KEY    │
├──────────────────────┤
│ PK idempotency_key   │
│ FK transaction_id    │
│    request_hash      │
│    response_data     │
│    expires_at        │
│    created_at        │
└──────────────────────┘
```

## Relationships

```
USER (1) ──────── (N) UPI_HANDLE
USER (1) ──────── (N) BANK_ACCOUNT
USER (1) ──────── (N) USER_DEVICE
USER (1) ──────── (1) PAYMENT_LIMIT

UPI_HANDLE (1) ── (N) BANK_ACCOUNT

TRANSACTION (1) ── (N) TRANSACTION_LOG
TRANSACTION (1) ── (1) SETTLEMENT
TRANSACTION (1) ── (1) IDEMPOTENCY_KEY
TRANSACTION (1) ── (N) NOTIFICATION
TRANSACTION (1) ── (N) WEBHOOK_EVENT
TRANSACTION (N) ── (1) BANK_ACCOUNT (sender)
TRANSACTION (N) ── (1) BANK_ACCOUNT (receiver)

MERCHANT (1) ──── (N) MERCHANT_QR
MERCHANT (1) ──── (N) TRANSACTION

FRAUD_DETECTION (N) ── (1) USER
FRAUD_DETECTION (N) ── (1) TRANSACTION
```

## Key Indexes

```sql
-- High-frequency query optimization
CREATE INDEX idx_transaction_sender ON transaction(sender_account_id, created_at);
CREATE INDEX idx_transaction_receiver ON transaction(receiver_account_id, created_at);
CREATE INDEX idx_transaction_status ON transaction(status, created_at);
CREATE INDEX idx_transaction_npci ON transaction(npci_transaction_id);
CREATE INDEX idx_upi_handle_vpa ON upi_handle(vpa);
CREATE INDEX idx_idempotency_key ON idempotency_key(idempotency_key);
CREATE INDEX idx_user_phone ON user(phone_number);
CREATE INDEX idx_settlement_date ON settlement(settlement_date, settlement_status);
```

## Partitioning Strategy

```
TRANSACTION table:
- Partition by created_at (monthly partitions)
- Hot partition (current month): SSD storage
- Cold partitions (older months): HDD storage, compressed

TRANSACTION_LOG table:
- Partition by timestamp (weekly partitions)
- Retention: 6 months

SETTLEMENT table:
- Partition by settlement_date (daily partitions)
```

## Data Types & Constraints

```sql
-- Critical constraints
ALTER TABLE transaction 
  ADD CONSTRAINT chk_amount CHECK (amount > 0 AND amount <= 100000);

ALTER TABLE transaction
  ADD CONSTRAINT unique_npci_txn UNIQUE (npci_transaction_id);

ALTER TABLE upi_handle
  ADD CONSTRAINT unique_vpa UNIQUE (vpa);

ALTER TABLE idempotency_key
  ADD CONSTRAINT pk_idempotency PRIMARY KEY (idempotency_key);

-- Amount precision for financial data
amount: DECIMAL(18, 2)  -- Supports up to 1 quadrillion with 2 decimal places
```

## Estimated Storage Calculations

```
Assumptions:
- 10 billion transactions/month
- 500 million users
- Average transaction size: 500 bytes
- Log retention: 6 months

USER: 500M × 200 bytes = 100 GB
UPI_HANDLE: 800M × 150 bytes = 120 GB
BANK_ACCOUNT: 600M × 300 bytes = 180 GB
TRANSACTION: 10B/month × 500 bytes × 12 months = 60 TB/year
TRANSACTION_LOG: 40B logs/month × 200 bytes × 6 months = 48 TB
SETTLEMENT: 10B/month × 300 bytes × 12 months = 36 TB/year

Total: ~145 TB/year
```

## Sharding Strategy

```
USER, UPI_HANDLE, BANK_ACCOUNT:
- Shard by user_id hash
- 64 shards initially, expandable to 256

TRANSACTION:
- Shard by sender_account_id hash (same as user shards)
- Ensures user's transactions stay together
- Cross-shard queries for receiver queries (acceptable trade-off)

SETTLEMENT:
- Shard by settlement_date
- Each bank pair gets separate partitions
```
