# Library Management System - High Level Design

## 1. Overview

A modern digital library management system handles the complete lifecycle of library operations including cataloging, lending, digital resources, member management, and analytics. The system supports physical books, e-books, journals, multimedia content, and provides features for both library staff and members.

**Key Features:**
- Comprehensive catalog management
- Member registration and profile management
- Book lending and return workflow
- Fine calculation and payment processing
- Digital resource access (e-books, audiobooks, journals)
- Search and recommendation system
- Reservation and waitlist management
- Inventory and procurement management
- Analytics and reporting

## 2. Requirements

### 2.1 Functional Requirements

**Core Features:**

1. **Catalog Management**
   - Add, update, delete books and resources
   - Multiple copies management for same title
   - ISBN, author, publisher, category management
   - Book metadata (title, description, cover image)
   - Support for various formats (physical, digital, audio)

2. **Member Management**
   - Member registration and authentication
   - Profile management with preferences
   - Membership types (student, faculty, general)
   - Borrowing limits based on membership tier
   - Member history and activity tracking

3. **Lending and Returns**
   - Book checkout process
   - Return processing with condition check
   - Renewal of borrowed books
   - Due date management
   - Multiple item checkout

4. **Reservation System**
   - Reserve books currently checked out
   - Waitlist management (FIFO queue)
   - Notification when book becomes available
   - Reservation expiry and cancellation

5. **Fine Management**
   - Automatic fine calculation for overdue books
   - Fine payment processing
   - Late fee waivers and adjustments
   - Fine history tracking

6. **Search and Discovery**
   - Full-text search across catalog
   - Filter by author, genre, publication year, availability
   - Barcode/ISBN scanning
   - Advanced search with multiple criteria

7. **Digital Library**
   - E-book and audiobook access
   - Online reading interface
   - Download for offline access
   - Digital rights management (DRM)
   - Concurrent access limits

8. **Notifications**
   - Due date reminders
   - Reservation available alerts
   - Overdue notices
   - New arrivals notifications
   - Event announcements

9. **Inventory Management**
   - Stock tracking for physical books
   - Book acquisition and procurement
   - Book condition tracking
   - Lost and damaged book management
   - Supplier management

### 2.2 Non-Functional Requirements

1. **Availability**: 99.9% uptime for critical operations
2. **Scalability**: Support 100,000+ members, millions of books
3. **Performance**:
   - Search results < 500ms
   - Checkout process < 2s
   - Page load < 1s
4. **Reliability**: No data loss for transactions
5. **Security**: Data encryption, RBAC
6. **Usability**: Intuitive interface for all age groups
7. **Compliance**: Copyright laws, data privacy (GDPR)

### 2.3 Extended Requirements

- Mobile app for members
- Self-service kiosks for checkout/return
- RFID integration for inventory management
- Integration with academic systems (for university libraries)
- Analytics dashboard for librarians
- Book recommendation engine
- Social features (reviews, ratings, reading lists)
- Inter-library loan system

## 3. Capacity Estimation and Constraints

### 3.1 Traffic Estimates

**Assumptions:**
- 50,000 active members
- 500,000 books in catalog
- Average 2 books borrowed per member per month
- 10% members active daily (5,000 DAU)
- Search to checkout ratio: 20:1

**Calculations:**
- Monthly checkouts: 50,000 * 2 = 100,000
- Daily checkouts: 100,000 / 30 = 3,333
- Checkouts per second (average): 3,333 / 86400 = 0.04/sec
- Checkouts per second (peak): 0.04 * 10 = 0.4/sec
- Search queries: 0.4 * 20 = 8 QPS
- Digital content access: 1,000 concurrent users

### 3.2 Storage Estimates

**Catalog Data:**
- Book metadata: 500,000 books * 5 KB = 2.5 GB
- Cover images: 500,000 * 50 KB = 25 GB
- Total catalog: ~30 GB

**Transaction Data:**
- Lending record: 2 KB per transaction
- Monthly transactions: 100,000 * 2 KB = 200 MB
- Annual: 200 MB * 12 = 2.4 GB
- 5-year retention: 12 GB

**Digital Content:**
- E-books: 10,000 titles * 5 MB = 50 GB
- Audiobooks: 5,000 titles * 100 MB = 500 GB
- Total digital: 550 GB

**Member Data:**
- Member profiles: 50,000 * 10 KB = 500 MB

**Total Storage:** ~600 GB with replication

### 3.3 Bandwidth Estimates

**Incoming:**
- Checkouts: 0.4/sec * 3 KB = 1.2 KB/s
- Book additions: Negligible

**Outgoing:**
- Search results: 8 QPS * 50 KB = 400 KB/s
- Digital content streaming: 1,000 users * 500 KB/s = 500 MB/s
- Total: ~500 MB/s (peak for digital content)

## 4. System Architecture

