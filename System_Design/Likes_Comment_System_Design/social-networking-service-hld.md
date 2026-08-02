# Social Networking Service - High-Level Design

## 1. System Overview

A Social Networking Service (like Facebook/Twitter) is a large-scale distributed platform that enables users to connect, share content (text, images, videos), interact through likes/comments, follow others, and build social graphs. The system must handle billions of users globally, process millions of posts per day, deliver personalized news feeds in real-time, scale horizontally across data centers, support 99.99% uptime, and provide low-latency content delivery worldwide.

## 2. Requirements

### Functional Requirements
- **User Management**: Registration, authentication, profile management
- **Social Graph**: Follow/unfollow users, friend connections
- **Post Creation**: Text posts, image/video uploads, hashtags, mentions
- **News Feed**: Personalized feed with posts from followed users
- **Interactions**: Like, comment, share, react to posts
- **Notifications**: Real-time alerts for likes, comments, mentions, follows
- **Messaging**: Direct messages, group chats
- **Search**: Find users, posts, hashtags, trending topics
- **Privacy**: Post visibility (public, friends, private), block users
- **Stories**: Ephemeral content (24-hour disappearing posts)

### Non-Functional Requirements
- **Availability**: 99.99% uptime
- **Scalability**: Support 2B+ users, 500M+ daily active users
- **Performance**: News feed load < 500ms, post creation < 200ms
- **Consistency**: Eventual consistency for feeds, strong consistency for posts
- **Latency**: < 200ms for global users (CDN-backed)
- **Storage**: Petabyte-scale for media, text posts
- **Real-time**: Sub-second notification delivery
- **Fault Tolerance**: Handle data center failures gracefully

## 3. Capacity Estimation

### Scale Assumptions
- **Total Users**: 2 billion registered users
- **Daily Active Users (DAU)**: 500 million users
- **Posts per Day**: 100M posts = 1157 posts/sec (peak: 5000/sec)
- **Reads per Day**: 5B feed refreshes = 57.8K reads/sec (peak: 200K/sec)
- **Read:Write Ratio**: 100:1 (read-heavy system)
- **Average Post Size**: 500 bytes text + 2MB media
- **Comments per Post**: Average 5 comments
- **Likes per Post**: Average 20 likes

### Storage Estimation
- **User Profiles**: 2B users × 5KB = 10TB
- **Posts (Text)**: 100M/day × 500 bytes × 365 = 18.25TB/year
- **Media (Images/Videos)**: 100M/day × 2MB × 365 = 73PB/year
- **Social Graph**: 2B users × 500 connections × 16 bytes = 16TB
- **Comments**: 500M/day × 200 bytes × 365 = 36.5TB/year
- **Likes**: 2B/day × 16 bytes × 365 = 11.7TB/year
- **Total Storage** (5 years): ~370PB (with replicas: 1.1EB)

### Bandwidth
- **Ingress**: 1157 posts/sec × 2MB = 2.3GB/s (peak: 10GB/s)
- **Egress**: 57.8K reads/sec × 1MB (avg feed size) = 57.8GB/s
- **Video Streaming**: 50M concurrent streams × 2Mbps = 100Tbps (CDN)

### Computation
- **Feed Generation**: 500M users × 2 feeds/day = 1B feeds/day
- **Ranking**: ML models rank ~1000 posts per user per feed
- **Notification Delivery**: 5B notifications/day = 57.8K/sec

## 4. System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Client Layer                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │  Web     │  │  iOS     │  │  Android │  │   API    │            │
│  │  Client  │  │   App    │  │   App    │  │  Clients │            │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘            │
└───────┼─────────────┼─────────────┼─────────────┼────────────────────┘
        │             │             │             │
        └─────────────┼─────────────┼─────────────┘
                      │
           ┌──────────▼────────────┐
           │   CDN (CloudFront)    │
           │  - Static Assets      │
           │  - Media Files        │
           └──────────┬────────────┘
                      │
           ┌──────────▼────────────┐
           │  API Gateway (Kong)   │
           │  - Rate Limiting      │
           │  - Authentication     │
           │  - SSL Termination    │
           └──────────┬────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
   ┌────▼────┐   ┌────▼────┐   ┌───▼─────┐
   │  User   │   │  Post   │   │  Feed   │
   │ Service │   │ Service │   │ Service │
   └────┬────┘   └────┬────┘   └───┬─────┘
        │             │             │
        └─────────────┼─────────────┘
                      │
        ┌─────────────┼─────────────────────┐
        │             │                     │
   ┌────▼─────┐  ┌───▼──────┐  ┌───────▼──────┐
   │ Comment  │  │   Like   │  │ Notification │
   │ Service  │  │ Service  │  │   Service    │
   └────┬─────┘  └───┬──────┘  └───────┬──────┘
        │            │                  │
        └────────────┼──────────────────┘
                     │
        ┌────────────▼────────────────────────┐
        │      Message Queue (Kafka)          │
        │  - post.created                     │
        │  - like.added                       │
        │  - comment.added                    │
        │  - user.followed                    │
        └────────────┬────────────────────────┘
                     │
        ┌────────────┼──────────────┐
        │            │              │
   ┌────▼──────┐ ┌──▼────────┐ ┌───▼──────┐
   │  Search   │ │ Analytics │ │   ML     │
   │  Service  │ │  Service  │ │ Service  │
   │(Elastic)  │ │(Spark)    │ │ (Rec)    │
   └───────────┘ └───────────┘ └──────────┘

