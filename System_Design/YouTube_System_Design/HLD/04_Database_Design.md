# 04. Database Design - YouTube System Design

## Table of Contents
1. [Database Schema (ERD)](#database-schema-erd)
2. [Table Definitions](#table-definitions)
3. [Indexing Strategy](#indexing-strategy)
4. [Sharding Strategy](#sharding-strategy)
5. [Replication](#replication)

---

## Database Schema (ERD)

### ASCII Entity-Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DATABASE ARCHITECTURE                            │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐
│       USERS          │
├──────────────────────┤
│ PK id (BIGINT)       │◄──────────────┐
│    email (VARCHAR)   │               │
│    username (VARCHAR)│               │ 1
│    password_hash     │               │
│    created_at        │               │
│    updated_at        │               │
└──────────┬───────────┘               │
           │ 1                         │
           │                           │
           │ *                         │
┌──────────▼───────────┐               │
│       VIDEOS         │               │
├──────────────────────┤               │
│ PK id (BIGINT)       │               │
│ FK user_id           │───────────────┘
│    title (VARCHAR)   │
│    description (TEXT)│
│    video_url (VARCHAR)│
│    thumbnail_url     │
│    duration (INT)    │          ┌──────────────────────┐
│    views (BIGINT)    │          │   VIDEO_QUALITIES    │
│    likes (INT)       │◄─────────┤──────────────────────┤
│    dislikes (INT)    │ 1      * │ PK id                │
│    status (ENUM)     │          │ FK video_id          │
│    created_at        │          │    quality (VARCHAR) │
│    updated_at        │          │    url (VARCHAR)     │
└──────────┬───────────┘          │    file_size (BIGINT)│
           │ 1                    └──────────────────────┘
           │
           │ *
┌──────────▼───────────┐
│      COMMENTS        │
├──────────────────────┤
│ PK id (BIGINT)       │◄──────────┐
│ FK video_id          │           │ Nested Comments
│ FK user_id           │           │ (Self-Referencing)
│ FK parent_id (NULL)  │───────────┘
│    text (TEXT)       │
│    likes (INT)       │
│    created_at        │
│    updated_at        │
└──────────────────────┘


┌──────────────────────┐         ┌──────────────────────┐
│        LIKES         │         │   SUBSCRIPTIONS      │
├──────────────────────┤         ├──────────────────────┤
│ PK id (BIGINT)       │         │ PK id (BIGINT)       │
│ FK user_id           │─────┐   │ FK subscriber_id     │─────┐
│ FK video_id          │     │   │ FK channel_id        │     │
│    created_at        │     │   │    created_at        │     │
└──────────────────────┘     │   │    notif_enabled     │     │
                             │   └──────────────────────┘     │
                             │                                │
                             │                                │
                             └────────────────┐   ┌───────────┘
                                              │   │
                                              ▼   ▼
                                         ┌────────────┐
                                         │   USERS    │
                                         └────────────┘


┌──────────────────────┐         ┌──────────────────────┐
│   WATCH_HISTORY      │         │   PLAYLISTS          │
├──────────────────────┤         ├──────────────────────┤
│ PK id (BIGINT)       │         │ PK id (BIGINT)       │
│ FK user_id           │         │ FK user_id           │
│ FK video_id          │         │    name (VARCHAR)    │
│    watch_time_sec    │         │    description (TEXT)│
│    completed (BOOL)  │         │    is_public (BOOL)  │
│    created_at        │         │    created_at        │
└──────────────────────┘         └──────────┬───────────┘
                                            │ 1
                                            │
                                            │ *
                                 ┌──────────▼───────────┐
                                 │  PLAYLIST_VIDEOS     │
                                 ├──────────────────────┤
                                 │ PK id                │
                                 │ FK playlist_id       │
                                 │ FK video_id          │
                                 │    position (INT)    │
                                 │    added_at          │
                                 └──────────────────────┘


┌──────────────────────┐         ┌──────────────────────┐
│   NOTIFICATIONS      │         │   VIEW_LOGS (NoSQL)  │
├──────────────────────┤         ├──────────────────────┤
│ PK id (BIGINT)       │         │ _id (ObjectId)       │
│ FK user_id           │         │ user_id              │
│    type (ENUM)       │         │ video_id             │
│    message (VARCHAR) │         │ timestamp            │
│    is_read (BOOL)    │         │ watch_duration       │
│    created_at        │         │ quality              │
└──────────────────────┘         │ device_type          │
                                 │ ip_address           │
                                 │ country              │
                                 └──────────────────────┘
                                   MongoDB (Sharded)
```

---

## Table Definitions

### 1. USERS Table

```sql
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    profile_picture_url VARCHAR(500),
    bio TEXT,
    is_verified BOOLEAN DEFAULT FALSE,
    subscriber_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_created_at ON users(created_at DESC);
```

**Size Estimation**:
- 2 billion users
- Average row size: 500 bytes
- Total: 2B * 500 bytes = 1 TB

---

### 2. VIDEOS Table

```sql
CREATE TABLE videos (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    video_url VARCHAR(500) NOT NULL,  -- S3 URL
    thumbnail_url VARCHAR(500),
    duration INT NOT NULL,  -- seconds
    views BIGINT DEFAULT 0,
    likes INT DEFAULT 0,
    dislikes INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'processing',  -- processing, ready, failed
    category VARCHAR(50),
    tags TEXT[],  -- Array of tags
    language VARCHAR(10),
    is_public BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_videos_user_id ON videos(user_id);
CREATE INDEX idx_videos_status ON videos(status);
CREATE INDEX idx_videos_created_at ON videos(created_at DESC);
CREATE INDEX idx_videos_views ON videos(views DESC);  -- For trending
CREATE INDEX idx_videos_category ON videos(category);
CREATE INDEX idx_videos_tags ON videos USING GIN(tags);  -- Full-text search on tags
```

**Size Estimation**:
- 500 hours uploaded per minute = 30K hours/hour = 720K hours/day = 262M hours/year
- Average video: 5 minutes = 0.083 hours
- Videos per year: 262M / 0.083 = 3.15 billion videos/year
- Row size: 1 KB
- Total: 3.15B * 1 KB = 3.15 TB/year

---

### 3. VIDEO_QUALITIES Table

```sql
CREATE TABLE video_qualities (
    id BIGSERIAL PRIMARY KEY,
    video_id BIGINT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    quality VARCHAR(10) NOT NULL,  -- 144p, 360p, 720p, 1080p, 4K
    url VARCHAR(500) NOT NULL,  -- S3 URL for specific quality
    file_size BIGINT NOT NULL,  -- bytes
    bitrate INT,  -- kbps
    codec VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_video_qualities_video_id ON video_qualities(video_id);
CREATE UNIQUE INDEX idx_video_qualities_unique ON video_qualities(video_id, quality);
```

---

### 4. COMMENTS Table (Nested/Hierarchical)

```sql
CREATE TABLE comments (
    id BIGSERIAL PRIMARY KEY,
    video_id BIGINT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_id BIGINT REFERENCES comments(id) ON DELETE CASCADE,  -- NULL for top-level
    text TEXT NOT NULL,
    likes INT DEFAULT 0,
    is_edited BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_comments_video_id ON comments(video_id, created_at DESC);
CREATE INDEX idx_comments_user_id ON comments(user_id);
CREATE INDEX idx_comments_parent_id ON comments(parent_id);
```

**Nested Comment Example**:
```
Comment 1 (parent_id = NULL)
  ├── Reply 1.1 (parent_id = 1)
  │   └── Reply 1.1.1 (parent_id = Reply 1.1)
  └── Reply 1.2 (parent_id = 1)
Comment 2 (parent_id = NULL)
```

**Query to Get All Comments with Replies**:
```sql
WITH RECURSIVE comment_tree AS (
    -- Top-level comments
    SELECT id, video_id, user_id, parent_id, text, likes, created_at, 0 AS depth
    FROM comments
    WHERE video_id = 123 AND parent_id IS NULL
    
    UNION ALL
    
    -- Replies
    SELECT c.id, c.video_id, c.user_id, c.parent_id, c.text, c.likes, c.created_at, ct.depth + 1
    FROM comments c
    INNER JOIN comment_tree ct ON c.parent_id = ct.id
)
SELECT * FROM comment_tree ORDER BY created_at DESC;
```

---

### 5. LIKES Table

```sql
CREATE TABLE likes (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    video_id BIGINT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE UNIQUE INDEX idx_likes_unique ON likes(user_id, video_id);  -- Prevent duplicate likes
CREATE INDEX idx_likes_video_id ON likes(video_id);
CREATE INDEX idx_likes_user_id ON likes(user_id);
```

**Size Estimation**:
- 10% of views result in a like
- 1 billion video views/day → 100M likes/day
- Row size: 50 bytes
- Total per day: 100M * 50 bytes = 5 GB/day = 1.8 TB/year

---

### 6. SUBSCRIPTIONS Table

```sql
CREATE TABLE subscriptions (
    id BIGSERIAL PRIMARY KEY,
    subscriber_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notification_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE UNIQUE INDEX idx_subscriptions_unique ON subscriptions(subscriber_id, channel_id);
CREATE INDEX idx_subscriptions_subscriber_id ON subscriptions(subscriber_id);
CREATE INDEX idx_subscriptions_channel_id ON subscriptions(channel_id);
```

---

### 7. WATCH_HISTORY Table

```sql
CREATE TABLE watch_history (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    video_id BIGINT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    watch_time_sec INT NOT NULL,  -- How much of video watched
    completed BOOLEAN DEFAULT FALSE,  -- Watched till end?
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_watch_history_user_id ON watch_history(user_id, created_at DESC);
CREATE INDEX idx_watch_history_video_id ON watch_history(video_id);
```

---

### 8. PLAYLISTS Table

```sql
CREATE TABLE playlists (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE playlist_videos (
    id BIGSERIAL PRIMARY KEY,
    playlist_id BIGINT NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
    video_id BIGINT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    position INT NOT NULL,  -- Order in playlist
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_playlists_user_id ON playlists(user_id);
CREATE INDEX idx_playlist_videos_playlist_id ON playlist_videos(playlist_id, position);
CREATE UNIQUE INDEX idx_playlist_videos_unique ON playlist_videos(playlist_id, video_id);
```

---

### 9. NOTIFICATIONS Table

```sql
CREATE TABLE notifications (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,  -- new_video, comment_reply, like, subscription
    message VARCHAR(500) NOT NULL,
    link VARCHAR(500),  -- URL to related content
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_notifications_user_id ON notifications(user_id, is_read, created_at DESC);
```

---

### 10. VIEW_LOGS (MongoDB - NoSQL)

```javascript
// MongoDB Collection: view_logs
{
  "_id": ObjectId("..."),
  "user_id": 12345,
  "video_id": 67890,
  "timestamp": ISODate("2024-01-15T10:30:00Z"),
  "watch_duration": 180,  // seconds
  "quality": "720p",
  "device_type": "mobile",
  "ip_address": "103.45.67.89",
  "country": "IN",
  "city": "Mumbai",
  "referrer": "https://google.com/search?q=..."
}

// Indexes
db.view_logs.createIndex({ "video_id": 1, "timestamp": -1 });
db.view_logs.createIndex({ "user_id": 1, "timestamp": -1 });
db.view_logs.createIndex({ "timestamp": -1 });

// Sharding key
sh.shardCollection("youtube.view_logs", { "user_id": "hashed" });
```

**Why MongoDB for Logs?**
- **High write throughput**: 1M+ views/minute
- **Flexible schema**: Easy to add new fields
- **Time-series optimized**: Efficient for timestamp queries
- **TTL Indexes**: Auto-delete old logs (>90 days)

```javascript
// Auto-delete logs older than 90 days
db.view_logs.createIndex({ "timestamp": 1 }, { expireAfterSeconds: 7776000 });
```

---

## Indexing Strategy

### Why Indexes?

**Without Index**:
```sql
SELECT * FROM videos WHERE user_id = 123;
-- Full table scan: 3 billion rows → 30 seconds
```

**With Index**:
```sql
CREATE INDEX idx_videos_user_id ON videos(user_id);
SELECT * FROM videos WHERE user_id = 123;
-- Index scan: 100 rows → 10 milliseconds
```

### Types of Indexes

#### 1. B-Tree Index (Default)
**Use Case**: Equality and range queries

```sql
CREATE INDEX idx_videos_created_at ON videos(created_at DESC);
```

**Query**:
```sql
SELECT * FROM videos WHERE created_at > '2024-01-01' ORDER BY created_at DESC LIMIT 10;
-- Uses index → Fast
```

---

#### 2. Unique Index
**Use Case**: Prevent duplicate values

```sql
CREATE UNIQUE INDEX idx_users_email ON users(email);
```

**Benefit**: Enforce uniqueness at database level (not application level)

---

#### 3. Composite Index
**Use Case**: Queries with multiple WHERE conditions

```sql
CREATE INDEX idx_videos_user_category ON videos(user_id, category, created_at DESC);
```

**Query**:
```sql
SELECT * FROM videos WHERE user_id = 123 AND category = 'education' ORDER BY created_at DESC;
-- Uses composite index → Fast
```

**Rule**: Index column order matters!
- Good: `(user_id, category, created_at)` → Covers queries on `user_id`, `user_id + category`, `user_id + category + created_at`
- Bad: `(created_at, category, user_id)` → Doesn't help queries on `user_id` alone

---

#### 4. Partial Index
**Use Case**: Index only subset of rows

```sql
CREATE INDEX idx_videos_public ON videos(created_at DESC) WHERE is_public = TRUE;
```

**Benefit**: Smaller index size, faster queries on public videos

---

#### 5. GIN Index (Generalized Inverted Index)
**Use Case**: Full-text search, array columns

```sql
CREATE INDEX idx_videos_tags ON videos USING GIN(tags);
```

**Query**:
```sql
SELECT * FROM videos WHERE tags @> ARRAY['system design', 'interview'];
-- Uses GIN index → Fast
```

---

### Index Maintenance

**Cost of Indexes**:
- **Storage**: Each index adds 10-20% to table size
- **Write Performance**: INSERT/UPDATE/DELETE slower (must update indexes)

**Rule of Thumb**:
- 3-5 indexes per table
- Index columns in WHERE, ORDER BY, JOIN
- Don't index low-cardinality columns (e.g., `is_public` with only TRUE/FALSE)

---

## Sharding Strategy

### Why Shard?

**Problem**: Single database can't handle:
- 3 billion videos
- 100 million writes/day
- 1 billion reads/day

**Solution**: Horizontal sharding (split data across multiple databases)

---

### Sharding by user_id (Hash-Based)

```
Shard 0: user_id % 4 = 0 → users 0, 4, 8, 12, ...
Shard 1: user_id % 4 = 1 → users 1, 5, 9, 13, ...
Shard 2: user_id % 4 = 2 → users 2, 6, 10, 14, ...
Shard 3: user_id % 4 = 3 → users 3, 7, 11, 15, ...
```

**Benefit**: Even distribution

**Downside**: Can't easily query "all videos" (must query all shards)

---

### Sharding by video_id (Range-Based)

```
Shard 0: video_id 1 - 1,000,000,000
Shard 1: video_id 1,000,000,001 - 2,000,000,000
Shard 2: video_id 2,000,000,001 - 3,000,000,000
```

**Benefit**: Easy to add new shards (just add next range)

**Downside**: Uneven load (recent videos get more traffic)

---

### Hybrid: Consistent Hashing

**Algorithm**:
```
shard = hash(user_id) % num_shards
```

**Adding a New Shard**:
- Only 1/N keys need to move (minimal disruption)
- Use virtual nodes for better distribution

---

## Replication

### Master-Slave Replication

```
┌────────────────┐
│  Master (Write)│
│  Port: 5432    │
└────────┬───────┘
         │ Async Replication
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌────────┐
│ Slave 1│ │ Slave 2│
│ (Read) │ │ (Read) │
│  :5433 │ │  :5434 │
└────────┘ └────────┘
```

**Benefits**:
- **High Availability**: Slave promotes to master if master fails
- **Read Scalability**: 90% of queries are reads → distribute across slaves
- **Backup**: Slave can be used for backups without affecting master

**Configuration**:
```yaml
# postgresql.conf (Master)
wal_level = replica
max_wal_senders = 3
```

```yaml
# recovery.conf (Slave)
primary_conninfo = 'host=master-db port=5432 user=replicator'
```

---

## Summary

**Key Takeaways**:
1. **PostgreSQL** for structured data (users, videos, comments)
2. **MongoDB** for logs (high write throughput)
3. **Indexes** on WHERE, ORDER BY, JOIN columns
4. **Sharding** by user_id for even distribution
5. **Replication** for high availability and read scaling

**Next**: [Scalability & Performance](05_Scalability.md)
