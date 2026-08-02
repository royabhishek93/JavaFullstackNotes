# 01. Architecture Overview - YouTube System Design

## Table of Contents
1. [Introduction](#introduction)
2. [System Requirements](#system-requirements)
3. [High-Level Architecture](#high-level-architecture)
4. [Component Breakdown](#component-breakdown)
5. [Data Flow](#data-flow)
6. [Key Design Decisions](#key-design-decisions)

---

## Introduction

YouTube is a video-sharing platform that allows users to:
- **Upload** videos (up to 12 hours, 256GB)
- **Watch** videos with adaptive streaming
- **Search** for content
- **Interact** through comments, likes, subscriptions
- **Get recommendations** based on watch history

### Scale Metrics
- **2+ billion** monthly active users
- **500+ hours** of video uploaded every minute
- **1 billion hours** of video watched daily
- **100+ countries**, 80+ languages
- **5+ EB** (exabytes) of storage

---

## System Requirements

### Functional Requirements (What the system does)

#### Core Features
1. **Video Upload**
   - Upload video files (multiple formats: MP4, AVI, MOV)
   - Add metadata (title, description, tags, thumbnail)
   - Process video (transcode to multiple resolutions)

2. **Video Streaming**
   - Stream videos with adaptive bitrate
   - Support multiple qualities (144p to 4K)
   - Resume playback from where left off

3. **Search**
   - Search videos by title, description, tags
   - Filter by date, views, duration
   - Auto-complete suggestions

4. **Social Features**
   - Like/dislike videos
   - Comment and reply to comments
   - Subscribe to channels
   - Share videos

5. **Recommendations**
   - Suggest videos based on watch history
   - Trending videos
   - Related videos

#### Out of Scope (for this design)
- Live streaming
- YouTube Premium features
- Content ID (copyright detection)
- Monetization (ads)

### Non-Functional Requirements (How well it performs)

| Requirement | Target | Explanation |
|-------------|--------|-------------|
| **Availability** | 99.99% | 52 minutes downtime/year |
| **Latency** | <200ms (video start) | Time to first byte |
| **Throughput** | 50K videos/min upload | Peak upload capacity |
| **Scalability** | 100M concurrent users | Horizontal scaling |
| **Consistency** | Eventual consistency | Views, likes can be delayed |
| **Durability** | 99.999999999% (11 9s) | Videos never lost (S3) |
| **Security** | HTTPS, DRM | Encrypted data transmission |

---

## High-Level Architecture

### ASCII Diagram - Complete System

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            CLIENT LAYER                                  │
├─────────────────────────────────────────────────────────────────────────┤
│  Web Browser          Mobile App (iOS/Android)        Smart TV          │
│  (React.js)           (Native/React Native)                              │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               │ HTTPS
                               ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                          CDN LAYER (CloudFront)                          │
├─────────────────────────────────────────────────────────────────────────┤
│  Edge Location (Mumbai)   Edge Location (US)   Edge Location (Europe)   │
│  Cache: Hot Videos        Cache: Hot Videos    Cache: Hot Videos        │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               │ Cache Miss
                               ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                      LOAD BALANCER (AWS ALB)                             │
├─────────────────────────────────────────────────────────────────────────┤
│  Round Robin + Health Checks + SSL Termination                          │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               │ Route by Path
                               ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                        API GATEWAY LAYER                                 │
├─────────────────────────────────────────────────────────────────────────┤
│  - Authentication (JWT)                                                  │
│  - Rate Limiting (100 req/min per user)                                 │
│  - Request Validation                                                    │
│  - API Versioning (/api/v1/videos)                                      │
└───┬──────────────┬──────────────┬──────────────┬──────────────┬─────────┘
    │              │              │              │              │
    ↓              ↓              ↓              ↓              ↓
┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
│ Video   │  │ User    │  │Comment  │  │ Search  │  │ Recommend│
│ Service │  │ Service │  │ Service │  │ Service │  │ Service  │
│         │  │         │  │         │  │         │  │          │
│ :8081   │  │ :8082   │  │ :8083   │  │ :8084   │  │ :8085    │
└────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └────┬─────┘
     │            │            │            │            │
     │            │            │            │            │
     └────────────┴────────────┴────────────┴────────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
                    ↓                     ↓
        ┌───────────────────┐   ┌───────────────────┐
        │  MESSAGE QUEUE    │   │   CACHE LAYER     │
        │   (Kafka)         │   │   (Redis)         │
        ├───────────────────┤   ├───────────────────┤
        │ Topic: video-     │   │ Cache:            │
        │   upload-events   │   │ - User sessions   │
        │ Topic: comment-   │   │ - Video metadata  │
        │   events          │   │ - View counts     │
        │ Topic: view-      │   │ - Hot videos      │
        │   events          │   │ TTL: 5-60 min     │
        └─────────┬─────────┘   └───────────────────┘
                  │
                  │ Consume Events
                  ↓
        ┌───────────────────┐
        │ VIDEO PROCESSOR   │
        │ (Worker Pool)     │
        ├───────────────────┤
        │ FFmpeg Transcoder │
        │ - 144p            │
        │ - 360p            │
        │ - 720p            │
        │ - 1080p           │
        │ - 4K              │
        │                   │
        │ Thumbnail Gen     │
        │ Subtitle Extract  │
        └─────────┬─────────┘
                  │
                  │ Upload Transcoded
                  ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                         STORAGE LAYER                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │
│  │ S3 (Videos)     │  │ RDS (PostgreSQL)│  │ MongoDB         │        │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤        │
│  │ Raw Videos      │  │ - users         │  │ - view_logs     │        │
│  │ Transcoded      │  │ - videos        │  │ - watch_history │        │
│  │ Thumbnails      │  │ - comments      │  │ - analytics     │        │
│  │                 │  │ - likes         │  │                 │        │
│  │ Bucket: youtube-│  │ - subscriptions │  │ Sharded by      │        │
│  │   videos-prod   │  │                 │  │ user_id         │        │
│  │                 │  │ Master-Slave    │  │                 │        │
│  │ S3 Glacier for  │  │ Replication     │  │                 │        │
│  │ old videos      │  │                 │  │                 │        │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘        │
│                                                                          │
│  ┌─────────────────┐                                                    │
│  │ Elasticsearch   │                                                    │
│  ├─────────────────┤                                                    │
│  │ Video Search    │                                                    │
│  │ Index           │                                                    │
│  │                 │                                                    │
│  │ - title         │                                                    │
│  │ - description   │                                                    │
│  │ - tags          │                                                    │
│  │ - transcript    │                                                    │
│  └─────────────────┘                                                    │
└──────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                      MONITORING & OBSERVABILITY                          │
├─────────────────────────────────────────────────────────────────────────┤
│  CloudWatch    Prometheus    Grafana    ELK Stack    Jaeger (Tracing)  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Client Layer
**Purpose**: User interface for interacting with YouTube

**Components**:
- **Web App (React.js)**: Desktop browser experience
- **Mobile App**: Native iOS/Android or React Native
- **Smart TV**: Streaming on television devices

**Key Features**:
- Video player with controls (play, pause, seek, quality selector)
- Upload interface with progress bar
- Search bar with auto-complete
- Comment section
- Recommendation feed

---

### 2. CDN Layer (Content Delivery Network)
**Purpose**: Serve videos from locations closest to users

**Technology**: AWS CloudFront (200+ edge locations worldwide)

**How it works**:
```
User (Mumbai) → Edge Location (Mumbai) → Cache Hit → Video Delivered (50ms)
                                       ↓
                                 Cache Miss → Origin S3 (US) → Cache & Deliver (500ms)
```

**Benefits**:
- **Low Latency**: 50-100ms instead of 500ms+
- **Reduced Load**: 90% requests served from cache
- **Cost Savings**: Bandwidth from edge is cheaper

**Cache Strategy**:
- Hot videos: Cache for 24 hours
- Cold videos: Cache for 1 hour
- Thumbnails: Cache for 7 days

---

### 3. Load Balancer
**Purpose**: Distribute traffic across multiple servers

**Type**: AWS Application Load Balancer (Layer 7)

**Features**:
- **Round Robin**: Distribute evenly
- **Health Checks**: Remove unhealthy servers
- **SSL Termination**: Handle HTTPS encryption
- **Sticky Sessions**: Same user → same server (for WebSocket)

**Example**:
```
Request 1 → Server A
Request 2 → Server B
Request 3 → Server C
Request 4 → Server A (cycle repeats)
```

---

### 4. API Gateway
**Purpose**: Single entry point for all API requests

**Responsibilities**:
1. **Authentication**: Verify JWT tokens
2. **Rate Limiting**: 100 requests/min per user
3. **Request Validation**: Check required fields
4. **Routing**: /api/v1/videos → Video Service
5. **API Versioning**: Support v1, v2 simultaneously

**Example Flow**:
```
Client Request:
GET /api/v1/videos/123
Headers: Authorization: Bearer <JWT>

API Gateway:
1. Validate JWT ✓
2. Check rate limit ✓
3. Route to Video Service:8081 ✓
```

---

### 5. Microservices Layer

#### A. Video Service (Port 8081)
**Responsibilities**:
- Upload video
- Get video details
- Update video metadata
- Delete video
- Trigger transcoding job

**Tech Stack**: Java Spring Boot, PostgreSQL

---

#### B. User Service (Port 8082)
**Responsibilities**:
- User registration/login
- Profile management
- Channel management
- Subscription management

**Tech Stack**: Java Spring Boot, PostgreSQL

---

#### C. Comment Service (Port 8083)
**Responsibilities**:
- Post comment
- Reply to comment (nested)
- Like comment
- Delete comment

**Tech Stack**: Java Spring Boot, PostgreSQL (with self-referencing foreign key)

---

#### D. Search Service (Port 8084)
**Responsibilities**:
- Full-text search
- Autocomplete suggestions
- Trending searches

**Tech Stack**: Java Spring Boot, Elasticsearch

---

#### E. Recommendation Service (Port 8085)
**Responsibilities**:
- Personalized recommendations
- Related videos
- Trending videos

**Tech Stack**: Python (ML models), Java Spring Boot (API layer), MongoDB

---

### 6. Message Queue (Kafka)
**Purpose**: Asynchronous event processing

**Topics**:
1. **video-upload-events**: Trigger transcoding
2. **comment-events**: Send notifications
3. **view-events**: Update view counts
4. **like-events**: Update like counts

**Why Kafka?**
- **Decoupling**: Video upload doesn't wait for transcoding
- **Scalability**: Add more consumers to process faster
- **Fault Tolerance**: Events persisted, retry on failure

**Example**:
```
Producer (Video Service):
  → Publish event: {"video_id": 123, "user_id": 456, "status": "uploaded"}

Consumer (Video Processor):
  → Consume event
  → Start transcoding video 123
  → Update status to "processing"
```

---

### 7. Video Processor (Worker Pool)
**Purpose**: Transcode videos to multiple formats

**Technology**: FFmpeg (open-source video processing)

**Process**:
```
Original Video (4K, 2GB, MP4)
        ↓
    FFmpeg Transcode
        ↓
Output:
- 144p (10MB, MP4)
- 360p (30MB, MP4)
- 720p (100MB, MP4)
- 1080p (300MB, MP4)
- 4K (2GB, MP4)
```

**Worker Pool**:
- 100 workers running in parallel
- Each worker: 1 video at a time
- Kubernetes auto-scaling based on queue depth

**Time Estimate**:
- 5-minute video: ~5 minutes to transcode (1:1 ratio)
- 1-hour video: ~1 hour to transcode

---

### 8. Cache Layer (Redis)
**Purpose**: Speed up frequent reads

**Cached Data**:
| Data Type | Key Example | TTL | Why? |
|-----------|-------------|-----|------|
| Video Metadata | `video:123` | 60 min | Reduce DB load |
| User Sessions | `session:abc123` | 30 min | Fast auth |
| View Counts | `views:123` | 5 min | Eventual consistency |
| Hot Videos | `trending:today` | 10 min | High traffic |

**Cache Strategy**: Write-Through
```
1. Write to DB → Success
2. Write to Cache → Success
3. Return to client
```

**Cache Invalidation**:
- On video update: Delete `video:123`
- On new comment: Delete `comments:video:123`

---

### 9. Storage Layer

#### A. S3 (Object Storage)
**Purpose**: Store videos, thumbnails

**Structure**:
```
youtube-videos-prod/
  └── videos/
      └── 2024/
          └── 01/
              └── 15/
                  └── video-123-original.mp4
                  └── video-123-1080p.mp4
                  └── video-123-720p.mp4
                  └── video-123-360p.mp4
  └── thumbnails/
      └── thumb-123.jpg
```

**Cost Optimization**:
- New videos: S3 Standard
- Videos >6 months old: S3 Infrequent Access
- Videos >1 year old: S3 Glacier (archive)

---

#### B. PostgreSQL (Relational Database)
**Purpose**: Store structured data

**Tables**:
- users, videos, comments, likes, subscriptions

**Why PostgreSQL?**
- ACID transactions (consistency)
- Complex queries (JOINs)
- Proven at scale

**Replication**:
- 1 Master (writes)
- 2 Slaves (reads)
- Automatic failover

---

#### C. MongoDB (NoSQL)
**Purpose**: Store logs, analytics

**Collections**:
- view_logs (1 document per view)
- watch_history
- analytics_daily

**Why MongoDB?**
- Flexible schema
- Horizontal sharding
- Fast writes

---

#### D. Elasticsearch
**Purpose**: Full-text search

**Index Structure**:
```json
{
  "video_id": 123,
  "title": "Learn System Design",
  "description": "Complete guide to...",
  "tags": ["system design", "interview"],
  "transcript": "Hello everyone...",
  "views": 10000
}
```

**Search Query**:
```
GET /videos/_search
{
  "query": {
    "multi_match": {
      "query": "system design",
      "fields": ["title^3", "description", "tags^2"]
    }
  }
}
```

---

## Data Flow

### Flow 1: Video Upload
```
1. User uploads video (2GB) → React App
2. React App → Multipart upload to S3 (direct, not via backend)
3. S3 returns video URL
4. React App → Video Service: POST /api/v1/videos {url, title, description}
5. Video Service → Save metadata to PostgreSQL
6. Video Service → Publish event to Kafka: "video-uploaded"
7. Video Processor → Consume event
8. Video Processor → Download from S3, transcode, upload back to S3
9. Video Processor → Update video status to "processed"
10. User receives notification: "Video ready!"
```

**Time**: 5-10 minutes for a 5-minute video

---

### Flow 2: Video Streaming
```
1. User clicks video → React App
2. React App → GET /api/v1/videos/123
3. Video Service → Check Redis cache
   - Cache Hit → Return metadata
   - Cache Miss → Query PostgreSQL → Cache result
4. React App receives video URLs:
   {
     "144p": "https://cdn.youtube.com/123-144p.mp4",
     "360p": "https://cdn.youtube.com/123-360p.mp4",
     "720p": "https://cdn.youtube.com/123-720p.mp4"
   }
5. React Player → Request video from CDN
6. CDN → Serve from nearest edge location
7. Video streams to user
8. React App → POST /api/v1/videos/123/views (async)
9. Video Service → Increment view count in Redis
10. Background job → Sync Redis to PostgreSQL every 5 min
```

**Latency**: 100-200ms to start playback

---

### Flow 3: Search
```
1. User types "system design" → React App
2. React App → GET /api/v1/search?q=system+design
3. Search Service → Query Elasticsearch
4. Elasticsearch → Return top 20 results (ranked by relevance + views)
5. React App → Display results with thumbnails
```

**Latency**: 50-100ms

---

## Key Design Decisions

### 1. Why Microservices?
**Pros**:
- Independent scaling (Video Service needs more servers than User Service)
- Technology diversity (Python for ML, Java for API)
- Fault isolation (Comment Service down ≠ Video streaming down)

**Cons**:
- Complexity (distributed tracing, service mesh)
- Network overhead

**Decision**: Microservices, because YouTube's scale requires independent scaling.

---

### 2. Why CDN?
**Without CDN**:
- User in India → Video from US S3 → 500ms latency
- All traffic hits origin servers → Expensive bandwidth

**With CDN**:
- User in India → Edge location in Mumbai → 50ms latency
- 90% traffic served from cache → 10x cost savings

**Decision**: CDN is essential for global low-latency delivery.

---

### 3. Why Kafka?
**Alternative 1**: Synchronous (Video Service calls Video Processor directly)
- **Problem**: Video upload takes 5 minutes (user waits)

**Alternative 2**: Database polling (Video Processor checks DB every 10s)
- **Problem**: Inefficient, high DB load

**Kafka**:
- Asynchronous (user upload completes in 2 seconds)
- Scalable (add more consumers)
- Fault-tolerant (retry failed jobs)

**Decision**: Kafka for async event-driven architecture.

---

### 4. Why PostgreSQL + MongoDB?
**PostgreSQL**:
- Structured data (users, videos, comments)
- Complex queries (JOINs)
- ACID transactions

**MongoDB**:
- High write throughput (millions of view events)
- Flexible schema (analytics)
- Horizontal sharding

**Decision**: Use the right tool for the job (polyglot persistence).

---

### 5. Why S3?
**Alternatives**:
- Store videos in database → Too large, expensive
- Store videos on EC2 EBS → Not scalable, no redundancy

**S3**:
- Unlimited storage
- 99.999999999% durability (11 9s)
- $0.023/GB/month (cheap)
- Integrates with CloudFront

**Decision**: S3 is purpose-built for storing large files.

---

## Summary: Architecture in 3 Sentences

1. **Upload**: User uploads video to S3 → metadata saved to PostgreSQL → Kafka event triggers transcoding → transcoded videos stored back in S3.

2. **Streaming**: User requests video → CDN serves from nearest edge location → metadata fetched from Redis/PostgreSQL → video streams with adaptive bitrate.

3. **Scalability**: Microservices scale independently, Kafka handles async jobs, CDN reduces origin load, database sharding handles data growth.

---

## Next Steps
- [System Components Deep Dive](02_System_Components.md)
- [Transaction Flow](03_Transaction_Flow.md)
- [Database Design](04_Database_Design.md)
