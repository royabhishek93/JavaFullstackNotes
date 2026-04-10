# Splitwise - High-Level Design

## 1. System Overview

Splitwise is an expense-sharing application that allows users to track shared expenses, split bills, and settle debts within groups. The system manages complex financial relationships, calculates optimal settlements to minimize transactions, supports multiple currencies, handles group hierarchies, and provides balance tracking across multiple contexts. It must ensure strong financial consistency, support millions of users globally, process thousands of transactions per second, and provide real-time balance updates with eventual settlement.

## 2. Requirements

### Functional Requirements
- **User Management**: Registration, profile management, friend connections
- **Expense Creation**: Add expenses with multiple participants, split types (equal, percentage, exact amounts, shares)
- **Group Management**: Create groups, add/remove members, group settings
- **Balance Tracking**: Track individual and group balances in real-time
- **Settlement**: Calculate optimal settlements, record payments, mark expenses as settled
- **Multiple Currencies**: Support 150+ currencies with real-time conversion
- **Categories**: Expense categorization (food, rent, entertainment, utilities)
- **Comments**: Add notes and comments to expenses
- **Notifications**: Alert users about new expenses, payments, reminders
- **Reports**: Monthly reports, group spending analytics, export data
- **Recurring Expenses**: Set up automatic recurring expenses (rent, subscriptions)

### Non-Functional Requirements
- **Consistency**: Strong consistency for financial transactions (ACID)
- **Availability**: 99.95% uptime
- **Scalability**: Support 50M+ users, 100K+ groups
- **Performance**: Expense creation < 300ms, balance calculation < 100ms
- **Accuracy**: Zero tolerance for financial calculation errors
- **Security**: End-to-end encryption for sensitive data, PCI compliance
- **Audit Trail**: Complete immutable history of all transactions
- **Multi-tenancy**: Isolated data per user/group

## 3. Capacity Estimation

### Scale Assumptions
- **Total Users**: 50 million registered users
- **Daily Active Users (DAU)**: 5 million users
- **Expenses per Day**: 2 million expenses = 23 expenses/sec (peak: 100/sec)
- **Groups**: 10 million active groups
- **Average Group Size**: 5 members
- **Expenses per User per Month**: 20 expenses
- **Settlements per Month**: 5 million settlements
- **Average Expense Participants**: 3 users

### Storage Estimation
- **Users**: 50M users × 2KB = 100GB
- **Friendships**: 50M users × 100 friends × 16 bytes = 80GB
- **Groups**: 10M groups × 5KB = 50GB
- **Expenses**: 2M/day × 1KB × 365 = 730GB/year
- **Expense Splits**: 2M/day × 3 participants × 200 bytes × 365 = 438GB/year
- **Settlements**: 5M/month × 500 bytes × 12 = 30GB/year
- **Balances**: 50M users × 100 balances × 100 bytes = 500GB
- **Comments**: 500K/day × 300 bytes × 365 = 54.75GB/year
- **Total Storage** (5 years): ~10TB (with replicas: 30TB)

### Bandwidth
- **Ingress**: 23 expenses/sec × 5KB = 115KB/s
- **Egress**: 50K balance queries/sec × 2KB = 100MB/s

### Computation
- **Balance Calculations**: 2M expenses/day × 3 participants = 6M balance updates/day
- **Settlement Optimization**: 5M settlements/month × 100ms = 500K seconds/month
- **Currency Conversions**: 500K conversions/day