┌──────────────────────────────────────────────────────────────────┐
│                      Data Layer                                  │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌─────────────┐  │
│  │PostgreSQL │  │   Redis   │  │ Cassandra │  │  Amazon S3  │  │
│  │  (Users,  │  │  (Cache,  │  │  (Posts,  │  │   (Media    │  │
│  │   Auth)   │  │ Sessions) │  │  Graphs)  │  │   Storage)  │  │
│  └───────────┘  └───────────┘  └───────────┘  └─────────────┘  │
│                                                                  │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐                   │
│  │   Neo4j   │  │ Elastic   │  │   HDFS    │                   │
│  │  (Social  │  │  Search   │  │ (Archives)│                   │
│  │   Graph)  │  │           │  │           │                   │
│  └───────────┘  └───────────┘  └───────────┘                   │
└──────────────────────────────────────────────────────────────────┘
```

## 5. Core Components

### User Service
- **Registration**: Create user accounts with email/phone verification
- **Authentication**: JWT-based auth, OAuth2 integration (Google, Facebook)
- **Profile Management**: Update profile picture, bio, privacy settings
- **User Discovery**: Suggest friends based on contacts, mutual connections
- **Caching**: Redis cache for active user profiles (TTL: 30 minutes)

### Post Service
- **Post Creation**: Store text posts in Cassandra (time-ordered)
- **Media Upload**: Upload images/videos to S3, store URLs in metadata
- **Hashtag Extraction**: Parse hashtags, index in Elasticsearch
- **Mention Detection**: Notify mentioned users via Kafka event
- **Post Deletion**: Soft delete, mark as deleted but retain for audit

### Feed Service (Critical Component)
- **Feed Generation Strategies**:
  - **Fan-out on Write (Push Model)**: Pre-compute feeds for followers
  - **Fan-out on Read (Pull Model)**: Compute feed on user request
  - **Hybrid Approach**: Push for normal users, pull for celebrities

- **Feed Generation Algorithm**:
```python
class FeedService:
    def generate_feed(self, user_id, page_size=50):
        # Step 1: Get user's followings
        following_ids = graph_service.get_followings(user_id)
        
        # Step 2: Fetch recent posts from followings (last 7 days)
        posts = post_service.get_posts_by_users(
            following_ids, 
            since=now() - 7.days,
            limit=1000
        )
        
        # Step 3: Rank posts by ML model
        ranked_posts = ml_service.rank_posts(user_id, posts)
        
        # Step 4: Apply filters (blocked users, privacy)
        filtered_posts = apply_filters(user_id, ranked_posts)
        
        # Step 5: Paginate and cache
        feed = filtered_posts[:page_size]
        redis.setex(f"feed:{user_id}", 300, feed)
        
        return feed
```

- **Feed Ranking Factors**:
  - Post recency (weight: 0.3)
  - Author affinity (interaction history: 0.25)
  - Post engagement (likes, comments: 0.2)
  - Content type preference (user likes videos: 0.15)
  - Dwell time (predicted: 0.1)

### Social Graph Service
- **Graph Storage**: Neo4j for friend/follow relationships
- **Follow/Unfollow**: Add/remove edges in graph
- **Friend Suggestions**: Graph algorithms (mutual friends, common interests)
- **Query Examples**:
```cypher
// Get mutual friends
MATCH (user1:User {id: 'U1'})-[:FOLLOWS]->(mutual)<-[:FOLLOWS]-(user2:User {id: 'U2'})
RETURN mutual

// Find 2nd degree connections
MATCH (user:User {id: 'U1'})-[:FOLLOWS]->()-[:FOLLOWS]->(suggestion)
WHERE NOT (user)-[:FOLLOWS]->(suggestion)
RETURN suggestion LIMIT 10
```

### Like Service
- **Like Storage**: Redis sorted set for fast reads
```python
# Add like
redis.zadd(f"post:{post_id}:likes", {user_id: timestamp})
redis.incr(f"post:{post_id}:like_count")

# Get like count
like_count = redis.get(f"post:{post_id}:like_count")

# Check if user liked post
is_liked = redis.zscore(f"post:{post_id}:likes", user_id) is not None
```
- **Persistence**: Async write to Cassandra for durability
- **Unlike**: Remove from Redis sorted set

### Comment Service
- **Hierarchical Comments**: Store parent_comment_id for nested threads
- **Pagination**: Fetch comments in batches (20 per page)
- **Real-time Updates**: WebSocket for live comment updates
- **Moderation**: Content filter for spam/abuse

### Notification Service
- **Notification Types**: Like, comment, follow, mention, tag
- **Delivery Channels**:
  - **In-app**: WebSocket push
  - **Push Notifications**: Firebase Cloud Messaging (FCM)
  - **Email**: SendGrid for digest emails
- **Notification Aggregation**: "John and 5 others liked your post"
- **Priority Queue**: Kafka with priority partitions
- **Storage**: Cassandra with TTL (30 days)

### Messaging Service
- **Direct Messages**: End-to-end encryption (Signal Protocol)
- **Group Chats**: Support up to 256 members
- **Message Storage**: Cassandra with user_id + timestamp clustering
- **Read Receipts**: Track message delivery and read status
- **Typing Indicators**: WebSocket for real-time status

### Search Service
- **Indexing**: Elasticsearch indexes posts, users, hashtags
- **Full-Text Search**: Search posts by keywords
- **Trending Topics**: Track hashtag frequency in last 24 hours
- **Autocomplete**: Prefix search for users, hashtags
- **Query Example**:
```json
{
  "query": {
    "multi_match": {
      "query": "machine learning",
      "fields": ["content", "hashtags"],
      "fuzziness": "AUTO"
    }
  },
  "sort": [
    {"timestamp": "desc"},
    {"engagement_score": "desc"}
  ]
}
```

### Media Service
- **Upload Flow**:
  1. Client requests signed S3 URL
  2. Client uploads directly to S3
  3. Client notifies backend of upload completion
  4. Backend creates post with S3 URL
- **Image Processing**: Lambda triggers on S3 upload
  - Generate thumbnails (100x100, 400x400)
  - Compress images (WebP format)
  - Extract metadata (dimensions, EXIF)
- **Video Processing**: AWS Elemental MediaConvert
  - Transcode to multiple resolutions (360p, 720p, 1080p)
  - Generate HLS/DASH manifests
  - Extract thumbnails
- **CDN Distribution**: CloudFront for global delivery

## 6. Database Design

### Schema Design

```sql
-- Users Table (PostgreSQL)
CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    password_hash VARCHAR(128) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    bio TEXT,
    profile_picture_url VARCHAR(500),
    cover_photo_url VARCHAR(500),
    date_of_birth DATE,
    gender VARCHAR(20),
    location VARCHAR(100),
    website VARCHAR(255),
    verified BOOLEAN DEFAULT FALSE,
    privacy_level VARCHAR(20) DEFAULT 'PUBLIC', -- PUBLIC, FRIENDS, PRIVATE
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE, SUSPENDED, DELETED
    follower_count INT DEFAULT 0,
    following_count INT DEFAULT 0,
    post_count INT DEFAULT 0,
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_created (created_at)
);