### 4.1 High-Level Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│Member Portal │    │ Staff Portal │    │Self-Service  │
│  (Web/App)   │    │              │    │   Kiosk      │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                    │
       └───────────────────┼────────────────────┘
                           │
                  ┌────────▼─────────┐
                  │   API Gateway    │
                  │  (Authentication)│
                  └────────┬─────────┘
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
│   Catalog   │    │   Lending   │    │   Member    │
│   Service   │    │   Service   │    │   Service   │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                   │                   │
┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
│   Search    │    │    Fine     │    │Notification │
│   Service   │    │   Service   │    │   Service   │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                   │                   │
┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
│  Digital    │    │ Reservation │    │  Analytics  │
│   Library   │    │   Service   │    │   Service   │
│   Service   │    │             │    │             │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
              ┌────────────▼────────────┐
              │   Message Queue (RabbitMQ)  │
              └────────────┬────────────┘
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
│ PostgreSQL  │    │   MongoDB   │    │    Redis    │
│ (Lending)   │    │  (Catalog)  │    │   (Cache)   │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
│Elasticsearch│    │      S3     │    │   MySQL     │
│  (Search)   │    │(Digital Books)   │   (Members) │
└─────────────┘    └─────────────┘    └─────────────┘
```

### 4.2 Service Architecture

**Microservices Pattern:**
- Independent deployment and scaling
- Database per service
- Event-driven communication
- API-first design

## 5. Core Components

### 5.1 Catalog Service

**Responsibilities:**
- Book CRUD operations
- ISBN management and validation
- Author and publisher management
- Category and genre taxonomy
- Copy management (multiple copies of same book)
- Book metadata enrichment
- Integration with external book databases (Google Books API)

**Data Model:**
```javascript
books: {
  book_id: UUID,
  isbn: String,
  title: String,
  subtitle: String,
  authors: [String],
  publisher: String,
  publication_date: Date,
  edition: String,
  language: String,
  pages: Number,
  categories: [String],
  description: Text,
  cover_image_url: String,
  format: ["physical", "ebook", "audiobook"],
  total_copies: Number,
  available_copies: Number,
  created_at: Date,
  updated_at: Date
}

book_copies: {
  copy_id: UUID,
  book_id: UUID,
  barcode: String,
  location: String,  // Shelf location
  condition: ["new", "good", "fair", "poor"],
  status: ["available", "checked_out", "reserved", "maintenance", "lost"],
  acquisition_date: Date,
  price: Decimal
}
```

**Technology:**
- Service: Java/Spring Boot
- Database: MongoDB (flexible schema for metadata)
- Search: Elasticsearch
- Cache: Redis

### 5.2 Lending Service

**Responsibilities:**
- Book checkout (issue) processing
- Book return processing
- Renewal of borrowed books
- Lending rules enforcement (max books, duration)
- Hold management
- Transaction history

**Lending Workflow:**
```
Member requests checkout
  → Validate member eligibility
  → Check book availability
  → Check member's current borrowings < limit
  → Create lending transaction
  → Update book copy status to "checked_out"
  → Set due date (14 days for regular members)
  → Generate notification
```

**Business Rules:**
- Student: Max 5 books, 14 days lending period
- Faculty: Max 10 books, 30 days lending period
- General: Max 3 books, 7 days lending period
- Max renewals: 2 times (if no reservations)
- Grace period: 1 day without fine

**State Machine:**
```
CHECKED_OUT → RENEWED (optional, max 2 times)
           → RETURNED (on time or late)
           → LOST (if not returned after 90 days)
```

**Technology:**
- Service: Java/Spring Boot
- Database: PostgreSQL (ACID for transactions)
- Cache: Redis for active lendings

### 5.3 Member Service

**Responsibilities:**
- Member registration and authentication
- Profile management
- Membership type management
- Member status (active, suspended, expired)
- Borrowing history
- Reading preferences

**Member Types:**
```sql
membership_types
- type_id (PK)
- name (Student, Faculty, General, Premium)
- max_books
- lending_period_days
- renewal_limit
- reservation_limit
- fine_per_day
- digital_access
- annual_fee
```

**Member Status:**
- ACTIVE: Can borrow books
- SUSPENDED: Has overdue books or unpaid fines > threshold
- EXPIRED: Membership expired, needs renewal
- BLOCKED: Violated rules (lost books, repeated violations)

**Technology:**
- Service: Node.js/Express
- Database: MySQL
- Cache: Redis
- Auth: JWT tokens

### 5.4 Reservation Service

**Responsibilities:**
- Book reservation (hold) management
- Waitlist queue (FIFO)
- Reservation notifications
- Reservation expiry handling
- Priority reservations (for faculty/research)

**Reservation Workflow:**
```
Member requests reservation for unavailable book
  → Add to waitlist queue
  → When book returned
    → Notify first member in queue
    → Hold book for 48 hours
    → If member doesn't checkout within 48 hours
      → Cancel reservation, notify next in queue
```

**Data Model:**
```sql
reservations
- reservation_id (PK)
- book_id (FK)
- member_id (FK)
- requested_at
- notified_at
- expires_at
- status (pending, notified, fulfilled, expired, cancelled)
- position_in_queue
```

**Technology:**
- Service: Python/Django
- Database: PostgreSQL
- Queue: RabbitMQ for notifications
- Cache: Redis for active reservations

### 5.5 Fine Service

**Responsibilities:**
- Automatic fine calculation for overdue books
- Fine payment processing
- Fine waiver management
- Payment history
- Refund processing

**Fine Calculation:**
```python
def calculate_fine(lending_record):
    due_date = lending_record.due_date
    return_date = lending_record.return_date or datetime.now()
    
    # Grace period
    if return_date <= due_date + timedelta(days=1):
        return 0
    
    days_overdue = (return_date - due_date).days - 1  # Subtract grace period
    
    # Get fine rate based on membership type
    fine_per_day = lending_record.member.membership_type.fine_per_day
    
    # Calculate fine
    fine = days_overdue * fine_per_day
    
    # Cap at book price
    max_fine = lending_record.book_copy.price
    
    return min(fine, max_fine)
```

**Fine Rules:**
- Student: $0.50/day, max $20
- Faculty: $1/day, max $50
- General: $1/day, max $30
- Lost book: Full replacement cost + processing fee ($10)
- Damaged book: Repair cost or replacement cost

**Suspension Logic:**
```python
if member.total_unpaid_fines > 50:
    member.status = "SUSPENDED"
    # Member cannot borrow until fines paid
