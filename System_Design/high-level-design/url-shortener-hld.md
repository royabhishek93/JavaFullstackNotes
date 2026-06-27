# High-Level Design: URL Shortener Service (bit.ly, TinyURL)

## System Overview
Design a scalable URL shortening service like bit.ly or TinyURL that converts long URLs into short, manageable links, handles billions of requests per day, provides analytics, and ensures high availability with sub-100ms latency.

**Target Audience**: 15+ years experienced architect interview

---

## Requirements

### Functional Requirements
1. **Shorten URL**: Given a long URL, generate a unique short URL (e.g., `https://short.ly/abc123`)
2. **Redirect**: When user visits short URL, redirect to original long URL (301/302)
3. **Custom Aliases**: Allow users to specify custom short codes
4. **Expiration**: URLs expire after specified time (default: never)
5. **Analytics**: Track click count, geographic location, referrer, device type
6. **API Access**: RESTful API for programmatic URL creation
7. **URL Validation**: Validate and sanitize input URLs
8. **Delete/Update**: Allow users to delete or update their short URLs

### Non-Functional Requirements
1. **Scalability**: Handle 100M+ URL creations per day, 10B+ redirects per day
2. **Availability**: 99.99% uptime (4 nines)
3. **Latency**: 
   - URL creation: < 200ms (p99)
   - Redirection: < 100ms (p99)
4. **Durability**: No data loss (URLs must persist)
5. **Consistency**: Eventual consistency acceptable for analytics
6. **Security**: Prevent abuse, malicious URLs, rate limiting
7. **SEO Friendly**: Support 301 (permanent) and 302 (temporary) redirects

---

## Capacity Estimation

### Traffic Estimates
- **Daily Active Users**: 100 million
- **URL Shortening**: 100M URLs/day = 1,157 URLs/sec (avg), ~5,000 URLs/sec (peak)
- **URL Redirection**: 10B redirects/day = 115,740 redirects/sec (avg), ~500K redirects/sec (peak)
- **Read/Write Ratio**: 100:1 (read-heavy system)

### Storage Estimates
**URL Data**:
- Average long URL length: 200 bytes
- Short code: 7 characters (62^7 = 3.5 trillion combinations)
- Metadata: 100 bytes (created_at, user_id, expiry, etc.)
- **Per URL**: ~500 bytes

**Total Storage** (5 years retention):
- URLs created: 100M/day × 365 days × 5 years = 182.5 billion URLs
- Storage: 182.5B × 500 bytes = **91 TB**

**Analytics Data** (clicks):
- 10B clicks/day × 200 bytes/click × 365 days = **730 TB/year**

**With compression and archival**: ~50% reduction → **400 TB total**

### Bandwidth Estimates
**Incoming (URL Creation)**:
- 1,157 URLs/sec × 500 bytes = **0.6 MB/s** = 4.8 Mbps

**Outgoing (Redirects)**:
- 115,740 redirects/sec × 500 bytes = **58 MB/s** = 464 Mbps

**Peak**: 500K redirects/sec × 500 bytes = **250 GB/s** = 2 Tbps (CDN required!)

### Cache Requirements
- Cache hot URLs (80/20 rule: 20% URLs = 80% traffic)
- 20% of daily active URLs: 2B URLs × 500 bytes = **1 TB cache**
- Distributed across 100 cache nodes = **10 GB per node**

---

## System Architecture

```
                                    ┌──────────────────────────────┐
                                    │        DNS (Route 53)        │
                                    │    short.ly → Load Balancer  │
                                    └──────────────┬───────────────┘
                                                   │
                                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Global Load Balancer (AWS ALB)                       │
│                  (Geographic routing, SSL termination)                       │
└───────────────┬─────────────────────────────────────────┬───────────────────┘
                │                                         │
        ┌───────▼──────────┐                    ┌────────▼──────────┐
        │   US-East Region │                    │  EU-West Region   │
        │                  │                    │                   │
        │  ┌────────────┐  │                    │  ┌────────────┐   │
        │  │ CDN (CF)   │  │                    │  │ CDN (CF)   │   │
        │  │ Edge Cache │  │                    │  │ Edge Cache │   │
        │  └──────┬─────┘  │                    │  └──────┬─────┘   │
        │         │        │                    │         │         │
        │         ▼        │                    │         ▼         │
        │  ┌────────────┐  │                    │  ┌────────────┐   │
        │  │ Regional   │  │                    │  │ Regional   │   │
        │  │ LB (ALB)   │  │                    │  │ LB (ALB)   │   │
        │  └──────┬─────┘  │                    │  └──────┬─────┘   │
        └─────────┼────────┘                    └─────────┼─────────┘
                  │                                       │
         ┌────────┴────────┬─────────────┐              │
         │                 │             │              │
         ▼                 ▼             ▼              ▼
┌─────────────────┐ ┌──────────────┐ ┌──────────────┐ ...
│ API Gateway     │ │ API Gateway  │ │ API Gateway  │
│ (Rate Limiting) │ │ (Auth)       │ │ (Validation) │
└────────┬────────┘ └──────┬───────┘ └──────┬───────┘
         │                 │                │
    ┌────┴─────┬──────────┼────────────────┘
    │          │          │
    ▼          ▼          ▼
┌─────────┐ ┌──────────┐ ┌────────────┐
│ Write   │ │ Read     │ │ Analytics  │
│ Service │ │ Service  │ │ Service    │
│ (Create)│ │(Redirect)│ │ (Metrics)  │
└────┬────┘ └────┬─────┘ └─────┬──────┘
     │           │              │
     │     ┌─────▼────────┐     │
     │     │ Distributed  │     │
     │     │ Cache        │     │
     │     │ (Redis)      │     │
     │     └─────┬────────┘     │
     │           │              │
     │           ▼              │
     │     ┌──────────────┐     │
     └────▶│  Database    │◀────┘
           │  Cluster     │
           │ (PostgreSQL) │
           └──────┬───────┘
                  │
           ┌──────▼────────┐
           │  Analytics    │
           │  Data Store   │
           │  (Cassandra)  │
           └───────────────┘
```

---