-- Posts Table (Cassandra)
CREATE TABLE posts (
    post_id UUID PRIMARY KEY,
    user_id BIGINT,
    content TEXT,
    media_urls LIST<TEXT>,
    media_type VARCHAR(20), -- TEXT, IMAGE, VIDEO, MIXED
    hashtags SET<TEXT>,
    mentions SET<BIGINT>,
    location TEXT,
    visibility VARCHAR(20) DEFAULT 'PUBLIC',
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    like_count INT DEFAULT 0,
    comment_count INT DEFAULT 0,
    share_count INT DEFAULT 0,
    is_deleted BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (user_id, created_at, post_id)
) WITH CLUSTERING ORDER BY (created_at DESC);

-- User Timeline (Cassandra) - Fan-out on Write
CREATE TABLE user_timeline (
    user_id BIGINT,
    post_id UUID,
    author_id BIGINT,
    created_at TIMESTAMP,
    post_content TEXT,
    media_urls LIST<TEXT>,
    PRIMARY KEY (user_id, created_at, post_id)
) WITH CLUSTERING ORDER BY (created_at DESC);

-- Comments Table (Cassandra)
CREATE TABLE comments (
    comment_id UUID PRIMARY KEY,
    post_id UUID,
    user_id BIGINT,
    parent_comment_id UUID, -- NULL for top-level comments
    content TEXT,
    created_at TIMESTAMP,
    like_count INT DEFAULT 0,
    is_deleted BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (post_id, created_at, comment_id)
) WITH CLUSTERING ORDER BY (created_at DESC);

-- Likes Table (Cassandra)
CREATE TABLE likes (
    like_id UUID PRIMARY KEY,
    post_id UUID,
    user_id BIGINT,
    created_at TIMESTAMP,
    PRIMARY KEY (post_id, user_id)
);

CREATE TABLE user_likes (
    user_id BIGINT,
    post_id UUID,
    created_at TIMESTAMP,
    PRIMARY KEY (user_id, created_at, post_id)
) WITH CLUSTERING ORDER BY (created_at DESC);

-- Follows Table (Neo4j)
// Create user nodes
CREATE (u:User {id: 'U123', username: 'john_doe'})

// Follow relationship
MATCH (follower:User {id: 'U123'}), (followee:User {id: 'U456'})
CREATE (follower)-[:FOLLOWS {since: timestamp()}]->(followee)

// Friendship (mutual follow)
CREATE (user1)-[:FRIEND_OF {since: timestamp()}]->(user2)

-- Notifications Table (Cassandra)
CREATE TABLE notifications (
    notification_id UUID,
    user_id BIGINT,
    type VARCHAR(20), -- LIKE, COMMENT, FOLLOW, MENTION
    actor_id BIGINT, -- User who triggered notification
    entity_id UUID, -- Post/comment ID
    content TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP,
    expires_at TIMESTAMP,
    PRIMARY KEY (user_id, created_at, notification_id)
) WITH CLUSTERING ORDER BY (created_at DESC)
AND default_time_to_live = 2592000; -- 30 days TTL

-- Messages Table (Cassandra)
CREATE TABLE messages (
    conversation_id UUID,
    message_id TIMEUUID,
    sender_id BIGINT,
    recipient_id BIGINT,
    content TEXT,
    encrypted_content BLOB,
    media_urls LIST<TEXT>,
    sent_at TIMESTAMP,
    delivered_at TIMESTAMP,
    read_at TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (conversation_id, sent_at, message_id)
) WITH CLUSTERING ORDER BY (sent_at DESC);

-- Hashtags Table (Elasticsearch)
{
  "mappings": {
    "properties": {
      "hashtag": {"type": "keyword"},
      "post_id": {"type": "keyword"},
      "user_id": {"type": "long"},
      "content": {"type": "text"},
      "created_at": {"type": "date"},
      "engagement_score": {"type": "float"}
    }
  }
}
```

## 7. API Design

### Create Post
```http
POST /api/v1/posts
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "Just launched my new project! #coding #tech",
  "media_urls": ["https://cdn.example.com/img1.jpg"],
  "media_type": "IMAGE",
  "visibility": "PUBLIC",
  "location": "San Francisco, CA"
}