## 4. System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                      Client Layer                              │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐          │
│  │   Web   │  │   iOS   │  │ Android │  │   API   │          │
│  │  React  │  │  Swift  │  │ Kotlin  │  │ Clients │          │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘          │
└───────┼────────────┼────────────┼────────────┼────────────────┘
        │            │            │            │
        └────────────┼────────────┼────────────┘
                     │
          ┌──────────▼──────────┐
          │   API Gateway       │
          │  - Authentication   │
          │  - Rate Limiting    │
          │  - Request Routing  │
          └──────────┬──────────┘
                     │
        ┌────────────┼────────────────────┐
        │            │                    │
   ┌────▼────┐  ┌───▼──────┐  ┌──────▼──────┐
   │  User   │  │ Expense  │  │   Group     │
   │ Service │  │ Service  │  │  Service    │
   └────┬────┘  └───┬──────┘  └──────┬──────┘
        │           │                 │
        └───────────┼─────────────────┘
                    │
        ┌───────────┼────────────────────┐
        │           │                    │
   ┌────▼─────┐ ┌──▼────────┐  ┌───────▼──────┐
   │ Balance  │ │Settlement │  │  Currency    │
   │ Service  │ │  Service  │  │   Service    │
   └────┬─────┘ └──┬────────┘  └───────┬──────┘
        │          │                    │
        └──────────┼────────────────────┘
                   │
        ┌──────────▼──────────────────────┐
        │   Message Queue (RabbitMQ)      │
        │  - expense.created              │
        │  - payment.recorded             │
        │  - balance.updated              │
        └──────────┬──────────────────────┘
                   │
        ┌──────────┼──────────┐
        │          │          │
   ┌────▼────┐ ┌──▼──────┐ ┌─▼────────┐
   │ Notif.  │ │Analytics│ │  Audit   │
   │ Service │ │ Service │ │  Service │
   └─────────┘ └─────────┘ └──────────┘

┌──────────────────────────────────────────────────────────────┐
│                    Data Layer                                │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │PostgreSQL  │  │   Redis    │  │  MongoDB   │            │
│  │ (Users,    │  │  (Cache,   │  │ (Expense   │            │
│  │  Expenses, │  │  Sessions) │  │  Details)  │            │
│  │  Balances) │  │            │  │            │            │
│  └────────────┘  └────────────┘  └────────────┘            │
└──────────────────────────────────────────────────────────────┘
```

## 5. Core Components

### User Service
- **Registration**: Email/phone verification with OTP
- **Authentication**: JWT tokens with refresh token rotation
- **Profile Management**: Update preferences, notification settings
- **Friend Management**: Add/remove friends, search by email/phone
- **Privacy**: Control who can add you to groups, expense visibility

### Group Service
- **Group Creation**: Create groups with name, description, category
- **Member Management**: Add/remove members, assign roles (admin, member)
- **Group Types**: Home, Trip, Couple, Event, Other
- **Group Settings**: Simplify debts by default, group currency
- **Group Balances**: Calculate aggregate group balances

### Expense Service (Core Component)
- **Expense Creation**:
```python
class ExpenseService:
    def create_expense(self, expense_data):
        """Create expense with atomic transaction"""
        
        with db.transaction():
            # Step 1: Validate expense
            self.validate_expense(expense_data)
            
            # Step 2: Create expense record
            expense = Expense(
                description=expense_data['description'],
                amount=Decimal(expense_data['amount']),
                currency=expense_data['currency'],
                category=expense_data['category'],
                date=expense_data['date'],
                created_by=expense_data['user_id'],
                group_id=expense_data.get('group_id')
            )
            db.save(expense)
            
            # Step 3: Calculate splits
            splits = self.calculate_splits(
                expense.amount,
                expense_data['split_type'],
                expense_data['participants']
            )
            
            # Step 4: Create split records
            for participant in splits:
                split = ExpenseSplit(
                    expense_id=expense.id,
                    user_id=participant['user_id'],
                    amount=participant['amount'],
                    paid_share=participant.get('paid_share', 0),
                    owed_share=participant['owed_share']
                )
                db.save(split)
            
            # Step 5: Update balances atomically
            self.update_balances(expense, splits)
            
            # Step 6: Emit event
            event_bus.publish('expense.created', {
                'expense_id': expense.id,
                'group_id': expense.group_id,
                'participants': [s['user_id'] for s in splits]
            })
            
            return expense
    
    def calculate_splits(self, amount, split_type, participants):
        """Calculate how expense is split"""
        
        if split_type == 'EQUAL':
            # Split equally among participants
            share_amount = amount / len(participants)
            splits = [
                {
                    'user_id': p['user_id'],
                    'paid_share': amount if p.get('paid_by') else 0,
                    'owed_share': share_amount
                }
                for p in participants
            ]
        
        elif split_type == 'EXACT':
            # Exact amounts specified per participant
            splits = [
                {
                    'user_id': p['user_id'],
                    'paid_share': p.get('paid_amount', 0),
                    'owed_share': p['owed_amount']
                }
                for p in participants
            ]
        
        elif split_type == 'PERCENTAGE':
            # Percentage-based split
            splits = [
                {
                    'user_id': p['user_id'],
                    'paid_share': amount if p.get('paid_by') else 0,
                    'owed_share': amount * (p['percentage'] / 100)
                }
                for p in participants
            ]
        
        elif split_type == 'SHARES':
            # Share-based split (e.g., 2:3:1 ratio)
            total_shares = sum(p['shares'] for p in participants)
            splits = [
                {
                    'user_id': p['user_id'],
                    'paid_share': amount if p.get('paid_by') else 0,
                    'owed_share': amount * (p['shares'] / total_shares)
                }
                for p in participants
            ]
        
        # Validate total matches expense amount
        total_owed = sum(s['owed_share'] for s in splits)
        if abs(total_owed - amount) > Decimal('0.01'):
            raise InvalidSplitException(f"Split total {total_owed} doesn't match expense {amount}")
        
        return splits