## Core Components

### 1. API Gateway Layer

**Responsibilities**:
- Rate limiting (prevent abuse)
- Authentication/Authorization
- Request validation
- SSL/TLS termination
- API versioning
- Request routing

**Rate Limiting Strategy**:
```
User Tiers:
- Anonymous: 10 URLs/hour, 100 redirects/min
- Free User: 100 URLs/day, 1000 redirects/min
- Premium: 10K URLs/day, unlimited redirects
```

**Implementation**:
```java
@RestController
@RequestMapping("/api/v1")
public class URLController {
    
    @RateLimited(limit = 100, window = "1h")
    @PostMapping("/shorten")
    public ResponseEntity<ShortURLResponse> shortenURL(
            @RequestBody @Valid ShortURLRequest request) {
        return urlService.createShortURL(request);
    }
    
    @RateLimited(limit = 10000, window = "1m")
    @GetMapping("/{shortCode}")
    public ResponseEntity<Void> redirect(
            @PathVariable String shortCode,
            HttpServletRequest httpRequest) {
        
        String longURL = urlService.getLongURL(shortCode);
        
        // Async analytics tracking (non-blocking)
        analyticsService.trackClickAsync(shortCode, httpRequest);
        
        return ResponseEntity
            .status(HttpStatus.MOVED_PERMANENTLY)
            .header("Location", longURL)
            .build();
    }
}
```

---

### 2. Write Service (URL Creation)

**Responsibilities**:
- Generate unique short codes
- Validate and sanitize URLs
- Store URL mappings
- Handle custom aliases
- Duplicate detection

#### Short Code Generation Strategies

**Option 1: Base62 Encoding (Hash-based)**
```java
public class Base62ShortCodeGenerator {
    private static final String BASE62 = 
        "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
    
    public String generateShortCode(String longURL) {
        // MD5 hash of URL + timestamp + salt
        String hash = MD5(longURL + System.nanoTime() + SALT);
        
        // Take first 43 bits → encode as 7 base62 characters
        long num = Long.parseLong(hash.substring(0, 10), 16);
        return toBase62(num, 7);
    }
    
    private String toBase62(long num, int length) {
        StringBuilder sb = new StringBuilder();
        while (num > 0 && sb.length() < length) {
            sb.append(BASE62.charAt((int)(num % 62)));
            num /= 62;
        }
        return sb.reverse().toString().padStart(length, '0');
    }
}
```

**Pros**: Simple, fast, no coordination
**Cons**: Collision possible (requires retry), not sequential

---

**Option 2: Counter-based (Distributed ID Generator - Snowflake)**
```java
public class SnowflakeIDGenerator {
    // 64-bit ID structure:
    // 1 bit (unused) | 41 bits (timestamp) | 10 bits (machine ID) | 12 bits (sequence)
    
    private long epoch = 1609459200000L; // 2021-01-01
    private long machineId;
    private long sequence = 0L;
    private long lastTimestamp = -1L;
    
    public synchronized long nextId() {
        long timestamp = System.currentTimeMillis();
        
        if (timestamp < lastTimestamp) {
            throw new RuntimeException("Clock moved backwards!");
        }
        
        if (timestamp == lastTimestamp) {
            sequence = (sequence + 1) & 0xFFF; // 12 bits
            if (sequence == 0) {
                timestamp = waitNextMillis(lastTimestamp);
            }
        } else {
            sequence = 0;
        }
        
        lastTimestamp = timestamp;
        
        return ((timestamp - epoch) << 22) 
             | (machineId << 12) 
             | sequence;
    }
    
    public String toShortCode(long id) {
        return toBase62(id, 7);
    }
}
```

**Pros**: No collisions, ordered, high throughput
**Cons**: Requires machine coordination, predictable

---

**Option 3: Zookeeper/Redis Counter (Recommended)**
```java
public class RedisCounterGenerator {
    private RedisTemplate<String, Long> redis;
    
    public String generateShortCode() {
        // Atomically increment global counter
        Long id = redis.opsForValue().increment("url:counter", 1);
        
        // Convert to base62 (7 characters)
        return toBase62(id, 7);
    }
    
    // Redis atomic operation guarantees uniqueness
}
```

**Pros**: Guaranteed unique, simple, centralized
**Cons**: Single point of failure (mitigated by Redis Cluster), slight latency

---

**Recommended: Hybrid Approach**
```java
public class HybridShortCodeGenerator {
    private SnowflakeIDGenerator snowflake;
    private RedisTemplate<String, String> redis;
    
    public String generateShortCode(String longURL, String customAlias) {
        // Option 1: Custom alias (if provided)
        if (customAlias != null) {
            if (isAvailable(customAlias)) {
                return customAlias;
            }
            throw new AliasAlreadyExistsException();
        }
        
        // Option 2: Check if URL already shortened (idempotency)
        String existingCode = redis.opsForValue().get("url:long:" + longURL);
        if (existingCode != null) {
            return existingCode;
        }
        
        // Option 3: Generate new unique code
        String shortCode = toBase62(snowflake.nextId(), 7);
        return shortCode;
    }
}
```

---

### 3. Read Service (URL Redirection)

**Responsibilities**:
- Resolve short code to long URL
- Return HTTP redirect (301/302)
- Handle cache misses
- Track analytics (async)

**Multi-layer Caching Strategy**:
```
Request → CDN Edge Cache (CloudFront)
          ↓ (miss)
          → Application Cache (Redis L1)
          ↓ (miss)
          → Local In-Memory Cache (Caffeine)
          ↓ (miss)
          → Database (PostgreSQL/Cassandra)
```

