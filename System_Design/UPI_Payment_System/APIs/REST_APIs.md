# REST API Specifications

## Base URL
```
Production: https://api.upipayment.com/v1
Sandbox: https://sandbox-api.upipayment.com/v1
```

## Authentication
All APIs require JWT token in the Authorization header:
```
Authorization: Bearer <JWT_TOKEN>
```

## Common Headers
```
Content-Type: application/json
X-Request-ID: <UUID> (for request tracing)
X-Device-ID: <Device-Identifier>
X-API-Version: 1.0
```

---

## 1. Payment APIs

### 1.1 Initiate Payment

**Endpoint**: `POST /payments/initiate`

**Description**: Initiate a new UPI payment transaction

**Request Body**:
```json
{
  "senderVPA": "user@ybl",
  "receiverVPA": "merchant@icici",
  "amount": 1500.00,
  "currency": "INR",
  "encryptedMPIN": "encrypted_pin_hash",
  "transactionNote": "Payment for order #12345",
  "deviceId": "device-uuid-123",
  "idempotencyKey": "client-generated-uuid",
  "transactionType": "P2M"
}
```

**Response** (200 OK):
```json
{
  "status": "SUCCESS",
  "transactionId": "txn_abc123def456",
  "message": "Payment successful",
  "amount": 1500.00,
  "receiverName": "XYZ Store",
  "timestamp": "2024-01-15T10:30:45Z",
  "referenceNumber": "NPCI202401151030"
}
```

**Response** (400 Bad Request - Validation Error):
```json
{
  "status": "FAILED",
  "errorCode": "INVALID_VPA",
  "message": "Receiver VPA is invalid or inactive",
  "timestamp": "2024-01-15T10:30:45Z"
}
```

**Response** (402 Payment Required - Insufficient Balance):
```json
{
  "status": "FAILED",
  "errorCode": "INSUFFICIENT_BALANCE",
  "message": "Insufficient balance in sender's account",
  "availableBalance": 1200.00,
  "requiredAmount": 1500.00
}
```

**Error Codes**:
- `INVALID_VPA` - VPA not found or inactive
- `INVALID_MPIN` - MPIN validation failed
- `INSUFFICIENT_BALANCE` - Not enough balance
- `LIMIT_EXCEEDED` - Transaction limit exceeded
- `FRAUD_DETECTED` - Transaction blocked by fraud detection
- `DUPLICATE_REQUEST` - Duplicate idempotency key
- `NPCI_ERROR` - NPCI system error

---

### 1.2 Check Transaction Status

**Endpoint**: `GET /payments/status/{transactionId}`

**Description**: Get status of a transaction

**Path Parameters**:
- `transactionId` (string, required): Transaction ID

**Response** (200 OK):
```json
{
  "transactionId": "txn_abc123def456",
  "status": "SUCCESS",
  "senderVPA": "user@ybl",
  "receiverVPA": "merchant@icici",
  "amount": 1500.00,
  "currency": "INR",
  "initiatedAt": "2024-01-15T10:30:00Z",
  "completedAt": "2024-01-15T10:30:45Z",
  "npciTransactionId": "NPCI202401151030",
  "transactionNote": "Payment for order #12345"
}
```

**Status Values**:
- `INITIATED` - Transaction created
- `VALIDATING` - VPA validation in progress
- `PENDING` - Sent to NPCI
- `PREPARED` - 2PC Phase 1 complete
- `DEBITED` - Amount debited from sender
- `CREDITED` - Amount credited to receiver
- `SUCCESS` - Transaction completed successfully
- `FAILED` - Transaction failed
- `REVERSING` - Reversal in progress
- `REVERSED` - Amount reversed to sender

---

### 1.3 Get Transaction History

**Endpoint**: `GET /payments/history`

**Description**: Get user's transaction history with pagination

**Query Parameters**:
- `page` (int, default: 1): Page number
- `limit` (int, default: 20, max: 100): Records per page
- `startDate` (date, optional): Filter from date (YYYY-MM-DD)
- `endDate` (date, optional): Filter to date (YYYY-MM-DD)
- `status` (string, optional): Filter by status
- `transactionType` (string, optional): Filter by type (P2P, P2M, etc.)