```

### Balance Service (Critical Component)
- **Balance Tracking**: Maintain balances between every user pair
- **Balance Calculation Algorithm**:
```python
class BalanceService:
    def update_balances(self, expense, splits):
        """Update balances atomically with pessimistic locking"""
        
        # Determine who paid and who owes
        payers = [s for s in splits if s['paid_share'] > 0]
        borrowers = [s for s in splits if s['owed_share'] > 0]
        
        # Update balances between payers and borrowers
        for payer in payers:
            for borrower in borrowers:
                if payer['user_id'] == borrower['user_id']:
                    # Same person paid and owes
                    continue
                
                # Calculate net change
                amount_paid_for_borrower = (
                    payer['paid_share'] * 
                    (borrower['owed_share'] / expense.amount)
                )
                
                if amount_paid_for_borrower <= 0:
                    continue
                
                # Convert to common currency if needed
                if expense.currency != 'USD':
                    amount_usd = currency_service.convert(
                        amount_paid_for_borrower,
                        expense.currency,
                        'USD'
                    )
                else:
                    amount_usd = amount_paid_for_borrower
                
                # Update or create balance record
                # Lock rows to prevent concurrent updates
                balance = db.query("""
                    SELECT * FROM balances
                    WHERE (user_id = ? AND friend_id = ?)
                       OR (user_id = ? AND friend_id = ?)
                    FOR UPDATE
                """, payer['user_id'], borrower['user_id'],
                     borrower['user_id'], payer['user_id']).first()
                
                if balance:
                    # Update existing balance
                    if balance.user_id == payer['user_id']:
                        balance.amount += amount_usd
                    else:
                        balance.amount -= amount_usd
                    
                    # Flip balance if it becomes negative
                    if balance.amount < 0:
                        balance.user_id, balance.friend_id = balance.friend_id, balance.user_id
                        balance.amount = abs(balance.amount)
                    
                    db.save(balance)
                else:
                    # Create new balance
                    balance = Balance(
                        user_id=payer['user_id'],
                        friend_id=borrower['user_id'],
                        amount=amount_usd,
                        currency='USD',
                        group_id=expense.group_id
                    )
                    db.save(balance)
    
    def get_user_balances(self, user_id):
        """Get all balances for a user"""
        
        # Check cache first
        cached = redis.get(f"balances:{user_id}")
        if cached:
            return json.loads(cached)
        
        # Fetch from database
        balances = db.query("""
            SELECT 
                CASE 
                    WHEN user_id = ? THEN friend_id 
                    ELSE user_id 
                END as other_user_id,
                CASE 
                    WHEN user_id = ? THEN amount 
                    ELSE -amount 
                END as balance_amount,
                currency,
                group_id
            FROM balances
            WHERE user_id = ? OR friend_id = ?
        """, user_id, user_id, user_id, user_id)
        
        # Cache for 5 minutes
        redis.setex(f"balances:{user_id}", 300, json.dumps(balances))
        
        return balances
    
    def get_group_balances(self, group_id):
        """Get all balances within a group"""
        
        balances = db.query("""
            SELECT user_id, friend_id, amount, currency
            FROM balances
            WHERE group_id = ?
        """, group_id)
        
        return balances