**Implementation**:
```java
@Service
public class URLRedirectionService {
    
    @Autowired private RedisCache redis;
    @Autowired private LocalCache caffeine;
    @Autowired private URLRepository repository;
    @Autowired private AnalyticsService analytics;
    
    public String getLongURL(String shortCode) {
        // L1: Local in-memory cache (Caffeine) - 1ms
        String longURL = caffeine.get(shortCode);
        if (longURL != null) {
            return longURL;
        }
        
        // L2: Redis distributed cache - 5ms
        longURL = redis.get("url:short:" + shortCode);
        if (longURL != null) {
            caffeine.put(shortCode, longURL); // Populate L1
            return longURL;
        }
        
        // L3: Database - 50ms
        URLMapping mapping = repository.findByShortCode(shortCode);
        if (mapping == null) {
            throw new URLNotFoundException();
        }
        
        // Check expiration
        if (mapping.isExpired()) {
            return "https://short.ly/expired";
        }
        
        longURL = mapping.getLongURL();
        
        // Populate caches
        redis.setex("url:short:" + shortCode, 3600, longURL); // 1 hour TTL
        caffeine.put(shortCode, longURL);
        
        return longURL;
    }
}
```

**Cache Eviction Strategy**:
- **TTL**: Hot URLs cached for 1 hour, warm URLs for 10 minutes
- **LRU**: Least recently used evicted when cache full
- **Proactive Refresh**: Top 1000 URLs refreshed every 5 minutes

---

### 4. Analytics Service

**Responsibilities**:
- Track clicks in real-time
- Extract metadata (IP, User-Agent, Referrer)
- Aggregate metrics (daily/hourly counts)
- Geographic analysis

**Event Schema**:
```json
{
  "short_code": "abc123",
  "timestamp": 1699564800000,
  "ip_address": "203.0.113.42",
  "country": "US",
  "city": "San Francisco",
  "user_agent": "Mozilla/5.0...",
  "device_type": "mobile",
  "os": "iOS",
  "browser": "Safari",
  "referrer": "https://twitter.com/...",
  "is_bot": false
}
```

**Architecture**:
```
Click Event
    ↓
Kafka Topic (click-events)
    ↓
┌─────────────────┬──────────────────┬──────────────────┐
│ Real-time       │ Batch Processing │ Stream           │
│ Counter         │ (Spark/Flink)    │ Processing       │
│ (Redis)         │ ↓                │ (Storm)          │
│ Increments:     │ Aggregations:    │ Anomaly          │
│ - Click count   │ - Daily stats    │ Detection:       │
│ - Hourly views  │ - Top countries  │ - Bot traffic    │
│                 │ - Device breakdown│ - DDoS           │
└─────────────────┴──────────────────┴──────────────────┘
                  ↓                   ↓
            Cassandra              Elasticsearch
         (Time-series data)       (Search & Analytics)
```

**Implementation**:
```java
@Service
public class AnalyticsService {
    
    @Autowired private KafkaTemplate<String, ClickEvent> kafka;
    @Autowired private RedisTemplate<String, Long> redis;
    
    @Async
    public void trackClickAsync(String shortCode, HttpServletRequest request) {
        ClickEvent event = ClickEvent.builder()
            .shortCode(shortCode)
            .timestamp(System.currentTimeMillis())
            .ipAddress(extractIP(request))
            .userAgent(request.getHeader("User-Agent"))
            .referrer(request.getHeader("Referer"))
            .build();
        
        // Send to Kafka for async processing
        kafka.send("click-events", shortCode, event);
        
        // Real-time counter (Redis)
        redis.opsForValue().increment("clicks:" + shortCode);
        redis.opsForHash().increment("clicks:hourly", 
            shortCode + ":" + getCurrentHour(), 1);
    }
    
    public ClickStats getStats(String shortCode) {
        Long totalClicks = redis.opsForValue().get("clicks:" + shortCode);
        
        // Fetch detailed stats from Cassandra
        List<DailyStats> dailyStats = cassandra.query(
            "SELECT date, clicks FROM url_analytics WHERE short_code = ?",
            shortCode
        );
        
        return ClickStats.builder()
            .totalClicks(totalClicks)
            .dailyBreakdown(dailyStats)
            .build();
    }
}
```

---

### 5. Database Design

#### Primary Database (PostgreSQL) - URL Mappings

**Schema**:
```sql
CREATE TABLE url_mappings (
    id BIGSERIAL PRIMARY KEY,
    short_code VARCHAR(10) UNIQUE NOT NULL,
    long_url TEXT NOT NULL,
    user_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    is_custom_alias BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'active', -- active, expired, deleted
    
    INDEX idx_short_code (short_code),
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at),
    INDEX idx_expires_at (expires_at)
);

CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    api_key VARCHAR(64) UNIQUE,
    tier VARCHAR(20), -- anonymous, free, premium
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Materialized view for quick lookups (read-optimized)
CREATE MATERIALIZED VIEW active_urls AS
SELECT short_code, long_url, expires_at
FROM url_mappings
WHERE status = 'active' 
  AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
WITH DATA;

CREATE UNIQUE INDEX ON active_urls(short_code);
```

**Partitioning Strategy** (for 100B+ rows):
```sql
-- Partition by creation date (monthly)
CREATE TABLE url_mappings_2024_01 PARTITION OF url_mappings
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE url_mappings_2024_02 PARTITION OF url_mappings
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- Auto-partition using pg_partman
```

**Sharding Strategy** (horizontal scaling):
```
Shard Key: HASH(short_code) % NUM_SHARDS

Shard 0: short_codes 0000000 - 1999999
Shard 1: short_codes 2000000 - 3999999
Shard 2: short_codes 4000000 - 5999999
...
```

---

#### Analytics Database (Cassandra) - Time-series Data

**Schema**:
```cql
CREATE TABLE click_events (
    short_code TEXT,
    click_date DATE,
    click_hour INT,
    click_id TIMEUUID,
    ip_address TEXT,
    country TEXT,
    city TEXT,
    device_type TEXT,
    browser TEXT,
    referrer TEXT,
    PRIMARY KEY ((short_code, click_date), click_hour, click_id)
) WITH CLUSTERING ORDER BY (click_hour DESC, click_id DESC);

-- Aggregated stats (pre-computed)
CREATE TABLE url_analytics_daily (
    short_code TEXT,
    date DATE,
    total_clicks COUNTER,
    unique_ips COUNTER,
    mobile_clicks COUNTER,
    desktop_clicks COUNTER,
    PRIMARY KEY (short_code, date)
) WITH CLUSTERING ORDER BY (date DESC);

CREATE TABLE url_analytics_country (
    short_code TEXT,
    country TEXT,
    date DATE,
    clicks COUNTER,
    PRIMARY KEY ((short_code, country), date)
);
```