```

**Technology:**
- Service: Java/Spring Boot
- Database: PostgreSQL
- Payment Gateway: Stripe
- Notifications: Email/SMS for overdue notices

### 5.6 Search Service

**Responsibilities:**
- Full-text search across catalog
- Faceted search with filters
- Autocomplete suggestions
- Search ranking and relevance
- Query performance optimization

**Search Features:**
- **Basic Search**: Title, author, ISBN
- **Advanced Search**: Multiple criteria (genre, publication year, language)
- **Filters**: Availability, format, category, location
- **Sort**: Relevance, title, author, publication date, popularity

**Elasticsearch Index:**
```json
{
  "book_id": "b123",
  "title": "Introduction to Algorithms",
  "authors": ["Thomas Cormen", "Charles Leiserson"],
  "isbn": "978-0262033848",
  "publisher": "MIT Press",
  "publication_year": 2009,
  "categories": ["Computer Science", "Algorithms"],
  "language": "English",
  "format": ["physical", "ebook"],
  "total_copies": 5,
  "available_copies": 2,
  "location": "CS-003-A",
  "rating": 4.5,
  "checkout_count": 150,
  "description": "Comprehensive textbook covering algorithms...",
  "indexed_at": "2026-04-07T10:00:00Z"
}
```

**Search Query:**
```json
{
  "query": {
    "bool": {
      "must": [
        {
          "multi_match": {
            "query": "algorithms",
            "fields": ["title^3", "authors^2", "description"],
            "type": "best_fields"
          }
        }
      ],
      "filter": [
        {"term": {"format": "physical"}},
        {"range": {"available_copies": {"gt": 0}}},
        {"terms": {"categories": ["Computer Science"]}}
      ]
    }
  },
  "sort": [
    {"_score": "desc"},
    {"checkout_count": "desc"}
  ]
}
```

**Ranking Factors:**
- Text relevance (BM25): 40%
- Popularity (checkout count): 30%
- Rating: 20%
- Recency (publication date): 10%

**Technology:**
- Service: Python/Flask
- Search Engine: Elasticsearch
- Cache: Redis for frequent queries

### 5.7 Digital Library Service

**Responsibilities:**
- E-book and audiobook access control
- Online reading interface
- Download management
- DRM enforcement
- Concurrent access limits
- Streaming for audiobooks

**Access Control:**
```python
def grant_digital_access(member_id, book_id):
    # Check if member has digital access privilege
    if not member.has_digital_access:
        raise PermissionDenied("Upgrade to premium membership")
    
    # Check concurrent access limit
    current_users = get_concurrent_readers(book_id)
    license_limit = get_digital_license_limit(book_id)
    
    if current_users >= license_limit:
        raise ResourceUnavailable("All digital copies currently in use")
    
    # Grant time-limited access token
    access_token = generate_access_token(member_id, book_id, expires_in=14*24*3600)
    
    # Track usage
    log_digital_access(member_id, book_id, access_token)
    
    return access_token
```

**DRM Implementation:**
- Watermarking with member details
- Encrypted content (AES-256)
- Time-limited access tokens
- Download limits (e.g., max 3 devices)
- Screenshot prevention

**Digital Lending Models:**
1. **One Copy, One User**: Like physical book (14-day loan)
2. **Concurrent Licenses**: Multiple simultaneous users (based on licenses purchased)
3. **Metered Access**: Pay per use
4. **Subscription**: Unlimited access for premium members

**Technology:**
- Service: Node.js
- Storage: AWS S3 with encryption
- Streaming: CloudFront CDN
- DRM: Adobe Content Server or custom solution

### 5.8 Notification Service

**Responsibilities:**
- Multi-channel notifications (Email, SMS, Push)
- Due date reminders (3 days, 1 day before)
- Overdue notices
- Reservation availability alerts
- New arrivals newsletters
- Event announcements

**Notification Schedule:**
```python
notifications = [
    {"type": "due_reminder", "days_before": 3, "channels": ["email", "push"]},
    {"type": "due_reminder", "days_before": 1, "channels": ["email", "sms", "push"]},
    {"type": "overdue", "days_after": 1, "channels": ["email"]},
    {"type": "overdue", "days_after": 7, "channels": ["email", "sms"]},
    {"type": "reservation_available", "delay": 0, "channels": ["email", "push"]},
]
```

**Batch Processing:**
- Cron job runs daily at 6 AM
- Fetch all lendings due in next 3 days
- Queue notification messages
- Process in batches to avoid rate limits

**Technology:**
- Service: Node.js
- Queue: RabbitMQ
- Email: SendGrid
- SMS: Twilio
- Push: Firebase Cloud Messaging

### 5.9 Analytics Service

**Responsibilities:**
- Library usage statistics
- Popular books and trends
- Member engagement metrics
- Collection development insights
- Financial reporting (fines, memberships)

**Key Metrics:**
- Total checkouts per month
- Most borrowed books
- Average lending period
- Overdue rate
- Reservation wait time
- Member retention rate
- Collection utilization (% of books borrowed at least once)

**Technology:**
- Stream Processing: Apache Kafka + Kafka Streams
- Database: TimescaleDB (time-series)
- Visualization: Grafana/Tableau

## 6. Database Design

### 6.1 Catalog Schema (MongoDB)

```javascript
books: {
  _id: ObjectId,
  book_id: UUID,
  isbn: String,
  title: String,
  authors: [String],
  publisher: String,
  publication_date: Date,
  categories: [String],
  description: String,
  cover_image_url: String,
  format: ["physical", "ebook", "audiobook"],
  metadata: {
    pages: Number,
    language: String,
    edition: String,
    dimensions: String
  },
  statistics: {
    total_copies: Number,
    available_copies: Number,
    checkout_count: Number,
    average_rating: Number,
    review_count: Number
  },
  created_at: Date,
  updated_at: Date
}