Response: 201 Created
{
  "post_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": 123456,
  "content": "Just launched my new project! #coding #tech",
  "media_urls": ["https://cdn.example.com/img1.jpg"],
  "hashtags": ["coding", "tech"],
  "created_at": "2026-04-07T10:00:00Z",
  "like_count": 0,
  "comment_count": 0
}
```

### Get News Feed
```http
GET /api/v1/feed?page=1&limit=20
Authorization: Bearer <token>

Response: 200 OK
{
  "posts": [
    {
      "post_id": "abc123",
      "author": {
        "user_id": 789,
        "username": "jane_smith",
        "profile_picture": "https://cdn.example.com/jane.jpg"
      },
      "content": "Beautiful sunset today!",
      "media_urls": ["https://cdn.example.com/sunset.jpg"],
      "created_at": "2026-04-07T09:45:00Z",
      "like_count": 142,
      "comment_count": 23,
      "is_liked_by_user": false
    }
  ],
  "next_cursor": "eyJwYWdlIjoyfQ==",
  "has_more": true
}
```

### Like Post
```http
POST /api/v1/posts/{post_id}/like
Authorization: Bearer <token>

Response: 200 OK
{
  "post_id": "abc123",
  "like_count": 143,
  "is_liked": true
}
```

### Add Comment
```http
POST /api/v1/posts/{post_id}/comments
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "Great post! Thanks for sharing.",
  "parent_comment_id": null
}

Response: 201 Created
{
  "comment_id": "def456",
  "post_id": "abc123",
  "user_id": 123456,
  "content": "Great post! Thanks for sharing.",
  "created_at": "2026-04-07T10:05:00Z",
  "like_count": 0
}
```

### Follow User
```http
POST /api/v1/users/{user_id}/follow
Authorization: Bearer <token>

Response: 200 OK
{
  "user_id": 789,
  "is_following": true,
  "follower_count": 1543
}
```

### Search
```http
GET /api/v1/search?q=machine+learning&type=posts&limit=20
Authorization: Bearer <token>

Response: 200 OK
{
  "results": [
    {
      "type": "post",
      "post_id": "xyz789",
      "content": "Deep dive into machine learning algorithms...",
      "author": {...},
      "created_at": "2026-04-06T15:30:00Z",
      "relevance_score": 0.95
    }
  ],
  "total": 1247,
  "next_cursor": "..."
}
```

### Get Notifications
```http
GET /api/v1/notifications?unread_only=true&limit=50
Authorization: Bearer <token>

Response: 200 OK
{
  "notifications": [
    {
      "notification_id": "notif123",
      "type": "LIKE",
      "actor": {
        "user_id": 789,
        "username": "jane_smith",
        "profile_picture": "..."
      },
      "entity_id": "abc123",
      "content": "liked your post",
      "created_at": "2026-04-07T09:50:00Z",
      "is_read": false
    }
  ],
  "unread_count": 5
}
```

## 8. Scalability Strategy

### Horizontal Scaling
- **Stateless Services**: All services are stateless, scale with Kubernetes HPA
- **Load Balancing**: Geo-based routing with AWS ALB
- **Auto-Scaling**: CPU > 70% triggers scale-up, < 30% triggers scale-down
- **Service Mesh**: Istio for service-to-service communication

### Database Sharding

```
Sharding Strategy:

1. Users (PostgreSQL):
   - Shard by user_id % 16 (16 shards)
   - Each shard: 125M users
   - Read replicas: 3 per shard

2. Posts (Cassandra):
   - Partition key: user_id
   - Clustering key: created_at (DESC)
   - Automatic sharding by consistent hashing
   - Replication factor: 3

3. Social Graph (Neo4j):
   - Shard by user_id range
   - Use GraphQL Federation for cross-shard queries
   - 8 shards, each handling 250M users

4. Timelines (Cassandra):
   - Partition key: user_id
   - Hot partition handling: Celebrities get dedicated nodes
```

### Caching Strategy

```
Redis Cache Layers:

1. User Cache:
   - Key: user:{user_id}
   - TTL: 30 minutes
   - Invalidate on profile update

2. Post Cache:
   - Key: post:{post_id}
   - TTL: 1 hour
   - Invalidate on edit/delete

3. Feed Cache:
   - Key: feed:{user_id}
   - TTL: 5 minutes
   - Invalidate on new post from followings

4. Like Count Cache:
   - Key: likes:{post_id}
   - TTL: None (permanent, sync to Cassandra every 10 seconds)

5. Session Cache:
   - Key: session:{token}
   - TTL: 24 hours

Cache Eviction Policy: LRU (Least Recently Used)
```

### Feed Generation Optimization

```python
class HybridFeedStrategy:
    def generate_feed(self, user_id):
        user = get_user(user_id)
        
        # Strategy 1: Fan-out on Write (for normal users)
        if user.follower_count < 1000:
            return self.fanout_on_write(user_id)
        
        # Strategy 2: Fan-out on Read (for celebrities)
        elif user.follower_count > 100000:
            return self.fanout_on_read(user_id)
        
        # Strategy 3: Hybrid (for mid-tier influencers)
        else:
            return self.hybrid_approach(user_id)
    
    def fanout_on_write(self, user_id):
        # Pre-computed timeline exists in Cassandra
        return cassandra.query("""
            SELECT * FROM user_timeline 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT 50
        """, user_id)
    
    def fanout_on_read(self, user_id):
        # Compute feed on-demand
        following_ids = graph_service.get_followings(user_id, limit=5000)
        posts = post_service.get_recent_posts(following_ids, limit=1000)
        return ml_service.rank_and_filter(user_id, posts, limit=50)
    
    def hybrid_approach(self, user_id):
        # Mix of pre-computed + real-time
        timeline = self.fanout_on_write(user_id)  # Get 30 posts
        recent = self.fanout_on_read(user_id)      # Get 20 fresh posts
        merged = merge_and_deduplicate(timeline, recent)
        return ml_service.rank(user_id, merged)[:50]