**Read Pattern Optimization**:
```
Query: "Get clicks for 'abc123' in last 7 days"
→ Single partition read on (abc123, [2024-01-15 to 2024-01-22])
→ O(1) lookup, no scatter-gather
```

---

## Advanced Features

### 1. URL Expiration & Cleanup

**Implementation**:
```java
@Scheduled(cron = "0 0 2 * * *") // Run at 2 AM daily
public void cleanupExpiredURLs() {
    LocalDateTime now = LocalDateTime.now();
    
    // Soft delete (mark as expired)
    int count = repository.updateExpiredURLs(now);
    
    log.info("Marked {} URLs as expired", count);
    
    // Archive old URLs to cold storage (S3/Glacier)
    List<URLMapping> oldURLs = repository.findOlderThan(
        now.minusYears(2)
    );
    
    s3Service.archiveBatch(oldURLs);
    repository.deleteAll(oldURLs);
}
```

---

### 2. Security & Abuse Prevention

**Malicious URL Detection**:
```java
@Service
public class URLSecurityService {
    
    @Autowired private VirusTotalAPI virusTotal;
    @Autowired private GoogleSafeBrowsingAPI safeBrowsing;
    
    public boolean isSafe(String url) {
        // Check against known blacklists
        if (isBlacklisted(url)) {
            return false;
        }
        
        // VirusTotal scan
        VirusTotalReport report = virusTotal.scan(url);
        if (report.getPositives() > 2) {
            return false;
        }
        
        // Google Safe Browsing
        if (safeBrowsing.isMalicious(url)) {
            return false;
        }
        
        return true;
    }
    
    private boolean isBlacklisted(String url) {
        // Regex patterns for common phishing/spam domains
        return url.matches(".*(bit\\.do|tinyurl\\.ru|000webhostapp).*");
    }
}
```

**Rate Limiting (Token Bucket)**:
```java
@Component
public class TokenBucketRateLimiter {
    
    private RedisTemplate<String, String> redis;
    
    public boolean allowRequest(String userId, int maxTokens, int refillRate) {
        String key = "rate_limit:" + userId;
        
        // Lua script for atomic token bucket
        String script = """
            local tokens = redis.call('get', KEYS[1])
            if not tokens then
                tokens = ARGV[1]
            end
            if tonumber(tokens) > 0 then
                redis.call('decr', KEYS[1])
                return 1
            else
                return 0
            end
        """;
        
        Long result = redis.execute(
            RedisScript.of(script, Long.class),
            Collections.singletonList(key),
            String.valueOf(maxTokens)
        );
        
        return result == 1;
    }
}
```

---

### 3. Custom Domains (Enterprise Feature)

**Use Case**: Companies want `go.company.com/abc123` instead of `short.ly/abc123`

**DNS Setup**:
```
Customer: Create CNAME record
    go.company.com → short.ly.cdn.cloudfront.net

Our Side:
1. Validate domain ownership (TXT record verification)
2. Provision SSL certificate (Let's Encrypt)
3. Add to CDN configuration
4. Store domain mapping in DB
```

**Implementation**:
```sql
CREATE TABLE custom_domains (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    domain VARCHAR(255) UNIQUE NOT NULL,
    ssl_cert_id VARCHAR(100),
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**Routing Logic**:
```java
public String resolveDomain(String host, String shortCode) {
    if (host.equals("short.ly")) {
        return getLongURL(shortCode);
    }
    
    // Check custom domain
    CustomDomain domain = domainRepo.findByDomain(host);
    if (domain != null && domain.isVerified()) {
        return getLongURL(shortCode, domain.getUserId());
    }
    
    throw new InvalidDomainException();
}
```

---

### 4. QR Code Generation

**On-the-fly generation**:
```java
@GetMapping("/{shortCode}/qr")
public ResponseEntity<byte[]> generateQRCode(
        @PathVariable String shortCode,
        @RequestParam(defaultValue = "200") int size) {
    
    String shortURL = "https://short.ly/" + shortCode;
    
    // Generate QR code using ZXing
    BitMatrix matrix = new QRCodeWriter().encode(
        shortURL,
        BarcodeFormat.QR_CODE,
        size,
        size
    );
    
    byte[] qrImage = MatrixToImageWriter.toBufferedImage(matrix);
    
    return ResponseEntity.ok()
        .contentType(MediaType.IMAGE_PNG)
        .cacheControl(CacheControl.maxAge(7, TimeUnit.DAYS))
        .body(qrImage);
}
```

---

## Deployment Architecture

### Multi-Region Deployment

```
┌─────────────────────────────────────────────────────────────────┐
│                      Route 53 (DNS)                              │
│  Latency-based routing: short.ly → nearest region               │
└───────────────┬─────────────────────────────┬───────────────────┘
                │                             │
        ┌───────▼──────────┐          ┌──────▼───────────┐
        │   US-EAST-1      │          │   EU-WEST-1      │
        │                  │          │                  │
        │  ┌────────────┐  │          │  ┌────────────┐  │
        │  │ App Tier   │  │          │  │ App Tier   │  │
        │  │ (ECS/K8s)  │  │          │  │ (ECS/K8s)  │  │
        │  └──────┬─────┘  │          │  └──────┬─────┘  │
        │         │        │          │         │        │
        │  ┌──────▼─────┐  │          │  ┌──────▼─────┐  │
        │  │ Redis      │  │          │  │ Redis      │  │
        │  │ Cluster    │  │          │  │ Cluster    │  │
        │  └──────┬─────┘  │          │  └──────┬─────┘  │
        │         │        │          │         │        │
        │  ┌──────▼─────┐  │          │  ┌──────▼─────┐  │
        │  │ PostgreSQL │◀─┼──────────┼─▶│ PostgreSQL │  │
        │  │ (Primary)  │  │          │  │ (Replica)  │  │
        │  └────────────┘  │          │  └────────────┘  │
        └──────────────────┘          └──────────────────┘
                │                             │
                └──────────┬──────────────────┘
                           ▼
                   ┌───────────────┐
                   │  Cassandra    │
                   │  (Multi-DC)   │
                   │  Replication  │
                   └───────────────┘