**Response** (200 OK):
```json
{
  "transactions": [
    {
      "transactionId": "txn_abc123",
      "type": "DEBIT",
      "amount": 1500.00,
      "counterpartyVPA": "merchant@icici",
      "counterpartyName": "XYZ Store",
      "status": "SUCCESS",
      "timestamp": "2024-01-15T10:30:45Z",
      "note": "Payment for order #12345"
    },
    {
      "transactionId": "txn_def456",
      "type": "CREDIT",
      "amount": 2000.00,
      "counterpartyVPA": "friend@paytm",
      "counterpartyName": "John Doe",
      "status": "SUCCESS",
      "timestamp": "2024-01-14T15:20:30Z",
      "note": "Lunch payment"
    }
  ],
  "pagination": {
    "currentPage": 1,
    "totalPages": 5,
    "totalRecords": 98,
    "hasNext": true,
    "hasPrevious": false
  }
}
```

---

## 2. VPA Management APIs

### 2.1 Validate VPA

**Endpoint**: `POST /vpa/validate`

**Description**: Check if a VPA exists and is active

**Request Body**:
```json
{
  "vpa": "merchant@icici"
}
```

**Response** (200 OK):
```json
{
  "vpa": "merchant@icici",
  "isValid": true,
  "accountHolderName": "XYZ Store",
  "bankName": "ICICI Bank"
}
```

**Response** (404 Not Found):
```json
{
  "vpa": "invalid@test",
  "isValid": false,
  "errorCode": "VPA_NOT_FOUND",
  "message": "VPA does not exist"
}
```

---

### 2.2 Create VPA

**Endpoint**: `POST /vpa/create`

**Description**: Create a new UPI handle for user

**Request Body**:
```json
{
  "desiredVPA": "myname@ybl",
  "bankAccountId": "acc_uuid_123",
  "isPrimary": true
}
```

**Response** (201 Created):
```json
{
  "vpa": "myname@ybl",
  "handleId": "handle_uuid_456",
  "bankCode": "YBL",
  "isPrimary": true,
  "isActive": true,
  "createdAt": "2024-01-15T10:30:45Z"
}
```

---

### 2.3 List User VPAs

**Endpoint**: `GET /vpa/list`

**Description**: Get all VPAs linked to user

**Response** (200 OK):
```json
{
  "vpas": [
    {
      "vpa": "user1@ybl",
      "handleId": "handle_uuid_1",
      "bankName": "Yes Bank",
      "isPrimary": true,
      "isActive": true
    },
    {
      "vpa": "user1@paytm",
      "handleId": "handle_uuid_2",
      "bankName": "Paytm Payments Bank",
      "isPrimary": false,
      "isActive": true
    }
  ]
}
```

---

## 3. Account Management APIs

### 3.1 Link Bank Account

**Endpoint**: `POST /accounts/link`

**Description**: Link a new bank account to user

**Request Body**:
```json
{
  "accountNumber": "1234567890",
  "ifscCode": "ICIC0001234",
  "accountType": "SAVINGS",
  "vpaToLink": "user@icici"
}
```

**Response** (201 Created):
```json
{
  "accountId": "acc_uuid_789",
  "accountNumber": "****7890",
  "ifscCode": "ICIC0001234",
  "bankName": "ICICI Bank",
  "accountType": "SAVINGS",
  "linkedVPA": "user@icici",
  "status": "ACTIVE",
  "createdAt": "2024-01-15T10:30:45Z"
}
```

---

### 3.2 Get Account Balance

**Endpoint**: `GET /accounts/{accountId}/balance`

**Description**: Get current account balance (cached value)

**Path Parameters**:
- `accountId` (string, required): Account ID

**Response** (200 OK):
```json
{
  "accountId": "acc_uuid_789",
  "accountNumber": "****7890",
  "balance": 25000.50,
  "currency": "INR",
  "lastUpdated": "2024-01-15T10:30:00Z"
}
```

---

## 4. QR Code APIs

### 4.1 Generate Static QR Code