```

### CDN Strategy

```
CloudFront Configuration:

1. Static Assets:
   - Origin: S3 bucket
   - Cache-Control: max-age=31536000 (1 year)
   - Edge locations: 400+ worldwide

2. Media Files:
   - Origin: S3 + Lambda@Edge for image resizing
   - Cache-Control: max-age=86400 (1 day)
   - Signed URLs for private content

3. API Responses:
   - Origin: API Gateway
   - Cache-Control: max-age=60 (1 minute) for feed
   - No cache for user-specific data

4. Video Streaming:
   - Origin: AWS Elemental MediaPackage
   - HLS/DASH adaptive bitrate streaming
   - Cache manifest: 10 seconds, segments: 1 hour
```

### Message Queue (Kafka)

```
Kafka Topics:

1. post.created (10 partitions)
   - Partition by user_id
   - Consumers: Feed service, Search service, Analytics

2. like.added (20 partitions)
   - Partition by post_id
   - Consumers: Notification service, Analytics

3. comment.added (10 partitions)
   - Partition by post_id
   - Consumers: Notification service, Post service (comment count)

4. user.followed (5 partitions)
   - Partition by followee_id
   - Consumers: Notification service, Graph service

5. notification.triggered (50 partitions)
   - Partition by user_id
   - Consumers: Push notification service, Email service

Retention Policy: 7 days
Replication Factor: 3
```

## 9. Fault Tolerance & High Availability

### Data Replication

```
PostgreSQL (Users):
- Master-Slave replication (1 master, 3 slaves per shard)
- Synchronous replication to 1 slave, async to others
- Automatic failover with Patroni

Cassandra (Posts, Timelines):
- Replication factor: 3
- Consistency level: QUORUM (read + write)
- Multi-datacenter replication

Neo4j (Social Graph):
- Causal clustering (3 core servers, 5 read replicas)
- Automatic leader election
- Read replicas for scaling reads

Redis (Cache):
- Redis Sentinel for automatic failover
- 1 master, 2 slaves per cache cluster
- Redis Cluster for horizontal scaling (16 shards)
```

### Circuit Breaker Pattern

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.last_failure_time = None
    
    def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpenException()
        
        try:
            result = func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
            raise

# Usage
like_service_breaker = CircuitBreaker()

def add_like_with_breaker(post_id, user_id):
    try:
        return like_service_breaker.call(like_service.add_like, post_id, user_id)
    except CircuitBreakerOpenException:
        # Fallback: Queue like operation for later
        kafka.send("like.pending", {"post_id": post_id, "user_id": user_id})
        return {"status": "queued"}
```

### Rate Limiting

```python
class RateLimiter:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def check_rate_limit(self, user_id, action, limit, window):
        """
        Sliding window rate limiter
        
        Args:
            user_id: User ID
            action: Action type (e.g., 'post_creation')
            limit: Max requests allowed
            window: Time window in seconds
        """
        key = f"rate_limit:{user_id}:{action}"
        now = time.time()
        
        # Remove old entries outside window
        self.redis.zremrangebyscore(key, 0, now - window)
        
        # Count requests in current window
        current_count = self.redis.zcard(key)
        
        if current_count >= limit:
            return False, 0
        
        # Add current request
        self.redis.zadd(key, {str(now): now})
        self.redis.expire(key, window)
        
        remaining = limit - current_count - 1
        return True, remaining

# Rate limit policies
RATE_LIMITS = {
    "post_creation": (10, 3600),      # 10 posts per hour
    "like_action": (100, 60),         # 100 likes per minute
    "comment_creation": (30, 3600),   # 30 comments per hour
    "follow_action": (50, 3600),      # 50 follows per hour
    "message_send": (100, 60),        # 100 messages per minute
}
```

### Graceful Degradation

```python
class FeedService:
    def get_feed(self, user_id):
        try:
            # Try to get personalized feed from ML service
            feed = ml_service.get_ranked_feed(user_id, timeout=2.0)
            return feed
        except TimeoutException:
            # Fallback 1: Cached personalized feed
            cached_feed = redis.get(f"feed:{user_id}")
            if cached_feed:
                return cached_feed
        except Exception:
            pass
        
        try:
            # Fallback 2: Simple chronological feed
            following_ids = graph_service.get_followings(user_id, timeout=1.0)
            posts = post_service.get_recent_posts(following_ids, limit=50)
            return sorted(posts, key=lambda p: p.created_at, reverse=True)
        except Exception:
            pass
        
        # Fallback 3: Trending posts (global feed)
        return self.get_trending_posts(limit=50)
```

## 10. Technology Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **Backend Services** | Java Spring Boot, Go | High performance, microservices |
| **Frontend Web** | React, Next.js | SEO, SSR, fast rendering |
| **Mobile Apps** | React Native, Swift, Kotlin | Cross-platform + native |
| **API Gateway** | Kong, AWS API Gateway | Rate limiting, auth |
| **User Database** | PostgreSQL 15+ | ACID, relational data |
| **Post Storage** | Cassandra | Write-heavy, time-series |
| **Graph Database** | Neo4j | Social graph queries |
| **Cache** | Redis Cluster | Low latency, in-memory |
| **Message Queue** | Apache Kafka | Event streaming, durability |
| **Search** | Elasticsearch | Full-text search, analytics |
| **Media Storage** | Amazon S3 | Scalable object storage |
| **CDN** | CloudFront, Cloudflare | Global content delivery |
| **Video Processing** | AWS Elemental MediaConvert | Transcoding, streaming |
| **ML Platform** | TensorFlow Serving, PyTorch | Recommendation, ranking |
| **Real-time** | WebSocket, Socket.io | Notifications, messaging |
| **Monitoring** | Prometheus, Grafana, Datadog | Metrics, alerts |
| **Logging** | ELK Stack (Elasticsearch, Logstash, Kibana) | Centralized logging |
| **Tracing** | Jaeger, OpenTelemetry | Distributed tracing |
| **Container** | Docker, Kubernetes | Orchestration, scaling |
| **CI/CD** | Jenkins, GitLab CI | Automated deployment |