```

### Settlement Service (Complex Component)
- **Optimal Settlement Algorithm**: Minimize number of transactions
```python
class SettlementService:
    def calculate_optimal_settlements(self, group_id):
        """
        Calculate optimal settlements to minimize transactions
        Using algorithm similar to "Simplify Debts" feature
        """
        
        # Step 1: Get all balances in group
        balances = balance_service.get_group_balances(group_id)
        
        # Step 2: Build net balance for each user
        net_balances = defaultdict(Decimal)
        
        for balance in balances:
            net_balances[balance.user_id] += balance.amount
            net_balances[balance.friend_id] -= balance.amount
        
        # Step 3: Separate debtors and creditors
        debtors = []   # Users who owe money
        creditors = []  # Users who are owed money
        
        for user_id, net_balance in net_balances.items():
            if net_balance < 0:
                debtors.append({'user_id': user_id, 'amount': abs(net_balance)})
            elif net_balance > 0:
                creditors.append({'user_id': user_id, 'amount': net_balance})
        
        # Step 4: Greedy algorithm to minimize transactions
        settlements = []
        
        debtors.sort(key=lambda x: x['amount'], reverse=True)
        creditors.sort(key=lambda x: x['amount'], reverse=True)
        
        i, j = 0, 0
        while i < len(debtors) and j < len(creditors):
            debtor = debtors[i]
            creditor = creditors[j]
            
            # Settle minimum of what debtor owes and creditor is owed
            settle_amount = min(debtor['amount'], creditor['amount'])
            
            settlements.append({
                'from_user_id': debtor['user_id'],
                'to_user_id': creditor['user_id'],
                'amount': settle_amount,
                'currency': 'USD'
            })
            
            debtor['amount'] -= settle_amount
            creditor['amount'] -= settle_amount
            
            if debtor['amount'] == 0:
                i += 1
            if creditor['amount'] == 0:
                j += 1
        
        return settlements
    
    def record_payment(self, payment_data):
        """Record a payment between users"""
        
        with db.transaction():
            # Create payment record
            payment = Payment(
                from_user_id=payment_data['from_user_id'],
                to_user_id=payment_data['to_user_id'],
                amount=payment_data['amount'],
                currency=payment_data['currency'],
                group_id=payment_data.get('group_id'),
                payment_method=payment_data.get('method'),
                notes=payment_data.get('notes'),
                created_at=datetime.now()
            )
            db.save(payment)
            
            # Update balance
            amount_usd = currency_service.convert(
                payment.amount,
                payment.currency,
                'USD'
            )
            
            balance = db.query("""
                SELECT * FROM balances
                WHERE (user_id = ? AND friend_id = ?)
                   OR (user_id = ? AND friend_id = ?)
                FOR UPDATE
            """, payment.to_user_id, payment.from_user_id,
                 payment.from_user_id, payment.to_user_id).first()
            
            if balance:
                if balance.user_id == payment.to_user_id:
                    balance.amount -= amount_usd
                else:
                    balance.amount += amount_usd
                
                # Flip if negative
                if balance.amount < 0:
                    balance.user_id, balance.friend_id = balance.friend_id, balance.user_id
                    balance.amount = abs(balance.amount)
                
                # Delete if settled
                if balance.amount < Decimal('0.01'):
                    db.delete(balance)
                else:
                    db.save(balance)
            
            # Invalidate cache
            redis.delete(f"balances:{payment.from_user_id}")
            redis.delete(f"balances:{payment.to_user_id}")
            
            # Emit event
            event_bus.publish('payment.recorded', {
                'payment_id': payment.id,
                'from_user_id': payment.from_user_id,
                'to_user_id': payment.to_user_id,
                'amount': payment.amount
            })
            
            return payment