book_copies: {
  _id: ObjectId,
  copy_id: UUID,
  book_id: UUID,
  barcode: String,
  rfid_tag: String,
  location: String,
  condition: String,
  status: String,
  acquisition_date: Date,
  price: Decimal,
  notes: String
}
```

### 6.2 Lending Schema (PostgreSQL)

```sql
lendings
- lending_id (PK)
- member_id (FK)
- copy_id (FK)
- book_id (FK)
- checkout_date
- due_date
- return_date
- renewal_count
- status (checked_out, returned, lost)
- checked_out_by (staff_id)
- returned_to (staff_id)
- notes

reservations
- reservation_id (PK)
- book_id (FK)
- member_id (FK)
- requested_at
- notified_at
- expires_at
- fulfilled_at
- status (pending, notified, fulfilled, expired, cancelled)
- position_in_queue

fines
- fine_id (PK)
- lending_id (FK)
- member_id (FK)
- fine_amount
- fine_type (overdue, lost, damaged)
- created_at
- paid_at
- waived_at
- status (unpaid, paid, waived)
- payment_transaction_id
```

### 6.3 Member Schema (MySQL)

```sql
members
- member_id (PK)
- membership_number (unique)
- first_name
- last_name
- email
- phone
- date_of_birth
- address
- membership_type_id (FK)
- status (active, suspended, expired, blocked)
- registration_date
- expiry_date
- total_checkouts
- total_fines_paid
- password_hash
- created_at
- updated_at

membership_types
- type_id (PK)
- name
- max_books
- lending_period_days
- renewal_limit
- reservation_limit
- fine_per_day
- digital_access
- annual_fee
- description
```

### 6.4 Caching Strategy (Redis)

```
book:{book_id} → Book details (TTL: 1 hour)
book:availability:{book_id} → Available copies count (TTL: 5 min)
member:{member_id} → Member profile (TTL: 30 min)
member:lendings:{member_id} → Current lendings (TTL: 10 min)
search:{query_hash} → Search results (TTL: 15 min)
popular_books → Top 100 books (TTL: 1 day)
digital:active:{book_id} → Set of active readers (TTL: 1 hour)
```

## 7. API Design

### 7.1 Catalog APIs

```
GET /api/v1/books/search
  Query: q, author, category, format, available, page, limit
  Response: { books: [...], total, page, page_size }

GET /api/v1/books/{book_id}
  Response: { book details with availability, ratings, related books }

POST /api/v1/books (Staff only)
  Body: { isbn, title, authors, publisher, copies, ... }
  Response: { book_id, success }

PUT /api/v1/books/{book_id} (Staff only)
  Body: { updated fields }
  Response: { success }

GET /api/v1/books/{book_id}/copies
  Response: { copies: [{copy_id, barcode, status, location}] }

POST /api/v1/books/{book_id}/copies (Staff only)
  Body: { barcode, location, condition, price }
  Response: { copy_id, success }
```

### 7.2 Lending APIs

```
POST /api/v1/lendings/checkout (Staff only)
  Body: { member_id, copy_id, staff_id }
  Response: { lending_id, due_date, success }

POST /api/v1/lendings/{lending_id}/return (Staff only)
  Body: { condition, notes }
  Response: { success, fine_amount }

POST /api/v1/lendings/{lending_id}/renew
  Body: { member_id }
  Response: { success, new_due_date, renewal_count }

GET /api/v1/lendings/current
  Query: member_id
  Response: { lendings: [{book, due_date, renewable}] }

GET /api/v1/lendings/history
  Query: member_id, page
  Response: { lendings: [...], total }
```

### 7.3 Reservation APIs

```
POST /api/v1/reservations
  Body: { member_id, book_id }
  Response: { reservation_id, position_in_queue, estimated_wait_days }

GET /api/v1/reservations
  Query: member_id, status
  Response: { reservations: [{book, position, requested_at}] }

DELETE /api/v1/reservations/{reservation_id}
  Response: { success }

GET /api/v1/reservations/{reservation_id}
  Response: { reservation details with book info }
```

### 7.4 Member APIs

```
POST /api/v1/members/register
  Body: { first_name, last_name, email, phone, address, membership_type }
  Response: { member_id, membership_number }

POST /api/v1/members/login
  Body: { email, password }
  Response: { access_token, member_info }

GET /api/v1/members/{member_id}
  Response: { member profile, statistics, status }

PUT /api/v1/members/{member_id}
  Body: { updated fields }
  Response: { success }

GET /api/v1/members/{member_id}/dashboard
  Response: { 
    current_lendings, due_soon, reservations, 
    fines, reading_history, recommendations 
  }
```

### 7.5 Fine APIs

```
GET /api/v1/fines
  Query: member_id, status
  Response: { fines: [{amount, type, created_at, status}], total_unpaid }

POST /api/v1/fines/{fine_id}/pay
  Body: { payment_method, amount }
  Response: { success, transaction_id, receipt_url }

POST /api/v1/fines/{fine_id}/waive (Staff only)
  Body: { reason, authorized_by }
  Response: { success }
```

### 7.6 Digital Library APIs

```
POST /api/v1/digital/access
  Body: { member_id, book_id }
  Response: { access_token, expires_at, reader_url }