## 11. Interview Discussion Points

### Q1: How do you handle the celebrity problem in feed generation?

**Answer**: Hybrid fan-out strategy:

**Problem**: When a celebrity with 100M followers posts, fan-out on write would write to 100M timelines, causing massive write amplification.

**Solution**:
```python
class FeedGenerator:
    CELEBRITY_THRESHOLD = 100000
    
    def handle_new_post(self, post):
        author = get_user(post.user_id)
        followers = get_followers(post.user_id)
        
        if len(followers) < self.CELEBRITY_THRESHOLD:
            # Fan-out on Write: Push to all followers' timelines
            for follower_id in followers:
                cassandra.insert_into_timeline(follower_id, post)
        else:
            # Fan-out on Read: Don't push, compute on demand
            # Mark author as celebrity
            redis.sadd("celebrity_users", post.user_id)
    
    def get_user_feed(self, user_id):
        # Get pre-computed timeline
        timeline = cassandra.get_timeline(user_id, limit=50)
        
        # Get followings who are celebrities
        celebrity_followings = redis.sinter(
            f"followings:{user_id}",
            "celebrity_users"
        )
        
        # Fetch recent posts from celebrities
        if celebrity_followings:
            celebrity_posts = post_service.get_posts(
                celebrity_followings,
                since=now() - 24.hours
            )
            timeline = merge(timeline, celebrity_posts)
        
        # Rank and return
        return rank_posts(user_id, timeline)[:50]
```

**Trade-offs**:
- Normal users: Fast reads (pre-computed), slower writes
- Celebrities: Fast writes (no fan-out), slightly slower reads for followers

### Q2: How do you ensure data consistency between cache and database?

**Answer**: Cache invalidation strategy:

**Pattern 1: Cache-Aside with Invalidation**
```python
class PostService:
    def update_post(self, post_id, content):
        # Update database first
        cassandra.execute("""
            UPDATE posts 
            SET content = ?, updated_at = ?
            WHERE post_id = ?
        """, content, now(), post_id)
        
        # Invalidate cache
        redis.delete(f"post:{post_id}")
        
        # Optional: Also invalidate feed caches
        author_id = get_post_author(post_id)
        followers = get_followers(author_id)
        for follower_id in followers[:100]:  # Invalidate top 100 active followers
            redis.delete(f"feed:{follower_id}")
```

**Pattern 2: Write-Through Cache**
```python
def add_like(post_id, user_id):
    # Write to cache immediately
    redis.zadd(f"likes:{post_id}", {user_id: time.time()})
    redis.incr(f"like_count:{post_id}")
    
    # Async write to database (Kafka)
    kafka.send("like.added", {
        "post_id": post_id,
        "user_id": user_id,
        "timestamp": time.time()
    })
    
    # Background consumer writes to Cassandra
```

**Pattern 3: Read Repair**
```python
def get_post(post_id):
    # Try cache first
    cached_post = redis.get(f"post:{post_id}")
    if cached_post:
        return cached_post
    
    # Cache miss: read from database
    post = cassandra.get_post(post_id)
    
    # Update cache
    redis.setex(f"post:{post_id}", 3600, post)
    
    return post
```

**Handling Race Conditions**:
```python
# Problem: Cache invalidated while another thread reads stale data

# Solution: Versioned cache
def update_post_with_version(post_id, content):
    # Get current version
    version = redis.get(f"post_version:{post_id}") or 0
    new_version = version + 1
    
    # Update database
    cassandra.update_post(post_id, content)
    
    # Increment version (invalidation signal)
    redis.set(f"post_version:{post_id}", new_version)
    redis.delete(f"post:{post_id}")

def get_post_with_version(post_id):
    version = redis.get(f"post_version:{post_id}") or 0
    cached = redis.hgetall(f"post:{post_id}:{version}")
    
    if cached:
        return cached
    
    post = cassandra.get_post(post_id)
    redis.hset(f"post:{post_id}:{version}", post)
    redis.expire(f"post:{post_id}:{version}", 3600)
    
    return post
```

### Q3: How do you implement real-time notifications at scale?

**Answer**: Multi-layered approach:

**Architecture**:
```
User Action → Kafka → Notification Service → (WebSocket/FCM/Email)
```

**Implementation**:
```python
class NotificationService:
    def __init__(self):
        self.websocket_manager = WebSocketManager()
        self.fcm_client = FirebaseCloudMessaging()
        self.email_service = SendGridClient()
    
    def handle_like_event(self, event):
        """Kafka consumer for like events"""
        post_id = event['post_id']
        liker_id = event['user_id']
        
        # Get post author
        post = get_post(post_id)
        author_id = post.user_id
        
        # Don't notify if user likes their own post
        if author_id == liker_id:
            return
        
        # Check notification preferences
        prefs = get_notification_preferences(author_id)
        if not prefs.like_notifications:
            return
        
        # Create notification
        notification = {
            "user_id": author_id,
            "type": "LIKE",
            "actor_id": liker_id,
            "entity_id": post_id,
            "content": f"{get_username(liker_id)} liked your post",
            "created_at": time.time()
        }
        
        # Store in database
        cassandra.insert_notification(notification)
        
        # Deliver notification
        self.deliver_notification(author_id, notification)
    
    def deliver_notification(self, user_id, notification):
        # Check if user is online (WebSocket connection exists)
        if self.websocket_manager.is_connected(user_id):
            self.websocket_manager.send(user_id, notification)
        else:
            # User offline: Send push notification
            device_tokens = get_device_tokens(user_id)
            for token in device_tokens:
                self.fcm_client.send(
                    token=token,
                    title="New Notification",
                    body=notification['content'],
                    data=notification
                )
```

