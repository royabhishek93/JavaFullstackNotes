# Instagram Likes Feature - End-to-End System Design

## Table of Contents
1. [Overview](#overview)
2. [Functional Requirements](#functional-requirements)
3. [Non-Functional Requirements](#non-functional-requirements)
4. [Scale Estimates](#scale-estimates)
5. [High-Level Architecture](#high-level-architecture)
6. [Component Design](#component-design)
7. [Database Schema](#database-schema)
8. [API Design](#api-design)
9. [Sequence Diagrams](#sequence-diagrams)
10. [Data Flow](#data-flow)
11. [Caching Strategy](#caching-strategy)
12. [Consistency Models](#consistency-models)
13. [Failure Scenarios](#failure-scenarios)
14. [Interview Follow-up Questions](#interview-follow-up-questions)

---

## Overview

The Instagram Likes feature allows users to:
- Like/unlike posts
- View like counts on posts
- See who liked a post
- Receive notifications when someone likes their post

**Key Challenges:**
- High write throughput (millions of likes per minute)
- Race conditions (double-clicks, concurrent requests)
- Real-time count updates
- Fan-out to followers' feeds
- Eventual consistency vs strong consistency

---

## Functional Requirements

### Core Features
1. **Like a Post**: User can like a post (idempotent operation)
2. **Unlike a Post**: User can remove their like
3. **View Like Count**: Display accurate like count on posts
4. **View Likers List**: Show list of users who liked a post
5. **Like Notifications**: Notify post owner when someone likes their content
6. **Like Status**: Show if current user has already liked a post

### Edge Cases
- Double-click protection
- Rapid like/unlike toggling
- Deleted posts/users
- Privacy settings (private accounts)

---

## Non-Functional Requirements

| Requirement | Target | Priority |
|-------------|--------|----------|
| **Availability** | 99.99% | Critical |
| **Latency (p99)** | < 200ms | High |
| **Write Throughput** | 50K likes/sec | Critical |
| **Read Throughput** | 500K reads/sec | High |
| **Consistency** | Eventual (count), Strong (user state) | High |
| **Data Durability** | 99.999999999% | Critical |
| **Idempotency** | 100% | Critical |

---

## Scale Estimates

### Assumptions
- **Total Users**: 2 billion
- **Daily Active Users (DAU)**: 500 million
- **Posts per day**: 100 million
- **Likes per post (avg)**: 50
- **Likes per day**: 5 billion
- **Likes per second (avg)**: ~58K
- **Likes per second (peak)**: ~200K

### Storage Estimates
```
Single Like Record: 
- user_id: 8 bytes
- post_id: 8 bytes  
- timestamp: 8 bytes
- metadata: 8 bytes
Total: 32 bytes

Daily Storage = 5B likes × 32 bytes = 160 GB/day
Yearly Storage = 160 GB × 365 = ~58 TB/year
5-year Storage = 290 TB
```

### Bandwidth Estimates
```
Write: 58K likes/sec × 32 bytes = 1.86 MB/sec
Read (view counts): 500K reads/sec × 100 bytes = 50 MB/sec
Total: ~52 MB/sec
```

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│  (iOS App, Android App, Web Browser, API Clients)              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CDN / EDGE LAYER                            │
│         (CloudFront, Akamai - Static Assets, Caching)           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LOAD BALANCER LAYER                           │
│        (AWS ELB, NGINX - SSL Termination, Rate Limiting)        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API GATEWAY LAYER                            │
│    (Authentication, Authorization, Request Routing, Logging)    │
└────────────────────────────┬────────────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Like Service   │ │  Count Service  │ │  Feed Service   │
│  (Write Path)   │ │  (Read Path)    │ │  (Fan-out)      │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                       CACHING LAYER                              │
│        Redis Cluster (Like Status, Counts, Hot Posts)           │
└────────────────────────────┬────────────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Primary DB    │ │   Analytics DB  │ │  Graph DB       │
│   (Cassandra)   │ │   (Clickhouse)  │ │  (Neo4j)        │
│                 │ │                 │ │                 │
│ - Likes Table   │ │ - Like Events   │ │ - Relationships │
│ - Count Table   │ │ - Aggregations  │ │ - Followers     │
└─────────────────┘ └─────────────────┘ └─────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MESSAGE QUEUE LAYER                           │
│     Kafka (Async Processing, Fan-out, Notifications)            │
└────────────────────────────┬────────────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Notification   │ │   Analytics     │ │  ML Pipeline    │
│    Service      │ │   Processor     │ │  (Recommendations)│
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## Component Design

### 1. Like Service (Write Path)

```
┌─────────────────────────────────────────────────────────────────┐
│                        LIKE SERVICE                              │
└─────────────────────────────────────────────────────────────────┘

Components:
┌──────────────────┐
│  API Endpoints   │
│  - POST /like    │
│  - DELETE /like  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Request Handler │
│  - Validation    │
│  - Auth Check    │
│  - Rate Limiting │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐        ┌──────────────────┐
│  Idempotency     │───────▶│  Redis Check     │
│  Layer           │        │  (Dedup Window)  │
└────────┬─────────┘        └──────────────────┘
         │
         ▼
┌──────────────────┐
│  Transaction     │
│  Manager         │
│  - Write Lock    │
│  - Retry Logic   │
└────────┬─────────┘
         │
         ├──────────────────┬──────────────────┐
         ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Write to DB  │  │ Update Cache │  │ Publish Event│
│ (Cassandra)  │  │ (Redis)      │  │ (Kafka)      │
└──────────────┘  └──────────────┘  └──────────────┘
```

**Key Responsibilities:**
- Validate like request (user exists, post exists, permissions)
- Check idempotency (prevent duplicate likes)
- Write to database atomically
- Update cache (like count, user's like status)
- Publish event to Kafka (for notifications, analytics, feed updates)

### 2. Count Service (Read Path)

```
┌─────────────────────────────────────────────────────────────────┐
│                        COUNT SERVICE                             │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│  API Endpoints   │
│  - GET /count    │
│  - GET /likers   │
│  - GET /status   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Cache Layer     │
│  (Redis)         │
│  - L1: Hot Posts │
│  - L2: Recent    │
└────────┬─────────┘
         │
         │ Cache Miss
         ▼
┌──────────────────┐
│  DB Query        │
│  (Cassandra)     │
│  - Count Query   │
│  - Pagination    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Response        │
│  Formatter       │
│  - Aggregation   │
│  - Hydration     │
└──────────────────┘
```

**Key Responsibilities:**
- Serve like counts (with caching)
- Return list of users who liked (paginated)
- Check if current user has liked a post
- Handle high read throughput

### 3. Notification Service

```
┌─────────────────────────────────────────────────────────────────┐
│                    NOTIFICATION SERVICE                          │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│  Kafka Consumer  │
│  (Like Events)   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Filter Logic    │
│  - Self-like     │
│  - User Settings │
│  - Privacy       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐        ┌──────────────────┐
│  Batching        │───────▶│  Aggregation     │
│  (10 sec window) │        │  (Group likes)   │
└────────┬─────────┘        └──────────────────┘
         │
         ▼
┌──────────────────┐
│  Notification    │
│  Delivery        │
│  - Push (FCM)    │
│  - In-app        │
│  - Email (batch) │
└──────────────────┘
```

---

## Database Schema

### Cassandra Tables (Primary Storage)

#### 1. Likes Table (Write-Optimized)
```sql
CREATE TABLE likes (
    post_id UUID,
    user_id UUID,
    created_at TIMESTAMP,
    like_type TEXT,              -- 'like', 'love', 'wow' (future)
    PRIMARY KEY (post_id, user_id)
) WITH CLUSTERING ORDER BY (user_id ASC);

-- Index for user's liked posts
CREATE INDEX ON likes (user_id);
```

#### 2. Like Counts Table (Read-Optimized)
```sql
CREATE TABLE like_counts (
    post_id UUID PRIMARY KEY,
    count COUNTER,
    last_updated TIMESTAMP
);
```

#### 3. User Like Status (Quick Lookup)
```sql
CREATE TABLE user_like_status (
    user_id UUID,
    post_id UUID,
    liked BOOLEAN,
    created_at TIMESTAMP,
    PRIMARY KEY (user_id, post_id)
);
```

#### 4. Likers List (For "View All Likers")
```sql
CREATE TABLE post_likers (
    post_id UUID,
    bucket INT,                  -- Sharding key (0-99)
    user_id UUID,
    username TEXT,
    profile_pic_url TEXT,
    created_at TIMESTAMP,
    PRIMARY KEY ((post_id, bucket), created_at, user_id)
) WITH CLUSTERING ORDER BY (created_at DESC);
```

### Redis Cache Schema

```
# Like Count Cache
Key: "like:count:{post_id}"
Value: Integer (count)
TTL: 1 hour

# User Like Status Cache
Key: "like:status:{user_id}:{post_id}"
Value: "1" (liked) or "0" (not liked)
TTL: 1 hour

# Likers List Cache (First 100)
Key: "like:likers:{post_id}"
Value: List of user_ids (Redis List)
TTL: 30 minutes

# Hot Posts Cache (Trending)
Key: "like:hot:{time_bucket}"
Value: Sorted Set (post_id, score=like_count)
TTL: 5 minutes

# Idempotency Cache
Key: "like:idempotent:{user_id}:{post_id}"
Value: "processing"
TTL: 5 seconds
```

---

## API Design

### 1. Like a Post
```http
POST /api/v1/posts/{post_id}/like
Authorization: Bearer {token}

Request Body:
{
    "like_type": "like"  // future: "love", "wow", etc.
}

Response (200 OK):
{
    "success": true,
    "post_id": "123e4567-e89b-12d3-a456-426614174000",
    "like_count": 1542,
    "user_liked": true,
    "timestamp": "2026-04-16T10:30:00Z"
}

Response (409 Conflict - Already Liked):
{
    "success": false,
    "error": "POST_ALREADY_LIKED",
    "message": "You have already liked this post"
}

Response (429 Too Many Requests):
{
    "success": false,
    "error": "RATE_LIMIT_EXCEEDED",
    "retry_after": 5
}
```

### 2. Unlike a Post
```http
DELETE /api/v1/posts/{post_id}/like
Authorization: Bearer {token}

Response (200 OK):
{
    "success": true,
    "post_id": "123e4567-e89b-12d3-a456-426614174000",
    "like_count": 1541,
    "user_liked": false,
    "timestamp": "2026-04-16T10:31:00Z"
}
```

### 3. Get Like Count
```http
GET /api/v1/posts/{post_id}/likes/count
Authorization: Bearer {token}

Response (200 OK):
{
    "post_id": "123e4567-e89b-12d3-a456-426614174000",
    "like_count": 1542,
    "user_liked": true
}
```

### 4. Get Likers List
```http
GET /api/v1/posts/{post_id}/likes?limit=50&cursor={cursor}
Authorization: Bearer {token}

Response (200 OK):
{
    "post_id": "123e4567-e89b-12d3-a456-426614174000",
    "total_count": 1542,
    "users": [
        {
            "user_id": "user-123",
            "username": "john_doe",
            "profile_pic_url": "https://cdn.instagram.com/...",
            "liked_at": "2026-04-16T10:30:00Z"
        },
        ...
    ],
    "next_cursor": "base64_encoded_cursor",
    "has_more": true
}
```

### 5. Batch Get Like Status
```http
POST /api/v1/posts/likes/batch
Authorization: Bearer {token}

Request Body:
{
    "post_ids": [
        "123e4567-e89b-12d3-a456-426614174000",
        "223e4567-e89b-12d3-a456-426614174001",
        ...
    ]
}

Response (200 OK):
{
    "results": [
        {
            "post_id": "123e4567-e89b-12d3-a456-426614174000",
            "like_count": 1542,
            "user_liked": true
        },
        ...
    ]
}
```

---

## Sequence Diagrams

### 1. Like a Post Flow

```
User          Client App      API Gateway      Like Service      Redis          Cassandra      Kafka
 |                |                |                |               |                |             |
 |─ Tap Like ────▶|                |                |               |                |             |
 |                |                |                |               |                |             |
 |                |─ POST /like ──▶|                |               |                |             |
 |                |                |                |               |                |             |
 |                |                |─ Authenticate ─|               |                |             |
 |                |                |◀───────────────|               |                |             |
 |                |                |                |               |                |             |
 |                |                |─ Forward ─────▶|               |                |             |
 |                |                |                |               |                |             |
 |                |                |                |─ Check Idempotency ──────────▶|             |
 |                |                |                |◀──────────────────────────────|             |
 |                |                |                |         (Not exists)           |             |
 |                |                |                |               |                |             |
 |                |                |                |─ SET idempotent_key ──────────▶|             |
 |                |                |                |               |                |             |
 |                |                |                |─ Check current status ─────────▶|            |
 |                |                |                |◀────────────────────────────────|            |
 |                |                |                |         (Not liked)             |            |
 |                |                |                |               |                |             |
 |                |                |                |─ INSERT like record ───────────────────────▶|
 |                |                |                |◀────────────────────────────────────────────|
 |                |                |                |               (Success)        |             |
 |                |                |                |               |                |             |
 |                |                |                |─ INCR like_count ──────────────▶|            |
 |                |                |                |◀────────────────────────────────|            |
 |                |                |                |               (1543)            |            |
 |                |                |                |               |                |             |
 |                |                |                |─ SET user_liked ───────────────▶|            |
 |                |                |                |               |                |             |
 |                |                |                |─ Publish event ────────────────────────────▶|
 |                |                |                |               |                |             |
 |                |                |◀─ Response ────|               |                |             |
 |                |◀─ 200 OK ──────|         (like_count: 1543)     |                |             |
 |◀─ UI Update ───|                |                |               |                |             |
 | (Animate ❤️)   |                |                |               |                |             |
```

### 2. View Like Count Flow (Cache Hit)

```
User          Client App      API Gateway      Count Service      Redis          Cassandra
 |                |                |                |                |                |
 |─ View Post ───▶|                |                |                |                |
 |                |                |                |                |                |
 |                |─ GET /count ──▶|                |                |                |
 |                |                |                |                |                |
 |                |                |─ Forward ─────▶|                |                |
 |                |                |                |                |                |
 |                |                |                |─ GET like_count ──────────────▶|
 |                |                |                |◀────────────────────────────────|
 |                |                |                |         (1543 - Cache Hit)      |
 |                |                |                |                |                |
 |                |                |◀─ Response ────|                |                |
 |                |◀─ 200 OK ──────|         (like_count: 1543)      |                |
 |◀─ Display ─────|                |                |                |                |
 | (1.5K likes)   |                |                |                |                |
```

### 3. View Likers List Flow

```
User          Client App      API Gateway      Count Service      Redis          Cassandra
 |                |                |                |                |                |
 |─ Tap Likes ───▶|                |                |                |                |
 |                |                |                |                |                |
 |                |─ GET /likers ─▶|                |                |                |
 |                |                |                |                |                |
 |                |                |─ Forward ─────▶|                |                |
 |                |                |                |                |                |
 |                |                |                |─ GET likers_list ─────────────▶|
 |                |                |                |◀────────────────────────────────|
 |                |                |                |      (First 100 - Cache Hit)    |
 |                |                |                |                |                |
 |                |                |                |─ Hydrate user data ────────────▶|
 |                |                |                |◀────────────────────────────────|
 |                |                |                |   (usernames, profile pics)     |
 |                |                |                |                |                |
 |                |                |◀─ Response ────|                |                |
 |                |◀─ 200 OK ──────|                |                |                |
 |◀─ Display ─────|                |                |                |                |
 | (List view)    |                |                |                |                |
```

### 4. Double-Click Protection Flow

```
User          Client App      API Gateway      Like Service      Redis
 |                |                |                |                |
 |─ Click Like ──▶|                |                |                |
 |                |─ POST /like ──▶|                |                |
 |                |                |─ Forward ─────▶|                |
 |                |                |                |─ SET NX idempotent_key ─────▶|
 |                |                |                |◀──────────────────────────────|
 |                |                |                |         (OK - Lock acquired)  |
 |─ Click Again ─▶|                |                |                |
 |  (100ms later) |                |                |                |
 |                |─ POST /like ──▶|                |                |
 |                |                |─ Forward ─────▶|                |
 |                |                |                |─ SET NX idempotent_key ─────▶|
 |                |                |                |◀──────────────────────────────|
 |                |                |                |    (nil - Lock exists)        |
 |                |                |◀─ 409 ─────────|                |
 |                |◀─ Conflict ────|   "Request in progress"         |
 |◀─ Ignore ──────| (Client dedupes)                |                |
```

---

## Data Flow

### Write Path (Like Action)

```
┌──────────────────────────────────────────────────────────────────┐
│                         WRITE PATH                                │
└──────────────────────────────────────────────────────────────────┘

[Client Request]
      │
      ▼
[Rate Limiter] ──(429 if exceeded)──▶ [Return Error]
      │
      ▼
[Idempotency Check (Redis)]
      │
      ├─(Already processing)─▶ [Return 409 Conflict]
      │
      ├─(Already liked)──────▶ [Return current state]
      │
      ▼
[Acquire Lock]
      │
      ▼
[Write to Cassandra]
      │
      ├─(Write Failure)──▶ [Retry 3x] ──(All failed)──▶ [Return 500]
      │                          │
      │                          └─(Success)─┐
      ▼                                      │
[Update Success] ◀─────────────────────────-┘
      │
      ├──────────┬──────────┬──────────┐
      ▼          ▼          ▼          ▼
[Update      [Update    [Publish   [Release
 Redis       Counter    to Kafka    Lock]
 Cache]      Table]     Queue]
      │          │          │          │
      └──────────┴──────────┴──────────┘
                    │
                    ▼
            [Return 200 OK]


[Async Processing from Kafka]
      │
      ├──────────┬──────────┬──────────┐
      ▼          ▼          ▼          ▼
[Notification] [Analytics] [Feed     [ML
 Service]      [Pipeline]  Update]   Pipeline]
```

### Read Path (Get Like Count)

```
┌──────────────────────────────────────────────────────────────────┐
│                         READ PATH                                 │
└──────────────────────────────────────────────────────────────────┘

[Client Request]
      │
      ▼
[L1 Cache Check (Redis)]
      │
      ├─(Cache Hit)──▶ [Return from Cache] ──▶ [Response]
      │
      ▼
[L2 Cache Check (Redis - Backup)]
      │
      ├─(Cache Hit)──▶ [Return from Cache] ──▶ [Response]
      │
      ▼
[Query Cassandra Counter Table]
      │
      ├─(Success)──▶ [Cache Result] ──▶ [Response]
      │                   │
      │                   ├─▶ [Update L1]
      │                   └─▶ [Update L2]
      │
      ▼
[Fallback: Query Likes Table COUNT]
      │
      ├─(Success)──▶ [Cache Result] ──▶ [Response]
      │
      ▼
[Return Error 500]
```

---

## Caching Strategy

### Multi-Level Caching

```
┌─────────────────────────────────────────────────────────────────┐
│                      CACHING ARCHITECTURE                        │
└─────────────────────────────────────────────────────────────────┘

Layer 1: Client-Side Cache (Mobile App)
├─ Like counts (1 minute TTL)
├─ User's own like status (5 minutes TTL)
└─ Recently viewed posts

Layer 2: CDN Cache (CloudFront)
├─ Static assets (profile pics, etc.)
└─ Public aggregated stats (1 minute TTL)

Layer 3: Redis Cluster (Primary Cache)
├─ Hot Posts (like counts) - 1 hour TTL
├─ User like status - 1 hour TTL
├─ Likers list (first 100) - 30 min TTL
├─ Trending posts - 5 min TTL
└─ Idempotency keys - 5 sec TTL

Layer 4: Database (Cassandra)
├─ All like records (persistent)
└─ Counter table (persistent)
```

### Cache Invalidation Strategy

```
Invalidation Event               Action
─────────────────────────────────────────────────────────────
User likes post              ──▶ Invalidate: like count cache
                                 Update: user like status cache
                                 Append: likers list cache

User unlikes post            ──▶ Invalidate: like count cache
                                 Update: user like status cache
                                 Remove: from likers list cache

Post deleted                 ──▶ Invalidate: all post-related caches
                                 (Use cache key pattern matching)

User deleted                 ──▶ Background job to clean up
                                 (Async - not time-critical)
```

### Cache Warming Strategy

```
Scenario                          Strategy
─────────────────────────────────────────────────────────────
New post published            ──▶ Pre-warm: like count = 0
                                  Pre-warm: user like status

Trending post                 ──▶ Replicate to multiple cache nodes
                                  Increase TTL to 24 hours

Celebrity post                ──▶ Pre-allocate sharded counters
                                  Use dedicated cache cluster

Cache server restart          ──▶ Prioritized replay from DB:
                                  1. Hot posts (top 10K)
                                  2. Recent posts (last 1 hour)
                                  3. Background fill
```

---

## Consistency Models

### Strong Consistency (Critical Operations)

**User's Like Status**
```
Requirement: User must never see conflicting state
Implementation:
- Read-your-writes consistency
- Single-row transactions in Cassandra
- Redis cache synchronized immediately
- No eventual consistency window

Example:
User likes → Immediately sees liked state
User unlikes → Immediately sees unliked state
```

### Eventual Consistency (Non-Critical)

**Like Count Display**
```
Requirement: Approximate counts acceptable (±1-5%)
Implementation:
- Counter updates batched every 100ms
- Cache updates asynchronous
- Acceptable lag: up to 5 seconds

Example:
Actual count: 1543
Displayed: 1541-1545 (acceptable range)
Eventually converges to 1543
```

### Consistency Trade-offs

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONSISTENCY SPECTRUM                          │
└─────────────────────────────────────────────────────────────────┘

Strong ◀──────────────────────────────────────────────────▶ Eventual
   │                                                            │
   │                                                            │
   ├─ User like status (MUST be accurate)                     │
   │                                                            │
   ├─ Idempotency (MUST prevent duplicates)                   │
   │                                                            │
   │                                                            │
   │          ├─ Exact like count (Nice to have)               │
   │                                                            │
   │                    ├─ Likers list order (OK if delayed)   │
   │                                                            │
   │                          ├─ Analytics aggregations        │
   │                                                            │
   │                                ├─ ML training data ───────┤
```

---

## Failure Scenarios & Mitigation

### 1. Database Write Failure

```
Scenario: Cassandra write fails
Impact: Like not recorded
Mitigation:
├─ Retry with exponential backoff (3 attempts)
├─ Write to dead letter queue (DLQ)
├─ Alert on-call engineer
└─ Return 500 to client (user can retry)

Recovery:
├─ Replay from DLQ once DB is healthy
└─ Deduplicate using idempotency keys
```

### 2. Cache Failure (Redis Down)

```
Scenario: Redis cluster unavailable
Impact: High DB load, slower responses
Mitigation:
├─ Circuit breaker pattern (fail fast)
├─ Fallback to DB reads directly
├─ Rate limit aggressive clients
└─ Scale up Cassandra read capacity

Recovery:
├─ Redis auto-failover to replica
├─ Cache warm-up from DB (top 10K posts)
└─ Gradual traffic restoration
```

### 3. Kafka Queue Backlog

```
Scenario: Notification service slow/down
Impact: Notifications delayed, Kafka lag increases
Mitigation:
├─ Monitor consumer lag (alert at 1M messages)
├─ Auto-scale consumer instances
├─ Batch processing (trade latency for throughput)
└─ Drop non-critical notifications if lag > 10M

Recovery:
├─ Catch-up processing (parallel consumers)
├─ Skip expired notifications (>1 hour old)
└─ Prioritize recent events
```

### 4. Thundering Herd (Celebrity Post)

```
Scenario: Celebrity posts get 10M likes in 1 minute
Impact: Database hotspot, cache contention
Mitigation:
├─ Sharded counters (split count across 100 shards)
├─ Write coalescing (batch 100 likes per DB write)
├─ Dedicated cache cluster for hot posts
└─ Rate limiting per post (max 100K likes/sec)

Example:
Normal post: Single counter
Hot post: 100 shards → Aggregate on read
post_count = sum(shard_0 to shard_99)
```

### 5. Double-Click Race Condition

```
Scenario: User clicks like twice within 50ms
Impact: Duplicate likes, incorrect count
Mitigation:
├─ Client-side debouncing (300ms)
├─ Idempotency key in Redis (5 sec TTL)
├─ Unique constraint in DB (post_id, user_id)
└─ Return 409 Conflict for duplicates

Flow:
Request 1: Acquires lock → Processes → Releases
Request 2: Lock exists → Returns 409 immediately
```

### 6. Split-Brain (Network Partition)

```
Scenario: Network partition between data centers
Impact: Conflicting writes to same post
Mitigation:
├─ Last-write-wins (LWW) with timestamp
├─ Cassandra's eventual consistency handles merges
├─ Conflict-free Replicated Data Type (CRDT) for counters
└─ Vector clocks for causality tracking

Recovery:
├─ Automatic conflict resolution
├─ Manual reconciliation if needed (rare)
└─ Alert for investigation
```

---

## Interview Follow-up Questions

### 1. Scale & Performance

**Q: How would you handle 1 million likes per second during a Super Bowl ad?**

```
Answer:
1. Pre-scaling:
   - Scale Cassandra cluster 10x (predictive)
   - Warm up cache clusters
   - Increase Kafka partition count
   - Add read replicas

2. Write Optimization:
   - Batch writes (100 likes per DB transaction)
   - Sharded counters (1000 shards for hot posts)
   - Async processing (all non-critical operations)
   - Drop low-priority notifications

3. Read Optimization:
   - CDN for count display (5 sec stale is OK)
   - Client-side aggregation
   - Serve from cache only (no DB reads)

4. Monitoring:
   - Real-time dashboard
   - Auto-scaling triggers
   - PagerDuty alerts for P0 metrics
```

**Q: What if Redis goes down completely?**

```
Answer:
1. Immediate (< 1 second):
   - Circuit breaker opens
   - Fallback to DB reads
   - Disable write-through cache updates

2. Short-term (< 5 minutes):
   - Redis failover to replica
   - If replica also down, deploy new Redis cluster
   - Enable read-only mode for likes (display only)

3. Recovery:
   - Cache warm-up job (prioritized by recency)
   - Gradual traffic shift (10% → 50% → 100%)
   - Monitor DB load during recovery

4. Prevention:
   - Multi-region Redis replication
   - Persistent snapshots every 5 minutes
   - Automated health checks and failover
```

---

### 2. Consistency & Correctness

**Q: How do you prevent double-counting a like?**

```
Answer:
Defense in Depth (Multiple Layers):

Layer 1: Client-Side
- Disable button after click (UI state)
- Debounce rapid clicks (300ms)

Layer 2: API Gateway
- Request deduplication (5 sec window)
- Rate limiting per user (10 likes/sec)

Layer 3: Like Service
- Idempotency key in Redis
  Key: "idempotent:{user_id}:{post_id}"
  TTL: 5 seconds
  SET NX (only if not exists)

Layer 4: Database
- Unique constraint on (post_id, user_id)
- Cassandra's lightweight transactions (CAS)
  INSERT IF NOT EXISTS

Result:
Even if all layers fail, DB constraint guarantees uniqueness
```

**Q: How do you ensure the like count is accurate?**

```
Answer:
Trade-off: Strong Consistency vs Performance

Option 1: Strong Consistency (NOT recommended)
- Count(*) on every read
- Distributed locks for writes
- Result: Slow (100ms+), doesn't scale

Option 2: Eventual Consistency (Recommended)
- Counter table (fast, eventually consistent)
- Reconciliation job (nightly)
- Acceptable drift: ±0.1%

Implementation:
1. Real-time: Counter table (INCR/DECR)
2. Hourly: Compare counter vs COUNT(*)
3. Daily: Full reconciliation job
4. Alert if drift > 1%

Special Cases:
- Hot posts: Sharded counters (sum on read)
- Celebrity posts: Accept eventual consistency
- User's own posts: Strongly consistent
```

---

### 3. Monitoring & Observability

**Q: What metrics would you monitor?**

```
Answer:
Golden Signals:

1. Latency:
   - P50, P95, P99 for like/unlike API
   - Target: P99 < 200ms
   - Alert: P99 > 500ms

2. Traffic:
   - Likes per second (overall)
   - Likes per post (detect hot posts)
   - Alert: Sudden spike (>10x baseline)

3. Errors:
   - 4xx rate (client errors)
   - 5xx rate (server errors)
   - Alert: Error rate > 0.1%

4. Saturation:
   - Database CPU (< 70%)
   - Redis memory (< 80%)
   - Kafka consumer lag (< 1M messages)

Business Metrics:
   - Like rate per user (engagement)
   - Unlike rate (dissatisfaction indicator)
   - Time to notification (delivery SLA)

Dashboards:
   - Real-time: Grafana (1 sec resolution)
   - Historical: Kibana (hourly aggregates)
   - Alerts: PagerDuty (P0/P1/P2 severity)
```

**Q: How would you debug a "likes not counting" issue?**

```
Answer:
Debugging Process:

1. Scope the Problem:
   - Specific post? → Check post permissions
   - Specific user? → Check user account status
   - All users? → System-wide issue
   - Time range? → Recent deploy correlation

2. Check Logs:
   - Client logs (request sent?)
   - API Gateway logs (request received?)
   - Like Service logs (processed?)
   - Database logs (write succeeded?)

3. Trace Request:
   - Use request_id to trace end-to-end
   - Check each hop in distributed tracing (Jaeger)
   - Identify where request failed

4. Verify Data:
   - Check Cassandra: SELECT * FROM likes WHERE...
   - Check Redis: GET like:count:{post_id}
   - Check Kafka: Consumer lag

5. Hypothesis Testing:
   - Reproduce in staging
   - Check recent config changes
   - Review recent deploys

6. Resolution:
   - Immediate: Rollback if recent deploy
   - Short-term: Hotfix
   - Long-term: Root cause analysis (RCA)
```

---

### 4. Database & Storage

**Q: Why Cassandra over MySQL for likes?**

```
Answer:
Cassandra Advantages:

1. Write Scalability:
   - Linear scale (add nodes = more throughput)
   - No single write bottleneck
   - Handles 50K writes/sec easily

2. Partition Tolerance:
   - Multi-datacenter replication
   - No single point of failure
   - Eventual consistency model

3. Data Model:
   - Wide column store (efficient for time-series)
   - No JOINs needed (likes are simple)
   - Compaction handles deletes

MySQL Disadvantages:
   - Single-leader writes (bottleneck)
   - Sharding complexity (manual)
   - JOIN overhead (not needed here)

Trade-offs:
- Cassandra: No strong consistency, No transactions
- MySQL: Better for complex queries, Strong consistency

For likes: Cassandra wins (write-heavy, simple queries)
```

**Q: How would you design the database schema to support "reactions" (like, love, wow, etc.)?**

```
Answer:
Schema Evolution:

Current (v1): Binary like/unlike
┌────────────────────────────┐
│ likes                      │
├────────────────────────────┤
│ post_id | user_id | created│
└────────────────────────────┘

Future (v2): Multiple reactions
┌──────────────────────────────────────────┐
│ reactions                                │
├──────────────────────────────────────────┤
│ post_id | user_id | reaction_type | time │
│ UUID    | UUID    | TEXT          | TS   │
└──────────────────────────────────────────┘

Reaction types: "like", "love", "wow", "sad", "angry"

Counter Table:
┌──────────────────────────────────────────┐
│ reaction_counts                          │
├──────────────────────────────────────────┤
│ post_id | reaction_type | count          │
│ UUID    | TEXT          | COUNTER        │
└──────────────────────────────────────────┘

Cache Schema:
Key: "reactions:{post_id}"
Value: JSON { "like": 100, "love": 50, "wow": 10 }

Migration Strategy:
1. Add reaction_type column (default "like")
2. Dual-write (old + new tables)
3. Backfill old data
4. Switch reads to new table
5. Drop old table
```

---

### 5. Security & Privacy

**Q: How do you prevent like abuse (bots, spam)?**

```
Answer:
Multi-Layer Defense:

1. Rate Limiting:
   - Per user: 10 likes/sec, 1000 likes/hour
   - Per IP: 100 likes/sec
   - Per post: 100K likes/sec (thundering herd)

2. CAPTCHA:
   - Trigger after 50 rapid likes
   - Re-verify if suspicious pattern

3. Bot Detection:
   - ML model (features: click speed, patterns, device)
   - Behavioral analysis (human vs bot patterns)
   - Score-based: 0-100 (block if < 20)

4. Account Reputation:
   - New accounts: Lower rate limits
   - Verified accounts: Higher limits
   - Previously banned: Stricter checks

5. Monitoring:
   - Anomaly detection (sudden spike in likes)
   - Graph analysis (like rings, coordinated behavior)
   - Manual review queue for flagged accounts

6. Enforcement:
   - Soft ban: Shadow ban likes (don't count)
   - Hard ban: Account suspension
   - Legal: Report to authorities (if fraud)
```

**Q: How do you handle private accounts?**

```
Answer:
Privacy Controls:

1. Permission Check (Before Like):
   ├─ Is post public? → Allow anyone
   ├─ Is user following poster? → Allow
   ├─ Is user tagged in post? → Allow
   └─ Otherwise → Deny (403 Forbidden)

2. Visibility Rules (Who Can See Likers):
   ├─ Post owner: See all likers
   ├─ Followers: See mutual followers' likes
   ├─ Non-followers: See count only (no names)
   └─ Private account: Hidden count

3. Notification Privacy:
   ├─ Public post: Notify owner + followers
   ├─ Private post: Notify owner only
   └─ User can disable notifications (settings)

4. Search & Discovery:
   ├─ Private account likes: Not indexed
   ├─ Public account likes: Indexed (findable)
   └─ User can opt-out of discovery

Implementation:
- Graph DB (Neo4j) for relationship checks
- Cache frequently accessed relationships
- Batch permission checks (reduce latency)
```

---

### 6. Cost Optimization

**Q: How would you reduce infrastructure costs?**

```
Answer:
Cost Optimization Strategies:

1. Caching (Biggest Win):
   - Cache hit rate: 95%+
   - Reduce DB reads by 20x
   - Savings: ~$100K/month

2. Data Tiering:
   - Hot data (< 7 days): SSD
   - Warm data (< 90 days): HDD
   - Cold data (> 90 days): S3 Glacier
   - Savings: ~$50K/month

3. Compression:
   - Enable Cassandra compression (LZ4)
   - Reduce storage by 60%
   - Savings: ~$30K/month

4. Right-Sizing:
   - Monitor CPU utilization (target 60-70%)
   - Scale down over-provisioned instances
   - Savings: ~$40K/month

5. Reserved Instances:
   - Purchase 1-year/3-year RIs
   - 30-50% discount vs on-demand
   - Savings: ~$80K/month

6. Spot Instances:
   - Use for non-critical workloads (analytics)
   - 70-90% discount
   - Savings: ~$20K/month

7. Data Retention:
   - Delete likes on deleted posts (cascade)
   - Archive old likes (> 2 years) to S3
   - Savings: ~$25K/month

Total Potential Savings: ~$345K/month
```

---

### 7. Advanced Topics

**Q: How would you implement "undo unlike" (within 5 seconds)?**

```
Answer:
Soft Delete + Grace Period:

1. Unlike Action:
   - Don't delete immediately
   - Mark as "pending_delete" in Redis
   - Decrease count in cache
   - Show "Undo" button for 5 seconds

2. Undo Action (within grace period):
   - Remove "pending_delete" flag
   - Restore count
   - Keep original like record

3. After Grace Period (5 seconds):
   - Background job deletes from DB
   - Permanent unlike

Implementation:
┌────────────────────────────────────────┐
│ Redis Key: "undo:{user_id}:{post_id}" │
│ Value: { action: "unlike", ... }      │
│ TTL: 5 seconds                         │
└────────────────────────────────────────┘

Benefits:
- Better UX (accidental unlikes)
- No permanent data loss
- Minimal performance impact
```

**Q: How would you implement "most liked posts" (leaderboard)?**

```
Answer:
Real-Time Leaderboard:

1. Data Structure:
   - Redis Sorted Set (ZSET)
   - Key: "leaderboard:{time_bucket}"
   - Score: like_count
   - Member: post_id

2. Update Logic:
   - On each like: ZINCRBY leaderboard 1 post_id
   - Time buckets: hourly, daily, weekly, all-time

3. Query:
   - Top 100: ZREVRANGE leaderboard 0 99 WITHSCORES
   - Rank of post: ZREVRANK leaderboard post_id

4. Time Decay (Trending):
   - Score = like_count * decay_factor
   - decay_factor = e^(-λ * age_in_hours)
   - Recent posts rank higher

5. Sharding (Scale):
   - Multiple leaderboards per region
   - Merge results for global leaderboard

Example:
┌────────────────────────────────────────┐
│ leaderboard:daily:2026-04-16           │
├────────────────────────────────────────┤
│ post_123: 1,000,000                    │
│ post_456: 500,000                      │
│ post_789: 250,000                      │
│ ...                                    │
└────────────────────────────────────────┘
```

---

## Summary: Key Design Decisions

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| **Cassandra** | High write throughput, horizontal scalability | Eventual consistency, no JOINs |
| **Redis** | Low-latency caching, high read throughput | Volatile storage, cache invalidation complexity |
| **Kafka** | Asynchronous processing, decoupling, replay | Operational complexity, consumer lag |
| **Counter Table** | Fast count reads, no COUNT(*) queries | Eventual consistency, reconciliation needed |
| **Sharded Counters** | Handle hot posts (celebrities) | Read-time aggregation overhead |
| **Idempotency Keys** | Prevent duplicate likes | Redis dependency, 5-second window |
| **Eventual Consistency** | Better performance, lower cost | Slightly stale counts (acceptable) |
| **Multi-Level Caching** | Reduced latency, lower DB load | Cache coherence, invalidation complexity |

---

## Production Readiness Checklist

- [ ] Load testing (1M likes/sec sustained)
- [ ] Chaos engineering (kill random services)
- [ ] Security audit (SQL injection, XSS, etc.)
- [ ] Disaster recovery plan (RTO < 1 hour, RPO < 5 min)
- [ ] Monitoring & alerting (P0/P1/P2 runbooks)
- [ ] Cost analysis (budget vs actual)
- [ ] Compliance (GDPR, CCPA data retention)
- [ ] Documentation (architecture, APIs, runbooks)
- [ ] Training (on-call engineers)
- [ ] Launch plan (phased rollout, rollback strategy)

---

**End of Document**

This design is production-ready and covers all aspects interviewers typically ask about in senior/staff-level system design interviews.