GET /api/v1/digital/library
  Query: member_id, format, category
  Response: { books: [...], total }

POST /api/v1/digital/download
  Body: { member_id, book_id, device_id }
  Response: { download_url, expires_in }

DELETE /api/v1/digital/return
  Body: { member_id, book_id }
  Response: { success }
```

## 8. Scalability and Performance

### 8.1 Database Optimization

**Indexing:**
```sql
-- PostgreSQL indexes
CREATE INDEX idx_lendings_member ON lendings(member_id, status, due_date);
CREATE INDEX idx_lendings_copy ON lendings(copy_id, return_date);
CREATE INDEX idx_reservations_book ON reservations(book_id, status, requested_at);
CREATE INDEX idx_fines_member ON fines(member_id, status);

-- MongoDB indexes
db.books.createIndex({"title": "text", "authors": "text", "description": "text"});
db.books.createIndex({"categories": 1, "statistics.available_copies": -1});
db.books.createIndex({"isbn": 1}, {unique: true});
db.book_copies.createIndex({"book_id": 1, "status": 1});
db.book_copies.createIndex({"barcode": 1}, {unique: true});
```

**Partitioning:**
- Partition `lendings` by checkout_date (yearly)
- Partition `fines` by created_at (yearly)
- Archive old data (> 5 years) to cold storage

**Read Replicas:**
- Route search queries to read replicas
- Route checkout operations to master
- Reduce load on master database

### 8.2 Caching Strategy

**Cache Hierarchy:**
1. **Application Cache**: In-memory LRU cache for hot data
2. **Redis Cache**: Distributed cache for shared data
3. **CDN**: Static assets (cover images, CSS, JS)

**Cache Invalidation:**
- **Time-based**: TTL for most data
- **Event-based**: Invalidate on book checkout/return
- **Write-through**: Update cache on write operations

**Cache Patterns:**
```python
def get_book(book_id):
    # Check cache
    book = redis.get(f"book:{book_id}")
    if book:
        return json.loads(book)
    
    # Cache miss, query database
    book = db.books.find_one({"book_id": book_id})
    
    # Update cache
    redis.setex(f"book:{book_id}", 3600, json.dumps(book))
    
    return book

def checkout_book(member_id, copy_id):
    # Update database
    lending = create_lending(member_id, copy_id)
    
    # Invalidate relevant caches
    redis.delete(f"member:lendings:{member_id}")
    redis.decr(f"book:availability:{lending.book_id}")
    
    return lending
```

### 8.3 Search Optimization

**Elasticsearch Optimization:**
- **Index Sharding**: 5 shards for 500K books
- **Replica Shards**: 2 replicas for high availability
- **Refresh Interval**: 30s (balance between real-time and performance)
- **Bulk Indexing**: Batch updates for efficiency

**Query Optimization:**
```json
{
  "query": {
    "bool": {
      "must": [{"multi_match": {...}}],
      "filter": [...]  // Filters are cached
    }
  },
  "size": 20,
  "_source": ["book_id", "title", "authors", "cover_image_url"],  // Only return needed fields
  "highlight": {
    "fields": {"title": {}, "description": {}}
  }
}
```

**Search Result Caching:**
```python
query_hash = hashlib.md5(json.dumps(query).encode()).hexdigest()
cache_key = f"search:{query_hash}"

results = redis.get(cache_key)
if not results:
    results = elasticsearch.search(index="books", body=query)
    redis.setex(cache_key, 900, json.dumps(results))  # 15 min TTL
```

### 8.4 Horizontal Scaling

**Microservices Scaling:**
- Stateless services behind load balancer
- Auto-scaling based on CPU/memory metrics
- Kubernetes for container orchestration

**Database Scaling:**
- **PostgreSQL**: Master-slave replication, read replicas
- **MongoDB**: Replica set (3 nodes), sharding by book_id if needed
- **Redis**: Cluster mode for horizontal scaling

### 8.5 Batch Processing

**Scheduled Jobs:**
```python
# Daily job at 6 AM: Due date reminders
def send_due_reminders():
    due_soon = db.lendings.find({
        "status": "checked_out",
        "due_date": {"$gte": today, "$lte": today + 3.days}
    })
    
    for lending in due_soon:
        queue_notification(lending.member_id, "due_reminder", lending)

# Daily job at 2 AM: Expire reservations
def expire_old_reservations():
    expired = db.reservations.find({
        "status": "notified",
        "expires_at": {"$lt": now()}
    })
    
    for reservation in expired:
        cancel_reservation(reservation.id)
        notify_next_in_queue(reservation.book_id)