**WebSocket Connection Management**:
```python
class WebSocketManager:
    def __init__(self):
        self.connections = {}  # {user_id: [connection1, connection2]}
        self.redis = Redis()
    
    async def handle_connection(self, websocket, user_id):
        # Register connection
        self.connections.setdefault(user_id, []).append(websocket)
        
        # Store in Redis for multi-server awareness
        self.redis.sadd(f"ws_connections:{user_id}", socket.getpeername())
        
        try:
            # Keep connection alive
            async for message in websocket:
                # Handle client messages (ack, etc.)
                pass
        finally:
            # Clean up on disconnect
            self.connections[user_id].remove(websocket)
            self.redis.srem(f"ws_connections:{user_id}", socket.getpeername())
    
    def send(self, user_id, notification):
        # Check if user is connected to this server
        connections = self.connections.get(user_id, [])
        for conn in connections:
            conn.send(json.dumps(notification))
        
        # If user might be on another server, use Redis Pub/Sub
        if not connections:
            self.redis.publish(f"notify:{user_id}", json.dumps(notification))
```

**Notification Aggregation**:
```python
class NotificationAggregator:
    def aggregate_likes(self, user_id):
        """Aggregate multiple likes into single notification"""
        
        # Get recent like notifications (last 5 minutes)
        notifications = cassandra.query("""
            SELECT * FROM notifications
            WHERE user_id = ? AND type = 'LIKE'
            AND created_at > ?
        """, user_id, now() - 5.minutes)
        
        # Group by post_id
        grouped = defaultdict(list)
        for notif in notifications:
            grouped[notif.entity_id].append(notif.actor_id)
        
        # Aggregate
        aggregated = []
        for post_id, likers in grouped.items():
            if len(likers) == 1:
                msg = f"{get_username(likers[0])} liked your post"
            elif len(likers) == 2:
                msg = f"{get_username(likers[0])} and {get_username(likers[1])} liked your post"
            else:
                msg = f"{get_username(likers[0])} and {len(likers)-1} others liked your post"
            
            aggregated.append({
                "type": "LIKE",
                "entity_id": post_id,
                "content": msg,
                "count": len(likers)
            })
        
        return aggregated
```

### Q4: How do you handle image upload and processing at scale?

**Answer**: Direct S3 upload with asynchronous processing:

**Upload Flow**:
```python
class MediaService:
    def get_upload_url(self, user_id, file_type, file_size):
        """Generate pre-signed S3 URL for direct upload"""
        
        # Validate file
        if file_size > MAX_FILE_SIZE:
            raise FileTooLargeException()
        
        if file_type not in ALLOWED_TYPES:
            raise InvalidFileTypeException()
        
        # Generate unique filename
        file_id = uuid.uuid4()
        key = f"uploads/{user_id}/{file_id}.{file_type}"
        
        # Generate pre-signed URL (valid for 15 minutes)
        s3_client = boto3.client('s3')
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': 'social-media-uploads',
                'Key': key,
                'ContentType': f'image/{file_type}'
            },
            ExpiresIn=900
        )
        
        return {
            "upload_url": presigned_url,
            "file_id": file_id,
            "file_key": key
        }
    
    def confirm_upload(self, user_id, file_key):
        """Called after client completes upload"""
        
        # Verify file exists in S3
        s3_client = boto3.client('s3')
        try:
            s3_client.head_object(Bucket='social-media-uploads', Key=file_key)
        except ClientError:
            raise FileNotFoundException()
        
        # Trigger async processing (Lambda)
        lambda_client = boto3.client('lambda')
        lambda_client.invoke(
            FunctionName='ImageProcessingFunction',
            InvocationType='Event',
            Payload=json.dumps({
                'bucket': 'social-media-uploads',
                'key': file_key,
                'user_id': user_id
            })
        )
        
        return {"status": "processing"}
```

**Lambda Processing**:
```python
def lambda_handler(event, context):
    """S3 trigger Lambda for image processing"""
    
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    
    # Download original image
    s3 = boto3.client('s3')
    image_data = s3.get_object(Bucket=bucket, Key=key)['Body'].read()
    
    image = Image.open(io.BytesIO(image_data))
    
    # Process image
    processed = process_image(image)
    
    # Upload processed versions
    for size, img in processed.items():
        output_key = key.replace('uploads/', f'processed/{size}/')
        s3.put_object(
            Bucket=bucket,
            Key=output_key,
            Body=img,
            ContentType='image/webp',
            CacheControl='max-age=31536000'
        )
    
    # Update database with CDN URLs
    cdn_urls = {
        size: f"https://cdn.example.com/{output_key}"
        for size, output_key in processed.items()
    }
    
    cassandra.update_media_urls(key, cdn_urls)
    
    return {"status": "success"}

def process_image(image):
    """Generate multiple sizes and optimize"""
    
    sizes = {
        'thumbnail': (150, 150),
        'small': (400, 400),
        'medium': (800, 800),
        'large': (1200, 1200)
    }
    
    processed = {}
    for size_name, dimensions in sizes.items():
        # Resize
        img = image.copy()
        img.thumbnail(dimensions, Image.LANCZOS)
        
        # Convert to WebP for better compression
        buffer = io.BytesIO()
        img.save(buffer, format='WEBP', quality=85)
        processed[size_name] = buffer.getvalue()
    
    return processed
```