```

### Currency Service
- **Exchange Rates**: Fetch and cache exchange rates
- **Conversion**:
```python
class CurrencyService:
    def __init__(self):
        self.redis = Redis()
        self.api_key = os.getenv('EXCHANGE_RATE_API_KEY')
    
    def get_exchange_rate(self, from_currency, to_currency):
        """Get exchange rate with caching"""
        
        if from_currency == to_currency:
            return Decimal('1.0')
        
        # Check cache
        cache_key = f"exchange_rate:{from_currency}:{to_currency}"
        cached_rate = self.redis.get(cache_key)
        
        if cached_rate:
            return Decimal(cached_rate)
        
        # Fetch from API
        response = requests.get(
            f"https://api.exchangerate-api.com/v4/latest/{from_currency}",
            timeout=5
        )
        rates = response.json()['rates']
        rate = Decimal(str(rates[to_currency]))
        
        # Cache for 1 hour
        self.redis.setex(cache_key, 3600, str(rate))
        
        return rate
    
    def convert(self, amount, from_currency, to_currency):
        """Convert amount between currencies"""
        
        rate = self.get_exchange_rate(from_currency, to_currency)
        converted = amount * rate
        
        # Round to 2 decimal places
        return converted.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
```

### Notification Service
- **Notification Types**: New expense, payment received, reminder, group activity
- **Channels**: Push notifications, email, in-app
- **Reminders**: Send reminders for outstanding balances
```python
class NotificationService:
    def notify_expense_created(self, expense):
        """Notify participants of new expense"""
        
        participants = get_expense_participants(expense.id)
        
        for participant in participants:
            if participant.user_id == expense.created_by:
                continue
            
            notification = {
                'user_id': participant.user_id,
                'type': 'EXPENSE_ADDED',
                'title': 'New expense added',
                'body': f"{expense.created_by_name} added \"{expense.description}\" (${expense.amount})",
                'data': {
                    'expense_id': expense.id,
                    'group_id': expense.group_id
                }
            }
            
            # Send push notification
            self.send_push_notification(participant.user_id, notification)
            
            # Send email if preferred
            if participant.email_notifications:
                self.send_email(participant.email, notification)
    
    def send_payment_reminder(self, user_id, friend_id, amount):
        """Send reminder for outstanding balance"""
        
        # Check if reminder was sent recently
        last_reminder = redis.get(f"reminder:{user_id}:{friend_id}")
        if last_reminder and (datetime.now() - last_reminder).days < 7:
            return
        
        notification = {
            'user_id': user_id,
            'type': 'REMINDER',
            'title': 'Payment reminder',
            'body': f"You owe {friend_name} ${amount}",
            'data': {
                'friend_id': friend_id,
                'amount': amount
            }
        }
        
        self.send_push_notification(user_id, notification)
        
        # Track reminder sent
        redis.set(f"reminder:{user_id}:{friend_id}", datetime.now())