```

**Write Propagation**:
- Primary region: US-EAST-1 (writes)
- Secondary regions: Asynchronous replication (eventual consistency)
- Analytics: Multi-datacenter Cassandra (writes to local DC)

---

### Scaling Strategy

**Horizontal Scaling**:
```yaml
# Kubernetes Auto-scaling
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: url-shortener-api
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: url-shortener-api
  minReplicas: 10
  maxReplicas: 1000
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "1000"
```

**Database Scaling**:
- **Vertical**: Upgrade to larger RDS instances (r6g.16xlarge - 512 GB RAM)
- **Horizontal**: Read replicas (10+ replicas for read traffic)
- **Sharding**: Hash-based sharding on `short_code`

---

## Monitoring & Observability

### Key Metrics

**Golden Signals**:
1. **Latency**: p50, p95, p99 response times
2. **Traffic**: Requests per second
3. **Errors**: 4xx, 5xx error rates
4. **Saturation**: CPU, memory, disk I/O

**Custom Metrics**:
```java
@Timed(value = "url.shorten", percentiles = {0.5, 0.95, 0.99})
public String shortenURL(String longURL) {
    // ... implementation
}

@Counted(value = "url.redirect", extraTags = {"status", "200"})
public void redirect(String shortCode) {
    // ... implementation
}

@Gauge(value = "cache.hit_rate")
public double getCacheHitRate() {
    return (double) cacheHits / (cacheHits + cacheMisses);
}
```

**Dashboards** (Grafana):
```
┌─────────────────────────────────────────────────────────┐
│ URL Shortener - Production Dashboard                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│ │ Requests/sec │  │ P99 Latency  │  │ Error Rate   │   │
│ │   125,432    │  │    87ms      │  │    0.03%     │   │
│ └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                          │
│ ┌─────────────────────────────────────────────────────┐ │
│ │         Redirect Latency (P50, P95, P99)            │ │
│ │  [Chart showing latency over time]                  │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                          │
│ ┌─────────────────────────────────────────────────────┐ │
│ │         Cache Hit Rate (Redis + Caffeine)           │ │
│ │  [Chart showing 94.7% hit rate]                     │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                          │
│ ┌─────────────────────────────────────────────────────┐ │
│ │         Database Connection Pool Utilization        │ │
│ │  [Chart showing 68% utilization]                    │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**Alerting** (PagerDuty):
```yaml
alerts:
  - name: HighErrorRate
    condition: error_rate > 1%
    duration: 5m
    severity: critical
    
  - name: HighLatency
    condition: p99_latency > 200ms
    duration: 10m
    severity: warning
    
  - name: CacheHitRateLow
    condition: cache_hit_rate < 80%
    duration: 15m
    severity: warning
    
  - name: DatabaseConnectionsExhausted
    condition: db_connections > 90%
    duration: 5m
    severity: critical
```

---

## Disaster Recovery & High Availability

### Backup Strategy

**Database Backups**:
- **Automated snapshots**: Every 6 hours (RDS automated backups)
- **Point-in-time recovery**: Up to 35 days
- **Cross-region replication**: Async replication to DR region
- **Backup retention**: 90 days

**Redis Backups**:
- **RDB snapshots**: Every hour
- **AOF (Append-Only File)**: Enabled for durability
- **Replica nodes**: 2 replicas per master

### Disaster Recovery Plan

**Failure Scenarios**:

1. **Single server failure**:
   - Auto-scaling group replaces failed instance (< 2 min)
   - Load balancer routes traffic to healthy instances
   - **RTO**: 2 minutes, **RPO**: 0 (no data loss)

2. **Availability Zone failure**:
   - Multi-AZ deployment (3 AZs minimum)
   - ALB routes to healthy AZs
   - **RTO**: < 1 minute, **RPO**: 0

3. **Regional failure** (entire AWS region down):
   - Route 53 failover to secondary region (EU-WEST-1)
   - Manual promotion of read replica to primary
   - **RTO**: 15 minutes, **RPO**: < 5 minutes

4. **Complete data loss** (catastrophic):
   - Restore from S3 cross-region backup
   - Replay Kafka events (if available)
   - **RTO**: 4 hours, **RPO**: 6 hours

---

## API Design

### RESTful API Endpoints

```yaml
# Create Short URL
POST /api/v1/shorten
Request:
  {
    "long_url": "https://www.example.com/very/long/url",
    "custom_alias": "mylink",  # Optional
    "expires_at": "2024-12-31T23:59:59Z"  # Optional
  }
Response:
  {
    "short_url": "https://short.ly/abc123",
    "short_code": "abc123",
    "long_url": "https://www.example.com/very/long/url",
    "created_at": "2024-01-15T10:30:00Z",
    "expires_at": "2024-12-31T23:59:59Z"
  }

# Get URL Info
GET /api/v1/urls/{shortCode}
Response:
  {
    "short_code": "abc123",
    "long_url": "https://www.example.com/very/long/url",
    "created_at": "2024-01-15T10:30:00Z",
    "click_count": 1234,
    "status": "active"
  }

# Update URL
PUT /api/v1/urls/{shortCode}
Request:
  {
    "long_url": "https://www.updated-url.com",
    "expires_at": "2025-01-01T00:00:00Z"
  }

# Delete URL
DELETE /api/v1/urls/{shortCode}

# Get Analytics
GET /api/v1/urls/{shortCode}/analytics?from=2024-01-01&to=2024-01-31
Response:
  {
    "short_code": "abc123",
    "total_clicks": 12456,
    "unique_visitors": 8932,
    "daily_breakdown": [
      {"date": "2024-01-01", "clicks": 150},
      {"date": "2024-01-02", "clicks": 203}
    ],
    "country_breakdown": [
      {"country": "US", "clicks": 5000},
      {"country": "IN", "clicks": 3000}
    ],
    "device_breakdown": {
      "mobile": 7000,
      "desktop": 5000,
      "tablet": 456
    }
  }

# Redirect (User-facing)
GET /{shortCode}
Response: 301/302 Redirect to long_url
```