**Video Processing**:
```python
class VideoProcessor:
    def process_video(self, video_key):
        """Transcode video to multiple resolutions"""
        
        mediaconvert = boto3.client('mediaconvert')
        
        job_settings = {
            "Inputs": [{
                "FileInput": f"s3://uploads/{video_key}"
            }],
            "OutputGroups": [
                {
                    "Name": "HLS",
                    "Outputs": [
                        {"NameModifier": "_360p", "ContainerSettings": {...}},
                        {"NameModifier": "_720p", "ContainerSettings": {...}},
                        {"NameModifier": "_1080p", "ContainerSettings": {...}}
                    ],
                    "OutputGroupSettings": {
                        "Type": "HLS_GROUP_SETTINGS",
                        "HlsGroupSettings": {
                            "Destination": f"s3://processed-videos/{video_key}/",
                            "SegmentLength": 6
                        }
                    }
                }
            ]
        }
        
        response = mediaconvert.create_job(Settings=job_settings)
        return response['Job']['Id']
```

### Q5: How do you implement efficient news feed ranking?

**Answer**: Multi-stage ML ranking pipeline:

**Stage 1: Candidate Generation**
```python
class FeedRankingPipeline:
    def generate_candidates(self, user_id, limit=1000):
        """Fetch potential posts for ranking"""
        
        # Get user's followings
        following_ids = graph_service.get_followings(user_id, limit=5000)
        
        # Fetch recent posts (last 7 days)
        posts = post_service.get_posts_by_users(
            user_ids=following_ids,
            since=now() - 7.days,
            limit=limit
        )
        
        return posts
```

**Stage 2: Feature Engineering**
```python
def extract_features(user_id, post):
    """Extract features for ranking model"""
    
    features = {
        # Time features
        'post_age_hours': (now() - post.created_at).hours,
        'hour_of_day': post.created_at.hour,
        'day_of_week': post.created_at.weekday(),
        
        # Engagement features
        'like_count': post.like_count,
        'comment_count': post.comment_count,
        'share_count': post.share_count,
        'engagement_rate': (post.like_count + post.comment_count * 2 + post.share_count * 3) / (post_age_hours + 1),
        
        # Author features
        'author_follower_count': get_user(post.user_id).follower_count,
        'is_verified': get_user(post.user_id).verified,
        
        # User-Author affinity
        'user_author_interaction_count': get_interaction_count(user_id, post.user_id),
        'user_author_last_interaction_days': get_last_interaction_days(user_id, post.user_id),
        
        # Content features
        'has_media': len(post.media_urls) > 0,
        'media_type': post.media_type,
        'hashtag_count': len(post.hashtags),
        'mention_count': len(post.mentions),
        'post_length': len(post.content),
        
        # User preferences
        'user_likes_video': user_preferences.prefers_video,
        'user_likes_author_content': get_author_affinity_score(user_id, post.user_id)
    }
    
    return features
```

**Stage 3: ML Ranking**
```python
class FeedRankingModel:
    def __init__(self):
        self.model = load_model('feed_ranking_model.pkl')
    
    def rank_posts(self, user_id, posts):
        """Rank posts using ML model"""
        
        # Extract features for all posts
        features = [extract_features(user_id, post) for post in posts]
        
        # Convert to DataFrame
        df = pd.DataFrame(features)
        
        # Predict engagement probability
        scores = self.model.predict_proba(df)[:, 1]
        
        # Attach scores to posts
        for post, score in zip(posts, scores):
            post.ranking_score = score
        
        # Sort by score
        ranked_posts = sorted(posts, key=lambda p: p.ranking_score, reverse=True)
        
        return ranked_posts
```

**Stage 4: Diversity and Freshness**
```python
def apply_diversity_boost(ranked_posts, user_id):
    """Ensure feed diversity and freshness"""
    
    final_feed = []
    authors_seen = set()
    content_types_seen = defaultdict(int)
    
    for post in ranked_posts:
        # Diversity: Don't show more than 2 posts from same author in top 20
        if len(final_feed) < 20 and authors_seen.count(post.user_id) >= 2:
            continue
        
        # Content type diversity: Mix media types
        if content_types_seen[post.media_type] >= 5:
            post.ranking_score *= 0.8
        
        # Freshness boost: Boost posts from last 6 hours
        if (now() - post.created_at).hours < 6:
            post.ranking_score *= 1.2
        
        authors_seen.add(post.user_id)
        content_types_seen[post.media_type] += 1
        final_feed.append(post)
        
        if len(final_feed) >= 50:
            break
    
    return final_feed
```

**Model Training**:
```python
# Training data: User interactions (clicks, likes, dwell time)
# Label: 1 if user engaged (like/comment), 0 otherwise

# Features: Same as ranking features
# Model: Gradient Boosted Trees (XGBoost) or Deep Neural Network

import xgboost as xgb

def train_ranking_model():
    # Load training data
    df_train = load_training_data()
    
    X_train = df_train.drop('engaged', axis=1)
    y_train = df_train['engaged']
    
    # Train XGBoost model
    model = xgb.XGBClassifier(
        max_depth=8,
        n_estimators=100,
        learning_rate=0.1,
        objective='binary:logistic'
    )
    
    model.fit(X_train, y_train)
    
    # Save model
    model.save_model('feed_ranking_model.pkl')
    
    return model
```

---

**End of Document**