**Endpoint**: `POST /qr/generate`

**Description**: Generate a static QR code for merchant

**Request Body**:
```json
{
  "merchantVPA": "shop@icici",
  "amount": 1500.00,
  "transactionNote": "Invoice #INV-12345"
}
```

**Response** (200 OK):
```json
{
  "qrCodeId": "qr_uuid_123",
  "qrCodeData": "upi://pay?pa=shop@icici&pn=My%20Shop&am=1500.00&cu=INR&tn=Invoice%20INV-12345",
  "qrCodeImage": "data:image/png;base64,iVBORw0KGgo...",
  "expiresAt": "2024-01-16T10:30:00Z"
}
```

---

### 4.2 Parse QR Code

**Endpoint**: `POST /qr/parse`

**Description**: Parse scanned QR code data

**Request Body**:
```json
{
  "qrData": "upi://pay?pa=shop@icici&pn=My%20Shop&am=1500.00&cu=INR&tn=Invoice%20INV-12345"
}
```

**Response** (200 OK):
```json
{
  "merchantVPA": "shop@icici",
  "merchantName": "My Shop",
  "amount": 1500.00,
  "currency": "INR",
  "transactionNote": "Invoice INV-12345",
  "isValid": true
}
```

---

## 5. Authentication APIs

### 5.1 Validate MPIN

**Endpoint**: `POST /auth/validate-mpin`

**Description**: Validate user's MPIN (internal use)

**Request Body**:
```json
{
  "userId": "user_uuid_123",
  "encryptedMPIN": "encrypted_hash",
  "deviceId": "device_uuid"
}
```

**Response** (200 OK):
```json
{
  "isValid": true,
  "attemptsRemaining": 3
}
```

**Response** (401 Unauthorized):
```json
{
  "isValid": false,
  "errorCode": "INVALID_MPIN",
  "attemptsRemaining": 2,
  "message": "Incorrect MPIN. 2 attempts remaining."
}
```

---

## 6. Rate Limits

| API Endpoint | Rate Limit | Time Window |
|--------------|------------|-------------|
| `/payments/initiate` | 10 requests | per minute |
| `/payments/status` | 100 requests | per minute |
| `/payments/history` | 50 requests | per minute |
| `/vpa/validate` | 50 requests | per minute |
| `/auth/validate-mpin` | 5 requests | per minute |

**Rate Limit Response** (429 Too Many Requests):
```json
{
  "errorCode": "RATE_LIMIT_EXCEEDED",
  "message": "Too many requests. Please try again later.",
  "retryAfter": 60
}
```

---

## 7. Webhook Events

### 7.1 Transaction Status Update

**Event**: `transaction.status.updated`

**Webhook URL**: Configured by merchant

**Payload**:
```json
{
  "eventId": "evt_uuid_123",
  "eventType": "transaction.status.updated",
  "timestamp": "2024-01-15T10:30:45Z",
  "data": {
    "transactionId": "txn_abc123",
    "previousStatus": "PENDING",
    "currentStatus": "SUCCESS",
    "amount": 1500.00,
    "senderVPA": "user@ybl",
    "receiverVPA": "merchant@icici"
  }
}
```

**Webhook Signature**:
```
X-Webhook-Signature: sha256=<HMAC-SHA256-signature>
```

---

## 8. Error Response Format

All error responses follow this format:

```json
{
  "status": "FAILED",
  "errorCode": "ERROR_CODE",
  "message": "Human-readable error message",
  "timestamp": "2024-01-15T10:30:45Z",
  "requestId": "req_uuid_123",
  "details": {
    "field": "senderVPA",
    "reason": "VPA format is invalid"
  }
}
```

## 9. HTTP Status Codes

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (auth failure) |
| 402 | Payment Required (insufficient balance) |
| 403 | Forbidden (fraud detected) |
| 404 | Not Found |
| 409 | Conflict (duplicate request) |
| 429 | Too Many Requests |
| 500 | Internal Server Error |
| 502 | Bad Gateway (NPCI error) |
| 503 | Service Unavailable |
| 504 | Gateway Timeout |