---

## Trade-offs & Design Decisions

### 1. Short Code Generation

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **Hash-based (MD5/SHA)** | Simple, no coordination | Collisions, requires retry | ❌ Not chosen |
| **Counter (Redis)** | No collisions, simple | Single point, predictable | ✅ **Chosen** (with HA) |
| **Snowflake ID** | Distributed, ordered | Requires coordination | ⚠️ Backup option |

**Chosen**: Redis counter with Redis Cluster (HA) + Snowflake as fallback

---

### 2. Redirect Type (301 vs 302)

| Type | Use Case | Caching | Analytics |
|------|----------|---------|-----------|
| **301 Permanent** | Static URLs, SEO benefit | Browser caches (less server load) | Miss subsequent clicks |
| **302 Temporary** | Dynamic URLs, tracking | No browser cache | Track every click |

**Chosen**: **302 by default** (better analytics), 301 for premium users (better SEO)

---

### 3. Database Choice

| Database | Use Case | Pros | Cons |
|----------|----------|------|------|
| **PostgreSQL** | URL mappings | ACID, transactions, indexing | Limited horizontal scaling |
| **Cassandra** | Analytics | Write-optimized, scalable | Eventual consistency |
| **DynamoDB** | Alternative | Managed, auto-scaling | Expensive at scale |

**Chosen**: PostgreSQL (primary) + Cassandra (analytics)

---

### 4. Caching Strategy

**Write-through vs Write-around**:
- **Write-through**: Update cache on write (complex, overkill)
- **Write-around**: Skip cache on write, populate on read
- **Chosen**: **Write-around** (simpler, read-heavy workload)

**Cache Invalidation**:
- TTL-based expiration (1 hour for hot URLs)
- No manual invalidation (eventual consistency OK)

---

## Cost Estimation (AWS)

### Monthly Cost Breakdown (100M URLs/day, 10B redirects/day)

```
Application Tier (ECS Fargate):
  - 200 containers × $0.04/hour × 730 hours = $5,840/month

Load Balancers (ALB):
  - 3 ALBs × $16.20/month = $48.60
  - LCU charges: ~$500/month
  
Database (RDS PostgreSQL):
  - Primary: db.r6g.8xlarge ($2.08/hour × 730) = $1,518
  - Read replicas: 5 × $1,518 = $7,590
  
Redis (ElastiCache):
  - 10 × cache.r6g.2xlarge ($0.504/hour × 730) = $3,680
  
Cassandra (Managed Cassandra):
  - 20 nodes × $0.40/hour × 730 = $5,840
  
CloudFront (CDN):
  - Data transfer: 10B requests × $0.0075/10K = $7,500
  - HTTP requests: 10B × $0.0075/10K = $7,500
  
S3 Storage (Backups):
  - 100 TB × $0.023/GB = $2,300
  
Data Transfer:
  - 100 TB outbound × $0.09/GB = $9,000

Total: ~$51,316/month (~$616K/year)

Per URL cost: $0.00051 per URL created
Per redirect cost: $0.0000051 per redirect
```

**Optimization opportunities**:
- Use Spot instances (save 70% on compute)
- Reserved instances (save 40% on RDS/Redis)
- CloudFront savings bundle
- **Optimized cost**: ~$300K/year

---

## Interview Discussion Points

### 1. **Scalability Deep Dive**
- "How do you handle 1M requests/second?"
  - **Answer**: Multi-region CDN + Redis caching + horizontal scaling + database read replicas

- "What if Redis goes down?"
  - **Answer**: Redis Cluster (HA), Sentinel for failover, fallback to DB (degraded performance)

### 2. **Consistency vs Availability**
- "CAP theorem choice?"
  - **Answer**: AP system (availability + partition tolerance), eventual consistency OK for analytics

### 3. **Hot URL Problem**
- "What if one URL gets 1M hits/sec?"
  - **Answer**: CDN edge caching (CloudFront), in-memory cache at app layer, database not hit

### 4. **Short Code Exhaustion**
- "What happens when you run out of 7-character codes?"
  - **Answer**: 62^7 = 3.5 trillion codes (enough for 95 years at 100M/day), can expand to 8 characters

### 5. **URL Conflicts**
- "How do you prevent duplicate short codes?"
  - **Answer**: Redis atomic counter guarantees uniqueness, database unique constraint as safety net

### 6. **Security**
- "How to prevent abuse?"
  - **Answer**: Rate limiting, CAPTCHA, API keys, URL scanning (VirusTotal), blacklist known phishing domains

### 7. **Analytics Accuracy**
- "Bots skewing analytics?"
  - **Answer**: User-Agent filtering, IP reputation checks, behavioral analysis, bot detection (reCAPTCHA)

### 8. **Cross-region Consistency**
- "User creates URL in US, immediately accesses from EU - will it work?"
  - **Answer**: Async replication lag (~1-2 seconds), can use synchronous replication for premium users (slower writes)

### 9. **Cost Optimization**
- "How to reduce $600K/year cost?"
  - **Answer**: Spot instances, reserved capacity, aggressive caching, compress analytics data, archive old URLs

### 10. **Future Enhancements**
- Link rotation (A/B testing)
- Passwordprotected URLs
- Geo-fencing (restrict by country)
- Link preview (Open Graph metadata)
- Branded short domains
- API SDKs (Python, Java, Node.js)

---

## Conclusion

This URL shortener design handles **10 billion redirects per day** with:
- ✅ Sub-100ms latency (p99)
- ✅ 99.99% availability
- ✅ Horizontal scalability (1000+ servers)
- ✅ Multi-region deployment
- ✅ Comprehensive analytics
- ✅ Security & abuse prevention
- ✅ Cost-effective ($300K/year optimized)

**Key architectural decisions**:
1. Redis counter for unique short code generation
2. Multi-layer caching (CDN + Redis + Local)
3. PostgreSQL for transactional data, Cassandra for analytics
4. Async analytics processing (Kafka + stream processing)
5. Multi-region active-passive deployment