```

### Analytics Service
- **Spending Patterns**: Track spending by category, group, time
- **Reports**: Generate monthly reports, group spending summaries
- **Exports**: Export data to CSV, Excel

## 6. Database Design

### Schema Design

```sql
-- Users Table
CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE,
    password_hash VARCHAR(128) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    profile_picture_url VARCHAR(500),
    default_currency CHAR(3) DEFAULT 'USD',
    timezone VARCHAR(50),
    email_notifications BOOLEAN DEFAULT TRUE,
    push_notifications BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    INDEX idx_email (email),
    INDEX idx_phone (phone)
);

-- Friendships Table
CREATE TABLE friendships (
    friendship_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    friend_id BIGINT REFERENCES users(user_id),
    status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE, BLOCKED
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, friend_id),
    INDEX idx_user (user_id),
    INDEX idx_friend (friend_id)
);

-- Groups Table
CREATE TABLE groups (
    group_id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    group_type VARCHAR(20), -- HOME, TRIP, COUPLE, EVENT, OTHER
    category VARCHAR(50),
    created_by BIGINT REFERENCES users(user_id),
    default_currency CHAR(3) DEFAULT 'USD',
    simplify_debts BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    INDEX idx_created_by (created_by)
);

-- Group Members Table
CREATE TABLE group_members (
    group_id BIGINT REFERENCES groups(group_id),
    user_id BIGINT REFERENCES users(user_id),
    role VARCHAR(20) DEFAULT 'MEMBER', -- ADMIN, MEMBER
    joined_at TIMESTAMP DEFAULT NOW(),
    left_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    PRIMARY KEY (group_id, user_id),
    INDEX idx_user (user_id)
);

-- Expenses Table
CREATE TABLE expenses (
    expense_id BIGSERIAL PRIMARY KEY,
    description VARCHAR(255) NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    currency CHAR(3) DEFAULT 'USD',
    category VARCHAR(50),
    expense_date DATE NOT NULL,
    created_by BIGINT REFERENCES users(user_id),
    group_id BIGINT REFERENCES groups(group_id),
    split_type VARCHAR(20), -- EQUAL, EXACT, PERCENTAGE, SHARES
    notes TEXT,
    receipt_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    is_recurring BOOLEAN DEFAULT FALSE,
    recurring_interval VARCHAR(20), -- DAILY, WEEKLY, MONTHLY
    INDEX idx_created_by (created_by),
    INDEX idx_group (group_id),
    INDEX idx_date (expense_date),
    INDEX idx_category (category),
    CONSTRAINT positive_amount CHECK (amount > 0)
);

-- Expense Splits Table
CREATE TABLE expense_splits (
    split_id BIGSERIAL PRIMARY KEY,
    expense_id BIGINT REFERENCES expenses(expense_id),
    user_id BIGINT REFERENCES users(user_id),
    paid_share DECIMAL(15,2) DEFAULT 0.00, -- Amount paid by this user
    owed_share DECIMAL(15,2) NOT NULL,     -- Amount owed by this user
    is_settled BOOLEAN DEFAULT FALSE,
    INDEX idx_expense (expense_id),
    INDEX idx_user (user_id),
    CONSTRAINT valid_shares CHECK (paid_share >= 0 AND owed_share >= 0)
);

-- Balances Table (Denormalized for fast lookups)
CREATE TABLE balances (
    balance_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    friend_id BIGINT REFERENCES users(user_id),
    amount DECIMAL(15,2) NOT NULL, -- Positive: user owes friend, Negative: friend owes user
    currency CHAR(3) DEFAULT 'USD',
    group_id BIGINT REFERENCES groups(group_id),
    last_updated TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, friend_id, group_id),
    INDEX idx_user (user_id),
    INDEX idx_friend (friend_id),
    INDEX idx_group (group_id),
    CONSTRAINT positive_balance CHECK (amount >= 0)
);