# Weekly job: Calculate popular books
def update_popular_books():
    popular = db.lendings.aggregate([
        {"$match": {"checkout_date": {"$gte": last_week}}},
        {"$group": {"_id": "$book_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 100}
    ])
    
    redis.setex("popular_books", 7*24*3600, json.dumps(popular))
```

## 9. Technology Stack

### 9.1 Backend Services

**Languages & Frameworks:**
- Java/Spring Boot: Lending, Fine services (transactional)
- Python/Django: Reservation, Analytics services
- Node.js/Express: Member, Notification, Digital Library services
- Python/Flask: Search service

### 9.2 Databases

**Relational:**
- PostgreSQL: Lendings, Fines, Reservations (ACID required)
- MySQL: Members, Membership Types

**NoSQL:**
- MongoDB: Books catalog, Book copies (flexible schema)
- Redis: Caching, Session management

**Search:**
- Elasticsearch: Full-text search

**Time-Series:**
- TimescaleDB: Analytics data

### 9.3 Message Queue

**RabbitMQ:**
- Notification delivery queue
- Reservation alerts
- Analytics events
- Background job processing

### 9.4 Infrastructure

**Cloud Platform:** AWS
- Compute: ECS for containers
- Load Balancer: ALB
- Storage: S3 for digital books and images
- CDN: CloudFront

**Monitoring:**
- Logging: ELK Stack
- Metrics: Prometheus + Grafana
- APM: New Relic
- Alerting: PagerDuty

### 9.5 Frontend

**Member Portal:**
- React.js: Web application
- React Native: Mobile apps

**Staff Portal:**
- React.js: Admin dashboard
- Barcode scanning integration

**Self-Service Kiosk:**
- Electron.js: Desktop application
- RFID reader integration

## 10. Interview Questions & Answers

### Q1: How do you prevent a book from being checked out to multiple members simultaneously?

**Answer:**
This is a classic concurrency problem. We use multiple mechanisms:

**1. Database-Level Locking:**

**Optimistic Locking:**
```sql
UPDATE book_copies 
SET status = 'checked_out', version = version + 1
WHERE copy_id = ? AND status = 'available' AND version = ?;

-- If affected rows = 0, checkout failed (book already taken or version changed)
```

**Pessimistic Locking:**
```sql
BEGIN TRANSACTION;

SELECT * FROM book_copies 
WHERE copy_id = ? AND status = 'available'
FOR UPDATE;  -- Lock row

-- Check if book is available
-- If available, create lending record and update status

COMMIT;
```

**2. Application-Level Locking (Redis):**
```python
def checkout_book(member_id, copy_id):
    lock_key = f"lock:copy:{copy_id}"
    lock_acquired = redis.set(lock_key, member_id, nx=True, ex=10)  # 10 sec TTL
    
    if not lock_acquired:
        return {"error": "Book is being checked out by another member"}
    
    try:
        # Check availability
        copy = db.book_copies.find_one({"copy_id": copy_id, "status": "available"})
        if not copy:
            return {"error": "Book not available"}
        
        # Create lending record
        lending = create_lending(member_id, copy_id)
        
        # Update copy status
        db.book_copies.update_one(
            {"copy_id": copy_id, "status": "available"},
            {"$set": {"status": "checked_out"}}
        )
        
        # Update availability count
        db.books.update_one(
            {"book_id": copy.book_id},
            {"$inc": {"statistics.available_copies": -1}}
        )
        
        return {"success": True, "lending": lending}
    
    finally:
        redis.delete(lock_key)
```

**3. Idempotency:**
- Use unique transaction IDs to prevent duplicate checkouts
- Store transaction ID in lending record
- If same transaction ID appears again, return existing lending

**4. Queue-Based Approach:**
For self-service kiosks with high concurrency:
```python
# Add checkout request to queue
checkout_request = {
    "request_id": uuid4(),
    "member_id": member_id,
    "copy_id": copy_id,
    "timestamp": now()
}
queue.enqueue("checkout_queue", checkout_request)

# Worker processes queue sequentially
def process_checkout_queue():
    while True:
        request = queue.dequeue("checkout_queue")
        result = checkout_book(request.member_id, request.copy_id)
        notify_member(request.member_id, result)
```

**Our Choice:** Combination of Redis distributed lock + optimistic locking for best balance of performance and consistency.

### Q2: How do you design the reservation system with waitlist management?

**Answer:**
Reservation system requires careful queue management and timely notifications:

**Data Model:**
```sql
reservations (
  reservation_id, book_id, member_id,
  requested_at, notified_at, expires_at,
  status, position_in_queue
)

-- Composite index for efficient queue queries
CREATE INDEX idx_queue ON reservations(book_id, status, requested_at);
```

**Queue Management:**

**Adding to Waitlist:**
```python
def reserve_book(member_id, book_id):
    # Check if book is available
    available_copies = db.books.find_one({"book_id": book_id}).available_copies
    if available_copies > 0:
        return {"error": "Book is available, please checkout directly"}
    
    # Check if member already has reservation
    existing = db.reservations.find_one({
        "member_id": member_id,
        "book_id": book_id,
        "status": {"$in": ["pending", "notified"]}
    })
    if existing:
        return {"error": "You already have a reservation for this book"}
    
    # Get current queue size
    queue_size = db.reservations.count_documents({
        "book_id": book_id,
        "status": "pending"
    })
    
    # Create reservation
    reservation = {
        "reservation_id": uuid4(),
        "book_id": book_id,
        "member_id": member_id,
        "requested_at": now(),
        "status": "pending",
        "position_in_queue": queue_size + 1
    }
    db.reservations.insert_one(reservation)
    
    # Estimate wait time
    avg_lending_period = 14  # days
    total_copies = db.books.find_one({"book_id": book_id}).total_copies
    estimated_wait = (queue_size / total_copies) * avg_lending_period
    
    return {
        "success": True,
        "position": queue_size + 1,
        "estimated_wait_days": int(estimated_wait)
    }
```

**Processing Returns (Book Becomes Available):**
```python
def on_book_return(copy_id):
    # Get book_id
    copy = db.book_copies.find_one({"copy_id": copy_id})
    book_id = copy.book_id
    
    # Check if there are pending reservations
    next_reservation = db.reservations.find_one({
        "book_id": book_id,
        "status": "pending"
    }, sort=[("requested_at", 1)])  # FIFO
    
    if next_reservation:
        # Hold book for reservation
        db.book_copies.update_one(
            {"copy_id": copy_id},
            {"$set": {"status": "reserved"}}
        )
        
        # Update reservation status
        expires_at = now() + timedelta(hours=48)  # 48-hour hold
        db.reservations.update_one(
            {"reservation_id": next_reservation.reservation_id},
            {"$set": {
                "status": "notified",
                "notified_at": now(),
                "expires_at": expires_at
            }}
        )
        
        # Send notification
        send_notification(
            next_reservation.member_id,
            "Your reserved book is available",
            {"book_id": book_id, "expires_at": expires_at}
        )
        
        # Update queue positions for remaining reservations
        update_queue_positions(book_id)
    else:
        # No reservations, mark as available
        db.book_copies.update_one(
            {"copy_id": copy_id},
            {"$set": {"status": "available"}}
        )
        db.books.update_one(
            {"book_id": book_id},
            {"$inc": {"statistics.available_copies": 1}}
        )
```

**Expiry Handling (Cron Job):**
```python
def expire_old_reservations():
    expired = db.reservations.find({
        "status": "notified",
        "expires_at": {"$lt": now()}
    })
    
    for reservation in expired:
        # Cancel expired reservation
        db.reservations.update_one(
            {"reservation_id": reservation.reservation_id},
            {"$set": {"status": "expired"}}
        )
        
        # Release the reserved copy
        db.book_copies.update_one(
            {"book_id": reservation.book_id, "status": "reserved"},
            {"$set": {"status": "available"}},
            limit=1
        )
        
        # Notify next in queue
        notify_next_in_queue(reservation.book_id)
        
        # Notify member about expiry
        send_notification(
            reservation.member_id,
            "Your reservation expired",
            {"book_id": reservation.book_id}
        )
```

**Checkout from Reservation:**
```python
def checkout_reserved_book(member_id, book_id):
    # Verify reservation
    reservation = db.reservations.find_one({
        "member_id": member_id,
        "book_id": book_id,
        "status": "notified",
        "expires_at": {"$gte": now()}
    })
    
    if not reservation:
        return {"error": "No valid reservation found"}
    
    # Find reserved copy
    copy = db.book_copies.find_one({
        "book_id": book_id,
        "status": "reserved"
    })
    
    # Checkout book
    lending = create_lending(member_id, copy.copy_id)
    
    # Mark reservation as fulfilled
    db.reservations.update_one(
        {"reservation_id": reservation.reservation_id},
        {"$set": {"status": "fulfilled", "fulfilled_at": now()}}
    )
    
    return {"success": True, "lending": lending}
```

**Priority Reservations:**
For faculty or research purposes:
```python
# Add priority field
reservations (
  ...,
  priority (normal, high, urgent),
  ...
)

# Sort by priority first, then requested_at
next_reservation = db.reservations.find_one({
    "book_id": book_id,
    "status": "pending"
}, sort=[("priority", -1), ("requested_at", 1)])
```

### Q3: How do you implement the fine calculation system?

**Answer:**
Fine calculation must be accurate, automatic, and fair:

**Fine Calculation Logic:**

```python
class FineCalculator:
    def calculate_overdue_fine(self, lending_record):
        """Calculate fine for overdue book"""
        due_date = lending_record.due_date
        return_date = lending_record.return_date or datetime.now()
        
        # Grace period
        grace_period_end = due_date + timedelta(days=1)
        if return_date <= grace_period_end:
            return Decimal('0.00')
        
        # Calculate days overdue (excluding grace period)
        days_overdue = (return_date - grace_period_end).days
        
        # Get fine rate from membership type
        membership_type = lending_record.member.membership_type
        fine_per_day = membership_type.fine_per_day
        
        # Calculate base fine
        base_fine = days_overdue * fine_per_day
        
        # Cap at book replacement cost
        book_price = lending_record.copy.price
        max_fine = book_price * Decimal('0.8')  # 80% of book price
        
        fine_amount = min(base_fine, max_fine)
        
        return round(fine_amount, 2)
    
    def calculate_lost_book_fine(self, lending_record):
        """Calculate fine for lost book"""
        book_price = lending_record.copy.price
        processing_fee = Decimal('10.00')
        
        # Overdue fine up to declaration date
        overdue_fine = self.calculate_overdue_fine(lending_record)
        
        # Total = replacement cost + processing fee + overdue fine
        total_fine = book_price + processing_fee + overdue_fine
        
        return round(total_fine, 2)
    
    def calculate_damaged_book_fine(self, lending_record, damage_level):
        """Calculate fine for damaged book"""
        book_price = lending_record.copy.price
        
        damage_multipliers = {
            "minor": Decimal('0.1'),    # 10% of price
            "moderate": Decimal('0.3'),  # 30% of price
            "severe": Decimal('0.7'),    # 70% of price
            "destroyed": Decimal('1.0')  # Full replacement
        }
        
        multiplier = damage_multipliers.get(damage_level, Decimal('0.3'))
        fine_amount = book_price * multiplier
        
        return round(fine_amount, 2)
```

**Automatic Fine Creation:**

```python
def on_book_return(lending_id, return_condition="good"):
    lending = db.lendings.find_one({"lending_id": lending_id})
    
    # Update lending record
    return_date = datetime.now()
    db.lendings.update_one(
        {"lending_id": lending_id},
        {"$set": {"return_date": return_date, "status": "returned"}}
    )
    
    # Calculate overdue fine
    if return_date > lending.due_date:
        calculator = FineCalculator()
        fine_amount = calculator.calculate_overdue_fine(lending)
        
        if fine_amount > 0:
            fine = {
                "fine_id": uuid4(),
                "lending_id": lending_id,
                "member_id": lending.member_id,
                "fine_type": "overdue",
                "fine_amount": fine_amount,
                "created_at": return_date,
                "status": "unpaid",
                "description": f"Overdue fine for '{lending.book.title}'"
            }
            db.fines.insert_one(fine)
            
            # Send notification
            send_notification(
                lending.member_id,
                f"Overdue fine: ${fine_amount}",
                fine
            )
    
    # Calculate damage fine
    if return_condition != "good":
        calculator = FineCalculator()
        damage_fine = calculator.calculate_damaged_book_fine(lending, return_condition)
        
        if damage_fine > 0:
            fine = {
                "fine_id": uuid4(),
                "lending_id": lending_id,
                "member_id": lending.member_id,
                "fine_type": "damaged",
                "fine_amount": damage_fine,
                "created_at": return_date,
                "status": "unpaid",
                "description": f"Damage fine for '{lending.book.title}' (Condition: {return_condition})"
            }
            db.fines.insert_one(fine)
    
    # Check if member should be suspended
    check_member_status(lending.member_id)
```

**Batch Fine Generation (Cron Job):**
```python
def generate_daily_fines():
    """Run daily to create fines for overdue books"""
    
    # Find all overdue lendings without return date
    overdue_lendings = db.lendings.find({
        "status": "checked_out",
        "due_date": {"$lt": datetime.now() - timedelta(days=1)},  # Past grace period
        "return_date": None
    })
    
    calculator = FineCalculator()
    
    for lending in overdue_lendings:
        # Check if fine already exists for today
        existing_fine = db.fines.find_one({
            "lending_id": lending.lending_id,
            "created_at": {"$gte": datetime.now().replace(hour=0, minute=0, second=0)}
        })
        
        if not existing_fine:
            # Calculate current fine amount
            fine_amount = calculator.calculate_overdue_fine(lending)
            
            # Create or update fine record
            # Option 1: Create daily fine records
            # Option 2: Update single fine record with accumulated amount
            
            # We'll use Option 2: Update accumulated fine
            db.fines.update_one(
                {"lending_id": lending.lending_id, "fine_type": "overdue"},
                {
                    "$set": {"fine_amount": fine_amount, "updated_at": now()},
                    "$setOnInsert": {
                        "fine_id": uuid4(),
                        "member_id": lending.member_id,
                        "fine_type": "overdue",
                        "status": "unpaid",
                        "created_at": now()
                    }
                },
                upsert=True
            )
```

**Member Suspension Logic:**
```python
def check_member_status(member_id):
    # Calculate total unpaid fines
    total_unpaid = db.fines.aggregate([
        {"$match": {"member_id": member_id, "status": "unpaid"}},
        {"$group": {"_id": None, "total": {"$sum": "$fine_amount"}}}
    ])
    
    total_amount = total_unpaid[0]["total"] if total_unpaid else 0
    
    # Update member record
    db.members.update_one(
        {"member_id": member_id},
        {"$set": {"total_unpaid_fines": total_amount}}
    )
    
    # Suspension threshold
    suspension_threshold = 50.00
    
    # Check for overdue books > 30 days
    severely_overdue = db.lendings.count_documents({
        "member_id": member_id,
        "status": "checked_out",
        "due_date": {"$lt": datetime.now() - timedelta(days=30)}
    })
    
    # Suspend member if conditions met
    if total_amount >= suspension_threshold or severely_overdue > 0:
        db.members.update_one(
            {"member_id": member_id},
            {"$set": {"status": "suspended", "suspended_at": now()}}
        )
        
        send_notification(
            member_id,
            "Account Suspended",
            {"reason": "Unpaid fines or severely overdue books", "total_fines": total_amount}
        )
    elif total_amount == 0:
        # Reactivate if all fines paid
        db.members.update_one(
            {"member_id": member_id, "status": "suspended"},
            {"$set": {"status": "active", "suspended_at": None}}
        )
```

**Fine Payment:**
```python
def pay_fine(fine_id, payment_method, amount):
    fine = db.fines.find_one({"fine_id": fine_id})
    
    if fine.fine_amount != amount:
        return {"error": "Payment amount doesn't match fine amount"}
    
    # Process payment via payment gateway
    transaction = process_payment(payment_method, amount)
    
    if transaction.status == "success":
        # Update fine status
        db.fines.update_one(
            {"fine_id": fine_id},
            {"$set": {
                "status": "paid",
                "paid_at": now(),
                "payment_transaction_id": transaction.id
            }}
        )
        
        # Check if member can be reactivated
        check_member_status(fine.member_id)
        
        # Generate receipt
        receipt = generate_receipt(fine, transaction)
        
        return {"success": True, "receipt_url": receipt.url}
    else:
        return {"error": "Payment failed", "message": transaction.error}
```

**Fine Waiver (Staff Action):**
```python
def waive_fine(fine_id, staff_id, reason):
    """Allow staff to waive fines in special circumstances"""
    
    # Validate staff has permission
    staff = db.staff.find_one({"staff_id": staff_id})
    if not staff.can_waive_fines:
        return {"error": "Insufficient permissions"}
    
    # Update fine
    db.fines.update_one(
        {"fine_id": fine_id},
        {"$set": {
            "status": "waived",
            "waived_at": now(),
            "waived_by": staff_id,
            "waiver_reason": reason
        }}
    )
    
    # Audit log
    log_action("fine_waived", {
        "fine_id": fine_id,
        "staff_id": staff_id,
        "reason": reason
    })
    
    return {"success": True}
```

This comprehensive library management system design covers all aspects of modern library operations, from physical book lending to digital resource management, with emphasis on data consistency, scalability, and user experience.