**Ready for 15-year architect interview** ✅

---
---

# LOW-LEVEL DESIGN (LLD) - URL SHORTENER

## Class Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         «interface»                                 │
│                      URLShortenerService                            │
├─────────────────────────────────────────────────────────────────────┤
│ + createShortURL(request: ShortURLRequest): ShortURLResponse       │
│ + getLongURL(shortCode: String): String                            │
│ + getURLInfo(shortCode: String): URLInfo                           │
│ + updateURL(shortCode: String, request: UpdateRequest): void       │
│ + deleteURL(shortCode: String): void                               │
│ + getAnalytics(shortCode: String, filter: AnalyticsFilter): Stats  │
└─────────────────────────────────────────────────────────────────────┘
                               △
                               │ implements
                               │
┌──────────────────────────────┴──────────────────────────────────────┐
│                   URLShortenerServiceImpl                           │
├─────────────────────────────────────────────────────────────────────┤
│ - shortCodeGenerator: ShortCodeGenerator                           │
│ - urlRepository: URLRepository                                      │
│ - cacheService: CacheService                                        │
│ - analyticsService: AnalyticsService                                │
│ - securityService: SecurityService                                  │
│ - rateLimiter: RateLimiter                                          │
├─────────────────────────────────────────────────────────────────────┤
│ + createShortURL(request: ShortURLRequest): ShortURLResponse       │
│ + getLongURL(shortCode: String): String                            │
│ - validateURL(url: String): boolean                                │
│ - checkDuplicate(url: String): Optional<String>                    │
└─────────────────────────────────────────────────────────────────────┘
           │                    │                    │
           │ uses               │ uses               │ uses
           ▼                    ▼                    ▼
┌────────────────────┐  ┌─────────────────┐  ┌─────────────────────┐
│ «interface»        │  │  «interface»    │  │   «interface»       │
│ ShortCodeGenerator │  │  CacheService   │  │  AnalyticsService   │
└────────────────────┘  └─────────────────┘  └─────────────────────┘
          △                      △                      △
          │                      │                      │
    ┌─────┴─────┬───────┐       │              ┌───────┴────────┐
    │           │       │       │              │                │
┌────────┐ ┌────────┐ ┌────────┐ ┌──────────────┐ ┌─────────────────┐
│Counter │ │Snowflake│ │Base62  │ │RedisCache    │ │KafkaAnalytics   │
│Based   │ │IDGen    │ │HashGen │ │Service       │ │Service          │
└────────┘ └────────┘ └────────┘ └──────────────┘ └─────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│                          URLMapping (Entity)                        │
├─────────────────────────────────────────────────────────────────────┤
│ - id: Long                                                          │
│ - shortCode: String                                                 │
│ - longURL: String                                                   │
│ - userId: Long                                                      │
│ - createdAt: Timestamp                                              │
│ - expiresAt: Timestamp                                              │
│ - isCustomAlias: boolean                                            │
│ - status: URLStatus (ACTIVE, EXPIRED, DELETED)                      │
│ - clickCount: AtomicLong                                            │
├─────────────────────────────────────────────────────────────────────┤
│ + isExpired(): boolean                                              │
│ + incrementClickCount(): void                                       │
│ + toDTO(): URLMappingDTO                                            │
└─────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│                        ClickEvent (Entity)                          │
├─────────────────────────────────────────────────────────────────────┤
│ - eventId: UUID                                                     │
│ - shortCode: String                                                 │
│ - timestamp: long                                                   │
│ - ipAddress: String                                                 │
│ - userAgent: String                                                 │
│ - country: String                                                   │
│ - city: String                                                      │
│ - deviceType: DeviceType (MOBILE, DESKTOP, TABLET)                 │
│ - browser: String                                                   │
│ - referrer: String                                                  │
│ - isBot: boolean                                                    │
├─────────────────────────────────────────────────────────────────────┤
│ + extractMetadata(request: HttpServletRequest): ClickEvent         │
│ + toJSON(): String                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Sequence Diagrams

### 1. Create Short URL Flow

```
Client          Controller      Service         Generator       Cache       DB          Kafka
  │                 │              │               │             │          │            │
  │─POST /shorten──>│              │               │             │          │            │
  │                 │              │               │             │          │            │
  │                 │─validate────>│               │             │          │            │
  │                 │<─────────────│               │             │          │            │
  │                 │              │               │             │          │            │
  │                 │─checkSecurity│               │             │          │            │
  │                 │<─────────────│               │             │          │            │
  │                 │              │               │             │          │            │
  │                 │──checkDuplicate─────────────────────>│     │          │            │
  │                 │<────────────────────────────────────│      │          │            │
  │                 │              │               │             │          │            │
  │                 │─generate─────────────>│      │             │          │            │
  │                 │              │        │──nextId()          │          │            │
  │                 │              │        │──toBase62()        │          │            │
  │                 │              │<───────│      │             │          │            │
  │                 │              │               │             │          │            │
  │                 │──save────────────────────────────────────────────>│   │            │
  │                 │<──────────────────────────────────────────────────│   │            │
  │                 │              │               │             │          │            │
  │                 │──cache───────────────────────────────>│    │          │            │
  │                 │<─────────────────────────────────────│     │          │            │
  │                 │              │               │             │          │            │
  │                 │──publishEvent───────────────────────────────────────────────>│     │
  │                 │<────────────────────────────────────────────────────────────│     │
  │                 │              │               │             │          │            │
  │<──201 Created───│              │               │             │          │            │
  │  {short_url}    │              │               │             │          │            │
```

---

### 2. Redirect Flow (Read Path)