-- Payments Table
CREATE TABLE payments (
    payment_id BIGSERIAL PRIMARY KEY,
    from_user_id BIGINT REFERENCES users(user_id),
    to_user_id BIGINT REFERENCES users(user_id),
    amount DECIMAL(15,2) NOT NULL,
    currency CHAR(3) DEFAULT 'USD',
    group_id BIGINT REFERENCES groups(group_id),
    payment_method VARCHAR(50), -- CASH, CARD, BANK_TRANSFER, PAYPAL, VENMO
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_from_user (from_user_id),
    INDEX idx_to_user (to_user_id),
    INDEX idx_date (created_at),
    CONSTRAINT positive_payment CHECK (amount > 0)
);

-- Comments Table
CREATE TABLE comments (
    comment_id BIGSERIAL PRIMARY KEY,
    expense_id BIGINT REFERENCES expenses(expense_id),
    user_id BIGINT REFERENCES users(user_id),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    INDEX idx_expense (expense_id)
);

-- Notifications Table
CREATE TABLE notifications (
    notification_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    type VARCHAR(50), -- EXPENSE_ADDED, PAYMENT_RECEIVED, REMINDER
    title VARCHAR(255),
    body TEXT,
    data JSONB,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_user_created (user_id, created_at),
    INDEX idx_unread (user_id, is_read)
);

-- Audit Log Table (Immutable)
CREATE TABLE audit_logs (
    log_id BIGSERIAL PRIMARY KEY,
    entity_type VARCHAR(50), -- EXPENSE, PAYMENT, BALANCE
    entity_id BIGINT,
    action VARCHAR(50), -- CREATE, UPDATE, DELETE
    user_id BIGINT REFERENCES users(user_id),
    old_data JSONB,
    new_data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_entity (entity_type, entity_id),
    INDEX idx_user (user_id),
    INDEX idx_created (created_at)
);
```

## 7. API Design

### Create Expense
```http
POST /api/v1/expenses
Authorization: Bearer <token>
Content-Type: application/json

{
  "description": "Dinner at restaurant",
  "amount": 120.00,
  "currency": "USD",
  "category": "Food",
  "expense_date": "2026-04-07",
  "group_id": 123,
  "split_type": "EQUAL",
  "participants": [
    {"user_id": 1, "paid_share": 120.00},
    {"user_id": 2, "owed_share": 40.00},
    {"user_id": 3, "owed_share": 40.00}
  ],
  "notes": "Great dinner!"
}

Response: 201 Created
{
  "expense_id": 456,
  "description": "Dinner at restaurant",
  "amount": 120.00,
  "currency": "USD",
  "splits": [
    {"user_id": 1, "paid": 120.00, "owed": 40.00, "net": 80.00},
    {"user_id": 2, "paid": 0.00, "owed": 40.00, "net": -40.00},
    {"user_id": 3, "paid": 0.00, "owed": 40.00, "net": -40.00}
  ],
  "created_at": "2026-04-07T10:00:00Z"
}
```

### Get User Balances
```http
GET /api/v1/users/me/balances
Authorization: Bearer <token>

Response: 200 OK
{
  "balances": [
    {
      "user_id": 2,
      "user_name": "John Doe",
      "balance": -40.00,
      "currency": "USD",
      "last_updated": "2026-04-07T10:00:00Z"
    },
    {
      "user_id": 3,
      "user_name": "Jane Smith",
      "balance": 25.00,
      "currency": "USD",
      "last_updated": "2026-04-06T15:30:00Z"
    }
  ],
  "total_owed": 40.00,
  "total_owing": 25.00,
  "net_balance": -15.00
}
```

### Calculate Settlements
```http
POST /api/v1/groups/{group_id}/settlements/calculate
Authorization: Bearer <token>

Response: 200 OK
{
  "settlements": [
    {
      "from_user_id": 2,
      "from_user_name": "John Doe",
      "to_user_id": 1,
      "to_user_name": "Alice",
      "amount": 40.00,
      "currency": "USD"
    },
    {
      "from_user_id": 3,
      "from_user_name": "Jane Smith",
      "to_user_id": 1,
      "to_user_name": "Alice",
      "amount": 25.00,
      "currency": "USD"
    }
  ],
  "transaction_count": 2,
  "optimized": true
}
```

### Record Payment
```http
POST /api/v1/payments
Authorization: Bearer <token>
Content-Type: application/json

