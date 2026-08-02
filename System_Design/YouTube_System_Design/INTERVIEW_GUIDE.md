# YouTube System Design - Interview Guide

## Quick Navigation
1. [Interview Format](#interview-format)
2. [HLD Interview (45-60 min)](#hld-interview-45-60-min)
3. [LLD Interview (45-60 min)](#lld-interview-45-60-min)
4. [Common Questions & Answers](#common-questions--answers)
5. [Cheat Sheet](#cheat-sheet)

---

## Interview Format

### HLD (High-Level Design) Interview
**Focus**: Architecture, scalability, distributed systems
**Time**: 45-60 minutes
**Typical at**: FAANG, Senior Engineer, Staff Engineer roles

### LLD (Low-Level Design) Interview
**Focus**: Classes, methods, design patterns, code
**Time**: 45-60 minutes
**Typical at**: FAANG, Mid-level to Senior Engineer roles

---

## HLD Interview (45-60 min)

### Phase 1: Requirements Gathering (5-10 min)

**Interviewer**: "Design YouTube"

**Your Response** (Ask clarifying questions):

```
Functional Requirements:
Q: What features should we support?
A: Upload video, watch video, search, comment, like, subscribe

Q: Do we need live streaming?
A: No, only pre-recorded videos

Q: What's the video size limit?
A: Up to 2GB, max 2 hours

Q: Do we need recommendations?
A: Yes, basic collaborative filtering
```

```
Non-Functional Requirements:
Q: How many users?
A: 100M daily active users (DAU)

Q: Read/write ratio?
A: 100:1 (100 reads per 1 write)

Q: Expected latency?
A: <200ms video start time, <50ms for search

Q: Availability target?
A: 99.99% (52 min downtime/year)

Q: Consistency requirements?
A: Eventual consistency OK for views/likes
   Strong consistency for video metadata
```

**Summary** (Write on whiteboard):
```
Functional: Upload, Watch, Search, Comment, Like, Subscribe
Non-Functional: 100M DAU, 100:1 read/write, <200ms latency, 99.99% uptime
```

---

### Phase 2: Capacity Estimation (5 min)

**Storage Estimation**:
```
Assumptions:
- 100M DAU
- Each user watches 5 videos/day
- Average video: 5 min, 50MB (720p)
- Upload rate: 500 hours/min (from requirements)

Daily Storage:
- 500 hours/min × 60 min/hour × 60 sec/hour = 1.8M hours uploaded/day
- 1.8M hours × 50MB/min × 60 min/hour = 5.4 PB/day

Total Storage (5 years):
- 5.4 PB/day × 365 days × 5 years = ~10 EB (10,000 PB)
```

**Bandwidth Estimation**:
```
Reads (Views):
- 100M DAU × 5 videos × 50MB = 25 PB/day
- 25 PB/day ÷ 86,400 sec = ~300 GB/sec peak

Writes (Uploads):
- 1.8M hours × 50MB/min × 60 min/hour = 5.4 PB/day
- 5.4 PB/day ÷ 86,400 sec = ~60 GB/sec peak
```

**Requests Per Second (RPS)**:
```
Video Views:
- 100M DAU × 5 videos/day = 500M requests/day
- 500M ÷ 86,400 sec = ~5,800 RPS average
- Peak (5x average): ~30K RPS

Video Uploads:
- 500 hours/min = 30K videos/hour = 8 videos/sec
```

**Write on Whiteboard**:
```
Storage: 10 EB (5 years)
Bandwidth: 300 GB/sec (read), 60 GB/sec (write)
RPS: 30K (peak video views)
```

---

### Phase 3: High-Level Architecture (15 min)

**Draw this diagram on whiteboard**:

```
┌──────────┐
│  Client  │
└────┬─────┘
     │
     ↓
┌─────────────┐
│ CDN/CloudFr.│ (90% traffic served from cache)
└────┬────────┘
     │ Cache Miss
     ↓
┌─────────────┐
│ Load Balance│
└────┬────────┘
     │
     ↓
┌─────────────────────────────────┐
│     Microservices Layer         │
│  ┌────────┐  ┌────────┐        │
│  │ Video  │  │ User   │  ...   │
│  │Service │  │Service │        │
│  └───┬────┘  └────────┘        │
└──────┼─────────────────────────┘
       │
       ↓
┌──────────────┐    ┌──────────┐
│ Message Queue│    │  Cache   │
│   (Kafka)    │    │ (Redis)  │
└──────┬───────┘    └──────────┘
       │
       ↓
┌──────────────┐
│Video Proc.   │
│(FFmpeg)      │
└──────┬───────┘
       │
       ↓
┌────────────────────────────────┐
│  Storage Layer                 │
│  ┌───────┐  ┌──────┐  ┌─────┐ │
│  │  S3   │  │ PgSQL│  │Mongo│ │
│  │Videos │  │Users │  │Logs │ │
│  └───────┘  └──────┘  └─────┘ │
└────────────────────────────────┘
```

**Explain Each Layer** (2 min each):

1. **CDN Layer**: "CloudFront with 200+ edge locations. 90% cache hit ratio. Reduces origin load 10x."

2. **Load Balancer**: "ALB with health checks, SSL termination, path-based routing."

3. **Microservices**: "Separate services for Video, User, Comment, Search. Independent scaling."

4. **Message Queue**: "Kafka for async video processing. Decouple upload from transcoding."

5. **Storage**: 
   - "S3 for videos (unlimited, durable, cheap)"
   - "PostgreSQL for metadata (ACID, relations)"
   - "MongoDB for logs (high write throughput)"

---

### Phase 4: Deep Dive (15-20 min)

**Interviewer picks ONE area. Prepare for these:**

#### Deep Dive A: Video Upload Flow

**Draw Sequence Diagram**:
```
User          API         Kafka      Worker       S3        DB
 |             |            |          |          |         |
 |--Upload---->|            |          |          |         |
 |             |---Save-------------------->      |         |
 |             |            |          |          |         |
 |             |---Event--->|          |          |         |
 |             |            |          |          |         |
 |<---200 OK---|            |          |          |         |
 |             |            |---Consume->         |         |
 |             |            |          |          |         |
 |             |            |          |--Download>|         |
 |             |            |          |          |         |
 |             |            |          |-Transcode-|         |
 |             |            |          |          |         |
 |             |            |          |--Upload-->|         |
 |             |            |          |          |         |
 |             |            |          |---Update------>     |
 |             |            |          |          |         |
 |<-------Notification------|          |          |         |
```

**Key Points**:
1. User uploads to S3 directly (presigned URL) - not via backend
2. Backend saves metadata to DB
3. Kafka event triggers video processor
4. FFmpeg transcodes to multiple resolutions
5. Eventual consistency: video visible immediately, processed later

**Answer Probing Questions**:
- Q: What if worker fails?
- A: Kafka retries (DLQ after 3 attempts), exponential backoff

- Q: How long does transcoding take?
- A: ~1:1 ratio (5 min video = 5 min processing)

- Q: How do you handle concurrent uploads by same user?
- A: Allow it. S3 handles concurrency. Rate limit: 10 uploads/hour per user.

---

#### Deep Dive B: Video Streaming (Adaptive Bitrate)

**Explain HLS Protocol**:
```
Video File (MP4)
      ↓
  FFmpeg Transcode
      ↓
Multiple Variants:
- 1080p (5 Mbps)
- 720p (2.5 Mbps)
- 480p (1 Mbps)
- 360p (500 Kbps)
      ↓
   M3U8 Playlist
      ↓
   CDN Cache
      ↓
Video Player (auto-switch quality)
```

**M3U8 Playlist Example**:
```m3u8
#EXTM3U
#EXT-X-STREAM-INF:BANDWIDTH=5000000,RESOLUTION=1920x1080
https://cdn.youtube.com/video-123-1080p.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=2500000,RESOLUTION=1280x720
https://cdn.youtube.com/video-123-720p.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=1000000,RESOLUTION=854x480
https://cdn.youtube.com/video-123-480p.m3u8
```

**Key Points**:
- Player starts at 360p (fast start)
- Monitors bandwidth, upgrades to 720p if stable
- Switches down if buffering occurs
- No user interruption

---

#### Deep Dive C: Recommendation System

**Architecture**:
```
User Watch History → Feature Extraction → ML Model → Top 20 Videos
                                           ↑
                          (Collaborative Filtering)
```

**Algorithm** (Simplified):
```
1. User watches video V1 (category: Education)
2. Find similar users who watched V1
3. Get videos those users watched (V2, V3, V4)
4. Rank by:
   - Watch time (30% weight)
   - Like rate (20% weight)
   - Recency (20% weight)
   - Category match (30% weight)
5. Return top 20
```

**Implementation**:
- **Offline**: Spark job computes similarity matrix (runs daily)
- **Online**: Redis cache stores precomputed recommendations
- **Real-time**: Update user vector on each view

**Answer Probing Questions**:
- Q: Cold start problem (new user)?
- A: Show trending videos + personalize after 3 views

- Q: How often do recommendations update?
- A: Batch: daily, Real-time adjustments: per view

---

### Phase 5: Scalability & Trade-offs (5-10 min)

**Bottlenecks & Solutions**:

1. **Database Bottleneck**
   - Problem: 30K RPS exceeds single PostgreSQL capacity
   - Solution: 
     - Read replicas (3 slaves for reads)
     - Sharding by user_id (4 shards → 7.5K RPS each)
     - Cache hot videos in Redis (90% cache hit)

2. **Storage Growth**
   - Problem: 5 PB/day storage costs
   - Solution: 
     - Lifecycle policy: S3 Standard → IA (90 days) → Glacier (1 year)
     - Delete videos <10 views after 2 years
     - Compress better (H.265 codec saves 50%)

3. **Hot Video (Viral)**
   - Problem: 1M concurrent viewers on 1 video
   - Solution:
     - CDN caching (99% cache hit)
     - Origin shield (single S3 fetch per edge location)
     - Rate limit API calls (100 req/min per IP)

**Trade-offs Table**:
| Decision | Pro | Con |
|----------|-----|-----|
| Eventual consistency (views) | Lower latency, higher throughput | View count may lag 5 min |
| Microservices | Independent scaling, fault isolation | Complexity, distributed tracing |
| CDN | 90% cost savings, low latency | Cache invalidation challenges |
| S3 Glacier | 80% storage savings | Retrieval takes 5-12 hours |

---

## LLD Interview (45-60 min)

### Phase 1: Scope Definition (5 min)

**Interviewer**: "Design the video upload service"

**Your Response**:
```
Clarifying Questions:
Q: Which components? Just upload or also processing?
A: Upload API + video processor

Q: Language preference?
A: Java

Q: Focus on classes or implementation?
A: Both - classes first, then implement 2-3 key methods

Q: Error handling in scope?
A: Yes
```

---

### Phase 2: Class Diagram (15 min)

**Draw on Whiteboard**:

```
┌─────────────────────────────┐
│   VideoUploadController     │
├─────────────────────────────┤
│ + uploadVideo(request, file)│
│ + getUploadStatus(videoId)  │
└──────────┬──────────────────┘
           │ uses
           ↓
┌─────────────────────────────┐
│   VideoService              │ (Interface)
├─────────────────────────────┤
│ + createVideo(request)      │
│ + processVideo(videoId)     │
│ + getVideo(videoId)         │
└──────────┬──────────────────┘
           │ implements
           ↓
┌─────────────────────────────┐
│   VideoServiceImpl          │
├─────────────────────────────┤
│ - videoRepository           │
│ - storageService            │
│ - videoProcessorQueue       │
│ + createVideo(request)      │
│ + processVideo(videoId)     │
└──────────┬──────────────────┘
           │ uses
     ┌─────┴─────┐
     ↓           ↓
┌─────────┐ ┌──────────────┐
│S3Storage│ │KafkaProducer │
│Service  │ │              │
└─────────┘ └──────────────┘
           │ uses
           ↓
┌─────────────────────────────┐
│   VideoRepository           │
├─────────────────────────────┤
│ + save(video)               │
│ + findById(id)              │
│ + updateStatus(id, status)  │
└──────────┬──────────────────┘
           │ persists
           ↓
┌─────────────────────────────┐
│         Video               │ (Entity)
├─────────────────────────────┤
│ - id: Long                  │
│ - userId: Long              │
│ - title: String             │
│ - url: String               │
│ - status: VideoStatus       │
│ - duration: Integer         │
│ - createdAt: Timestamp      │
│ + isReadyForStreaming()     │
└─────────────────────────────┘

┌─────────────────────────────┐
│   VideoStatus (Enum)        │
├─────────────────────────────┤
│ UPLOADING                   │
│ PROCESSING                  │
│ READY                       │
│ FAILED                      │
└─────────────────────────────┘
```

---

### Phase 3: Implementation (20-25 min)

**Implement Key Methods**:

#### 1. Video Entity (5 min)

```java
@Entity
@Table(name = "videos")
public class Video {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    private Long userId;
    
    @Column(nullable = false)
    private String title;
    
    private String description;
    
    @Column(nullable = false)
    private String videoUrl;
    
    @Enumerated(EnumType.STRING)
    private VideoStatus status;
    
    private Integer duration; // seconds
    
    private Long views = 0L;
    
    @CreationTimestamp
    private LocalDateTime createdAt;
    
    // Constructor, getters, setters
    
    public boolean isReadyForStreaming() {
        return this.status == VideoStatus.READY;
    }
}

public enum VideoStatus {
    UPLOADING,
    PROCESSING,
    READY,
    FAILED
}
```

---

#### 2. VideoService Implementation (10 min)

```java
@Service
@Transactional
public class VideoServiceImpl implements VideoService {
    
    private final VideoRepository videoRepository;
    private final S3StorageService storageService;
    private final KafkaTemplate<String, VideoEvent> kafkaTemplate;
    
    private static final String VIDEO_UPLOAD_TOPIC = "video-upload-events";
    
    @Autowired
    public VideoServiceImpl(
        VideoRepository videoRepository,
        S3StorageService storageService,
        KafkaTemplate<String, VideoEvent> kafkaTemplate
    ) {
        this.videoRepository = videoRepository;
        this.storageService = storageService;
        this.kafkaTemplate = kafkaTemplate;
    }
    
    @Override
    public VideoResponse createVideo(VideoUploadRequest request, MultipartFile file) {
        // Validate file
        validateVideoFile(file);
        
        // Upload to S3
        String videoUrl = storageService.uploadVideo(file, request.getUserId());
        
        // Create video entity
        Video video = Video.builder()
            .userId(request.getUserId())
            .title(request.getTitle())
            .description(request.getDescription())
            .videoUrl(videoUrl)
            .status(VideoStatus.PROCESSING)
            .duration(0) // Will be extracted during processing
            .build();
        
        // Save to database
        Video savedVideo = videoRepository.save(video);
        
        // Publish event to Kafka for async processing
        VideoEvent event = new VideoEvent(
            savedVideo.getId(),
            savedVideo.getUserId(),
            videoUrl
        );
        kafkaTemplate.send(VIDEO_UPLOAD_TOPIC, event);
        
        return mapToResponse(savedVideo);
    }
    
    private void validateVideoFile(MultipartFile file) {
        if (file.isEmpty()) {
            throw new InvalidVideoException("File is empty");
        }
        
        // Check file size (max 2GB)
        if (file.getSize() > 2L * 1024 * 1024 * 1024) {
            throw new InvalidVideoException("File size exceeds 2GB limit");
        }
        
        // Check file type
        String contentType = file.getContentType();
        if (!isValidVideoType(contentType)) {
            throw new InvalidVideoException("Invalid video format");
        }
    }
    
    private boolean isValidVideoType(String contentType) {
        return contentType != null && (
            contentType.equals("video/mp4") ||
            contentType.equals("video/quicktime") ||
            contentType.equals("video/x-msvideo")
        );
    }
    
    @Override
    public VideoResponse getVideo(Long videoId) {
        Video video = videoRepository.findById(videoId)
            .orElseThrow(() -> new VideoNotFoundException("Video not found: " + videoId));
        
        return mapToResponse(video);
    }
    
    private VideoResponse mapToResponse(Video video) {
        return VideoResponse.builder()
            .id(video.getId())
            .title(video.getTitle())
            .videoUrl(video.getVideoUrl())
            .status(video.getStatus().name())
            .views(video.getViews())
            .createdAt(video.getCreatedAt())
            .build();
    }
}
```

---

#### 3. Video Processor (Consumer) (5 min)

```java
@Component
public class VideoProcessor {
    
    private final VideoRepository videoRepository;
    private final FFmpegService ffmpegService;
    private final S3StorageService storageService;
    
    @KafkaListener(topics = "video-upload-events", groupId = "video-processor")
    public void processVideo(VideoEvent event) {
        try {
            // Update status to processing
            Video video = videoRepository.findById(event.getVideoId())
                .orElseThrow(() -> new VideoNotFoundException("Video not found"));
            
            video.setStatus(VideoStatus.PROCESSING);
            videoRepository.save(video);
            
            // Download original video
            File originalVideo = storageService.downloadVideo(event.getVideoUrl());
            
            // Extract metadata (duration)
            int duration = ffmpegService.extractDuration(originalVideo);
            
            // Transcode to multiple resolutions
            List<TranscodedVideo> transcodedVideos = ffmpegService.transcode(
                originalVideo,
                Arrays.asList("1080p", "720p", "480p", "360p")
            );
            
            // Upload transcoded videos to S3
            for (TranscodedVideo transcoded : transcodedVideos) {
                storageService.uploadVideo(transcoded.getFile(), video.getId(), transcoded.getQuality());
            }
            
            // Update video status to READY
            video.setStatus(VideoStatus.READY);
            video.setDuration(duration);
            videoRepository.save(video);
            
            // Send notification to user
            notifyUser(video.getUserId(), "Your video is ready!");
            
        } catch (Exception e) {
            handleProcessingFailure(event.getVideoId(), e);
        }
    }
    
    private void handleProcessingFailure(Long videoId, Exception e) {
        Video video = videoRepository.findById(videoId).orElse(null);
        if (video != null) {
            video.setStatus(VideoStatus.FAILED);
            videoRepository.save(video);
        }
        // Log error, send alert
    }
}
```

---

### Phase 4: Design Patterns (5 min)

**Patterns Used**:

1. **Strategy Pattern** (Video Encoding)
```java
interface VideoEncoder {
    byte[] encode(File video, String quality);
}

class H264Encoder implements VideoEncoder { ... }
class H265Encoder implements VideoEncoder { ... }

class VideoEncodingService {
    private VideoEncoder encoder;
    
    public void setEncoder(VideoEncoder encoder) {
        this.encoder = encoder;
    }
    
    public byte[] encode(File video, String quality) {
        return encoder.encode(video, quality);
    }
}
```

2. **Factory Pattern** (Video Quality Creation)
```java
class VideoQualityFactory {
    public static VideoQuality create(String quality) {
        switch (quality) {
            case "1080p": return new VideoQuality1080p();
            case "720p": return new VideoQuality720p();
            default: throw new IllegalArgumentException();
        }
    }
}
```

3. **Observer Pattern** (Notifications)
```java
interface VideoEventListener {
    void onVideoReady(Video video);
}

class NotificationService implements VideoEventListener {
    public void onVideoReady(Video video) {
        sendPushNotification(video.getUserId(), "Video ready!");
    }
}
```

---

### Phase 5: Edge Cases & Testing (5 min)

**Edge Cases to Handle**:

1. **Duplicate Upload**
   - Solution: Check MD5 hash before upload
   
2. **Corrupted Video File**
   - Solution: Validate with FFmpeg before processing
   
3. **Concurrent Access to Same Video**
   - Solution: Optimistic locking with `@Version` annotation
   
4. **Out of Memory (Large Video)**
   - Solution: Stream processing instead of loading entire file

**Unit Test Example**:
```java
@Test
public void testUploadVideo_Success() {
    // Arrange
    MultipartFile file = new MockMultipartFile("video.mp4", new byte[1024]);
    VideoUploadRequest request = new VideoUploadRequest("Title", 1L);
    
    when(storageService.uploadVideo(any(), anyLong())).thenReturn("s3://bucket/video.mp4");
    when(videoRepository.save(any())).thenReturn(new Video(1L, "Title"));
    
    // Act
    VideoResponse response = videoService.createVideo(request, file);
    
    // Assert
    assertNotNull(response);
    assertEquals("Title", response.getTitle());
    verify(kafkaTemplate, times(1)).send(anyString(), any(VideoEvent.class));
}
```

---

## Common Questions & Answers

### Q1: How do you prevent duplicate video uploads?

**Answer**:
```
1. Hash-based deduplication:
   - Compute MD5/SHA-256 of uploaded file
   - Check if hash exists in database
   - If exists, return existing video ID
   
2. Benefits:
   - Save storage (no duplicate 2GB files)
   - Save processing time
   
3. Implementation:
   Video {
     contentHash: String (indexed)
   }
   
   Before upload:
     hash = computeHash(file)
     existingVideo = videoRepository.findByContentHash(hash)
     if (existingVideo) return existingVideo
```

---

### Q2: How do you handle a video going viral (10M views in 1 hour)?

**Answer**:
```
1. CDN Caching:
   - Video cached at 200+ edge locations
   - 99% cache hit ratio
   - Origin (S3) handles only 100K requests (1%)

2. Rate Limiting:
   - 100 API calls/min per user (search, comments)
   - No limit on video streaming (handled by CDN)

3. Auto-Scaling:
   - API servers scale from 10 → 50 instances
   - Trigger: CPU > 70% for 5 min

4. Database:
   - View count in Redis (write-back every 5 min)
   - Read replicas handle increased read load
```

---

### Q3: How do you count views accurately?

**Answer**:
```
Challenges:
- 1 billion views/day = 11K writes/sec to database (bottleneck)
- User refreshes page → should not count as new view

Solution:
1. Client-side:
   - Track "view" after 30 seconds of playback
   - Cookie: prevent duplicate within 24 hours

2. Backend:
   - Write to Redis (fast in-memory)
   - Batch write to DB every 5 minutes
   
3. Redis Structure:
   Key: views:videoId
   Value: count (incremented atomically)
   
4. Background Job (Cron every 5 min):
   - Read all keys: views:*
   - Batch update PostgreSQL
   - Delete Redis keys

Result:
- Handles 11K writes/sec (Redis can do 100K/sec)
- View count may lag 5 min (acceptable)
```

---

### Q4: How do you handle copyright detection (Content ID)?

**Answer**:
```
System: YouTube Content ID

1. Reference Database:
   - Copyright owners upload reference videos
   - Extract fingerprint (audio + video signatures)
   - Store in database

2. Upload Flow:
   User uploads video
      ↓
   Extract fingerprint
      ↓
   Compare against reference DB (ML model)
      ↓
   If match > 80% → Flag video
      ↓
   Options:
   a) Block video
   b) Monetize for copyright owner
   c) Mute audio

3. Technology:
   - Perceptual hashing (resistant to compression)
   - Audio fingerprinting (Shazam-like)
   - ML model: Siamese network for similarity

4. Scale:
   - 100M reference videos
   - 10M uploads/day to check
   - GPU cluster for parallel processing
```

---

## Cheat Sheet

### Key Numbers to Remember
```
DAU: 100M
Videos uploaded: 500 hours/min = 10M videos/day
Storage: 5 PB/day, 10 EB total (5 years)
RPS: 30K peak (video views)
Latency: <200ms video start
CDN cache hit: 90%+
Read/write ratio: 100:1
```

### AWS Services Quick Ref
```
Compute: EC2 (c6i.2xlarge), Lambda
Storage: S3 (videos), EBS (DB)
Database: RDS PostgreSQL, DocumentDB, ElastiCache Redis
CDN: CloudFront
Queue: MSK (Kafka)
Video: MediaConvert (transcoding)
Network: ALB, Route 53
Monitoring: CloudWatch, X-Ray
```

### Database Schema (5 Core Tables)
```
users: id, email, username
videos: id, user_id, title, url, views, status
comments: id, video_id, user_id, text, parent_id
likes: id, user_id, video_id
subscriptions: id, subscriber_id, channel_id
```

### Design Patterns
```
Strategy: Video encoding (H.264 vs H.265)
Factory: Create video quality objects
Observer: Notify subscribers on new upload
Singleton: S3 client
Builder: Video entity construction
```

### Must-Know Concepts
```
HLS: HTTP Live Streaming (adaptive bitrate)
CDN: Content Delivery Network (edge caching)
Sharding: Horizontal partitioning by user_id
Kafka: Event-driven async processing
Redis: In-memory cache (hot data)
S3 Lifecycle: Standard → IA → Glacier
```

---

## Final Tips

### For HLD Interview
1. **Always start with requirements** - don't jump to solution
2. **Draw diagrams** - whiteboard communication is key
3. **Mention numbers** - "CDN reduces load by 90%"
4. **Discuss trade-offs** - no perfect solution exists
5. **Think aloud** - interviewer wants to see your thought process

### For LLD Interview
1. **Clarify scope** - "Upload only or processing too?"
2. **Start with interfaces** - show abstraction skills
3. **Code readability** - use meaningful names, comments
4. **Handle errors** - try-catch, validation
5. **Mention testing** - "I would unit test this method"

### Red Flags to Avoid
❌ "This is easy" - shows overconfidence
❌ Jumping to code without design
❌ Ignoring scalability ("We can optimize later")
❌ Not asking clarifying questions
❌ Not discussing trade-offs

### Green Flags to Aim For
✅ "Let me clarify the requirements first"
✅ "Here's the trade-off: X vs Y"
✅ "At 100M users, we'll need sharding"
✅ "I would test this with..."
✅ "Alternative approach: ..."

---

## Success Rate by Preparation Level

| Preparation | HLD Pass Rate | LLD Pass Rate |
|-------------|---------------|---------------|
| Read docs only | 30% | 40% |
| + Drew diagrams | 60% | 60% |
| + Coded examples | 70% | 80% |
| + Mock interviews | 85% | 90% |

**Recommended**: 40-60 hours total prep (this guide = 20 hours)

---

**Good luck with your interview!** 🚀

Return to [Main README](README.md)