```
Client       CDN        Controller    Service      Cache(L1)   Cache(L2)    DB        Analytics
  │           │             │            │             │           │          │            │
  │─GET /abc123─────>│      │            │             │           │          │            │
  │           │──cache miss─>│           │             │           │          │            │
  │           │      │       │           │             │           │          │            │
  │           │      │───getLongURL─────>│             │           │          │            │
  │           │      │       │           │             │           │          │            │
  │           │      │       │───L1.get──────────>│    │           │          │            │
  │           │      │       │<─────cache hit─────│    │           │          │            │
  │           │      │       │           │             │           │          │            │
  │           │      │       │───trackAsync────────────────────────────────────────────>│  │
  │           │      │       │<─────────────────────────────────────────────────────────│  │
  │           │      │       │           │             │           │          │            │
  │           │      │<──301 redirect────│             │           │          │            │
  │           │<─────│       │           │             │           │          │            │
  │<──301─────│      │       │           │             │           │          │            │
  │           │      │       │           │             │           │          │            │
  │──GET long_url───>│       │           │             │           │          │            │
  │<──200 OK─────────│       │           │             │           │          │            │


Cache Miss Scenario:
  │           │      │───getLongURL─────>│             │           │          │            │
  │           │      │       │───L1.get──────────>│    │           │          │            │
  │           │      │       │<───null────────────│    │           │          │            │
  │           │      │       │           │             │           │          │            │
  │           │      │       │───L2.get(Redis)─────────────────>│  │          │            │
  │           │      │       │<───null──────────────────────────│  │          │            │
  │           │      │       │           │             │           │          │            │
  │           │      │       │───DB.find───────────────────────────────────>│ │            │
  │           │      │       │<───URLMapping────────────────────────────────│ │            │
  │           │      │       │           │             │           │          │            │
  │           │      │       │───L2.set──────────────────────>│   │          │            │
  │           │      │       │───L1.set──────────>│    │           │          │            │
  │           │      │<──301 redirect────│             │           │          │            │
```

---

### 3. Analytics Processing Flow

```
Controller    Kafka       Consumer      Parser      Aggregator    Cassandra   Redis
  │            │            │             │             │             │          │
  │──click─────>│           │             │             │             │          │
  │  event     │           │             │             │             │          │
  │            │───────────>│             │             │             │          │
  │            │           │             │             │             │          │
  │            │           │──parse──────>│             │             │          │
  │            │           │<─metadata────│             │             │          │
  │            │           │             │             │             │          │
  │            │           │──aggregate──────────────>│              │          │
  │            │           │             │            │─batch insert─>│          │
  │            │           │             │            │<──────────────│          │
  │            │           │             │             │             │          │
  │            │           │──increment counter────────────────────────────>│   │
  │            │           │<─────────────────────────────────────────────│   │
  │            │           │             │             │             │          │
```

---

## Implementation

### 📁 Java Implementation

The complete Java implementation with all classes has been moved to a dedicated folder for better organization:

**Location**: `./url-shortener-implementation/`

### 📦 What's Included:

**Core Service Layer:**
- `URLShortenerService.java` - Main service interface (6 operations)
- `URLShortenerServiceImpl.java` - Complete implementation with caching, validation, security
- `CacheService.java` - Multi-layer cache (Caffeine L1 + Redis L2)

**Short Code Generators:**
- `ShortCodeGenerator.java` - Strategy interface
- `SnowflakeShortCodeGenerator.java` - Twitter Snowflake algorithm (170 lines)
- `RedisCounterShortCodeGenerator.java` - Redis atomic counter (95 lines)

**Entity Layer:**
- `URLMapping.java` - JPA entity with indexes
- `URLStatus.java` - Enum (ACTIVE, EXPIRED, DELETED)

**Documentation:**
- `README.md` - Complete documentation (350+ lines)
- `IMPLEMENTATION_SUMMARY.md` - Quick reference
- `PROJECT_STRUCTURE.txt` - Visual structure

### 📊 Implementation Statistics:

- **Total Files**: 9 Java files + 3 documentation files
- **Lines of Code**: ~900 lines
- **Documentation**: 400+ lines
- **Design Patterns**: Strategy, Repository, Service Layer, Builder, Template Method

### 🔗 Quick Access:

```bash
# View implementation structure
cd url-shortener-implementation/
cat PROJECT_STRUCTURE.txt

# Read complete documentation
cat README.md

# View core service
cat src/main/java/com/urlshortener/service/URLShortenerServiceImpl.java

# View short code generators
cat src/main/java/com/urlshortener/generator/SnowflakeShortCodeGenerator.java
```

### 🎯 Key Implementation Highlights:

**1. URL Creation Flow:**
```java
// Rate limiting → Validation → Security → Generation → Save → Cache
ShortURLResponse response = urlService.createShortURL(request);
```

**2. URL Redirect Flow:**
```java
// L1 cache (1ms) → L2 cache (5ms) → Database (50ms)
String longURL = urlService.getLongURL(shortCode);
```

**3. Short Code Generation (Snowflake):**
```java
// 64-bit ID: timestamp + machine ID + sequence
SnowflakeShortCodeGenerator generator = new SnowflakeShortCodeGenerator();
String shortCode = generator.generate(); // "aBc123X"
```

**4. Multi-Layer Caching:**
```java
// L1: Caffeine (10K entries, 5 min TTL) - ~1ms
// L2: Redis (1 hour TTL) - ~5ms
// L3: Database fallback - ~50ms
Optional<String> url = cacheService.getFromLocalCache(shortCode);
```

### 📈 Performance Characteristics:

**Latency:**
- URL Creation: < 200ms (p99)
- URL Redirect: < 100ms (p99)
  - L1 cache hit: ~1ms
  - L2 cache hit: ~5ms
  - Database fallback: ~50ms

**Throughput:**
- Creation: 5,000 req/sec per instance
- Redirect: 500,000 req/sec (with CDN)

**Cache Hit Rates:**
- L1 (Caffeine): 70-80%
- L2 (Redis): 15-20%
- L3 (Database): 5-10%

### 🎯 Design Patterns:

1. **Strategy Pattern** - Multiple short code generators
2. **Repository Pattern** - Data access abstraction
3. **Service Layer** - Business logic separation
4. **Builder Pattern** - Entity/DTO construction
5. **Template Method** - Multi-layer cache hierarchy

---

**For complete Java implementation, see**: [`./url-shortener-implementation/`](./url-shortener-implementation/)

**For quick reference**: [`./url-shortener-implementation/PROJECT_STRUCTURE.txt`](./url-shortener-implementation/PROJECT_STRUCTURE.txt)

---