{
  "from_user_id": 2,
  "to_user_id": 1,
  "amount": 40.00,
  "currency": "USD",
  "group_id": 123,
  "payment_method": "CASH",
  "notes": "Paid in cash"
}

Response: 201 Created
{
  "payment_id": 789,
  "from_user_id": 2,
  "to_user_id": 1,
  "amount": 40.00,
  "currency": "USD",
  "new_balance": 0.00,
  "created_at": "2026-04-07T11:00:00Z"
}
```

### Get Group Expenses
```http
GET /api/v1/groups/{group_id}/expenses?page=1&limit=20
Authorization: Bearer <token>

Response: 200 OK
{
  "expenses": [
    {
      "expense_id": 456,
      "description": "Dinner at restaurant",
      "amount": 120.00,
      "currency": "USD",
      "category": "Food",
      "created_by": {
        "user_id": 1,
        "name": "Alice"
      },
      "expense_date": "2026-04-07",
      "participants": [
        {"user_id": 1, "paid": 120.00, "owed": 40.00},
        {"user_id": 2, "paid": 0.00, "owed": 40.00},
        {"user_id": 3, "paid": 0.00, "owed": 40.00}
      ],
      "created_at": "2026-04-07T10:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 45,
    "has_more": true
  }
}
```

## 8. Scalability Strategy

### Database Sharding
```
Sharding Strategy:

1. Users & Friendships: Shard by user_id % 8
2. Groups: Shard by group_id % 8
3. Expenses: Shard by expense_id % 8
4. Balances: Shard by user_id % 8 (co-located with users)

Cross-Shard Queries:
- Group balances may require scatter-gather across shards
- Use caching heavily to avoid frequent cross-shard queries
```

### Caching Strategy
```
Redis Cache:

1. User balances: Key = balances:{user_id}, TTL = 5 minutes
2. Group members: Key = group_members:{group_id}, TTL = 30 minutes
3. Exchange rates: Key = exchange_rate:{from}:{to}, TTL = 1 hour
4. User sessions: Key = session:{token}, TTL = 24 hours

Invalidation:
- Invalidate user balances on expense creation or payment
- Invalidate group members on member add/remove
```

### Message Queue
```
RabbitMQ Queues:

1. expense.created: Triggers balance updates, notifications
2. payment.recorded: Triggers balance updates, notifications
3. notification.send: Async notification delivery
4. analytics.process: Async analytics processing
```

## 9. Technology Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **Backend** | Python Flask, FastAPI | Rapid development, Decimal precision |
| **Frontend** | React, TypeScript | Type safety, modern UI |
| **Mobile** | React Native | Cross-platform |
| **Database** | PostgreSQL 15+ | ACID, Decimal precision |
| **Cache** | Redis | Fast balance lookups |
| **Message Queue** | RabbitMQ | Reliable message delivery |
| **Currency API** | ExchangeRate-API | Real-time rates |
| **Monitoring** | Prometheus, Grafana | Metrics and alerts |

## 10. Interview Discussion Points

### Q1: How do you ensure financial consistency across concurrent transactions?

**Answer**: Use pessimistic locking with database transactions:
```python
with db.transaction():
    # Lock balance rows
    balance = db.query("""
        SELECT * FROM balances
        WHERE user_id = ? AND friend_id = ?
        FOR UPDATE
    """, user_id, friend_id).first()
    
    # Update balance
    balance.amount += new_amount
    db.save(balance)
```

### Q2: How do you handle currency conversions?

**Answer**: Normalize all balances to USD internally, display in user's preferred currency.

### Q3: How does the optimal settlement algorithm work?

**Answer**: Calculate net balances, use greedy matching between debtors and creditors to minimize transactions.

---

**End of Document**
