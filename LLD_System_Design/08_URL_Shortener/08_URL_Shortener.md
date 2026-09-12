# URL Shortener — Complete LLD Interview Guide

**Interview Duration: 40 min | Difficulty: Medium-Hard | Must-Know: ⭐⭐⭐⭐⭐ | 15-YOE Focus: Hash Collision + Distributed Counter + Analytics**

---

## BIG PICTURE — Architecture

```
 ┌──────────────────────────────────────────────────────────────────┐
 │                    URL SHORTENER SYSTEM                         │
 │                                                                  │
 │  WRITE PATH (shorten)          READ PATH (redirect)             │
 │  ┌───────────────────────┐     ┌────────────────────────────┐  │
 │  │ POST /shorten         │     │ GET /{shortCode}            │  │
 │  │ longUrl: amazon.com/..│     │                            │  │
 │  │         │             │     │  [Cache: Redis]            │  │
 │  │         ▼             │     │   hit? → 301 redirect      │  │
 │  │  [ShortCode Generator]│     │   miss? ↓                  │  │
 │  │  Base62 encode(id)    │     │  [DB lookup by shortCode]  │  │
 │  │  abc123 ← 7 chars     │     │  found? → 301 redirect     │  │
 │  │         │             │     │  not found? → 404          │  │
 │  │         ▼             │     │  async → Analytics          │  │
 │  │  [DB: shortCode→url]  │     └────────────────────────────┘  │
 │  │  [Cache: warm it]     │                                       │
 │  └───────────────────────┘     ANALYTICS                        │
 │                                ┌────────────────────────────┐  │
 │  DISTRIBUTED ID GENERATION     │ click events → Kafka       │  │
 │  ┌───────────────────────┐     │ aggregated: count/geo/time │  │
 │  │  Snowflake ID         │     └────────────────────────────┘  │
 │  │  41-bit timestamp     │                                       │
 │  │  10-bit machineId     │                                       │
 │  │  12-bit sequence      │                                       │
 │  │  → Base62 → 7 chars   │                                       │
 │  └───────────────────────┘                                       │
 └──────────────────────────────────────────────────────────────────┘

 BASE62 ENCODING:
 ┌──────────────────────────────────────────────────────────────────┐
 │  Characters: 0-9, a-z, A-Z  (62 total)                         │
 │  7 characters → 62^7 = 3.5 TRILLION unique URLs                 │
 │                                                                  │
 │  ID = 12345678   →  Base62  →  "dnh75"                         │
 │  dnh75 → DB lookup → https://www.amazon.com/very/long/url/...  │
 │                                                                  │
 │  Why 7 chars?                                                    │
 │  100M URLs/day × 10 years = 365 billion URLs                    │
 │  62^7 = 3.5T > 365B → enough headroom                          │
 └──────────────────────────────────────────────────────────────────┘
```

---

## CONVERSATIONAL SCRIPT

### Phase 1 — Requirements (5 min)

**You:** "Before I design, let me clarify.

Functional:
- Shorten a long URL to a 7-character short code
- Redirect: given short code, redirect to original URL
- Custom alias: user can choose their own short code (e.g., bit.ly/my-brand)
- Expiry: URLs can have an optional expiry date
- Analytics: track clicks, geographic distribution, device type

Non-functional:
- Scale: 100M URLs created per day, 10B redirects per day (100:1 read:write ratio)
- Latency: redirect must be <10ms — this is on the hot path
- Uniqueness: no two long URLs can share the same short code

The design challenge is: the redirect path is read-heavy (10B/day). Every millisecond matters. Let me design for that hot path first.

Also — how do we generate unique 7-char codes in a distributed system without collisions?"

---

### Phase 3 — Implementation

```java
// ─── ShortCode Generator ────────────────────────────────────────
public class Base62Encoder {
    private static final String CHARS =
        "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";
    private static final int BASE = 62;

    public String encode(long id) {
        if (id == 0) return String.valueOf(CHARS.charAt(0));
        StringBuilder sb = new StringBuilder();
        while (id > 0) {
            sb.append(CHARS.charAt((int)(id % BASE)));
            id /= BASE;
        }
        return sb.reverse().toString();
    }

    public long decode(String code) {
        long result = 0;
        for (char c : code.toCharArray()) {
            result = result * BASE + CHARS.indexOf(c);
        }
        return result;
    }
}

// ─── Snowflake ID Generator (distributed-safe unique IDs) ──────
public class SnowflakeIdGenerator {
    // 41 bits timestamp | 10 bits machineId | 12 bits sequence
    private static final long EPOCH         = 1700000000000L; // Nov 2023 custom epoch
    private static final int  MACHINE_BITS  = 10;
    private static final int  SEQUENCE_BITS = 12;
    private static final long MAX_MACHINE   = (1L << MACHINE_BITS) - 1;
    private static final long MAX_SEQUENCE  = (1L << SEQUENCE_BITS) - 1;
    private static final int  MACHINE_SHIFT = SEQUENCE_BITS;
    private static final int  TIME_SHIFT    = MACHINE_BITS + SEQUENCE_BITS;

    private final long machineId;
    private long lastTimestamp = -1;
    private long sequence      = 0;

    public SnowflakeIdGenerator(long machineId) {
        if (machineId > MAX_MACHINE) throw new IllegalArgumentException("Machine ID too large");
        this.machineId = machineId;
    }

    public synchronized long nextId() {
        long now = System.currentTimeMillis() - EPOCH;
        if (now < lastTimestamp) throw new IllegalStateException("Clock moved backwards!");

        if (now == lastTimestamp) {
            sequence = (sequence + 1) & MAX_SEQUENCE;
            if (sequence == 0) {
                // Sequence exhausted: wait for next millisecond
                while (now <= lastTimestamp) now = System.currentTimeMillis() - EPOCH;
            }
        } else {
            sequence = 0;
        }
        lastTimestamp = now;
        return (now << TIME_SHIFT) | (machineId << MACHINE_SHIFT) | sequence;
    }
}

// ─── URL Entity ──────────────────────────────────────────────────
public class ShortUrl {
    private final String    shortCode;
    private final String    longUrl;
    private final String    userId;
    private final LocalDateTime createdAt;
    private final LocalDateTime expiresAt;   // null = never expires
    private long            clickCount;

    public ShortUrl(String shortCode, String longUrl, String userId, LocalDateTime expiresAt) {
        this.shortCode = shortCode;
        this.longUrl   = longUrl;
        this.userId    = userId;
        this.createdAt = LocalDateTime.now();
        this.expiresAt = expiresAt;
        this.clickCount = 0;
    }

    public boolean isExpired() {
        return expiresAt != null && LocalDateTime.now().isAfter(expiresAt);
    }

    public String getShortCode() { return shortCode; }
    public String getLongUrl()   { return longUrl; }
    public LocalDateTime getExpiresAt() { return expiresAt; }
}

// ─── URL Shortener Service ───────────────────────────────────────
public class UrlShortenerService {
    private final SnowflakeIdGenerator idGenerator;
    private final Base62Encoder        encoder;
    private final UrlRepository        urlRepository;   // DB abstraction
    private final CacheService         cache;           // Redis abstraction
    private final EventPublisher       analyticsPublisher;

    // Rate limiting per user (prevent abuse)
    private final Map<String, AtomicInteger> rateLimiter = new ConcurrentHashMap<>();

    public UrlShortenerService(long machineId, UrlRepository repo,
                                CacheService cache, EventPublisher publisher) {
        this.idGenerator       = new SnowflakeIdGenerator(machineId);
        this.encoder           = new Base62Encoder();
        this.urlRepository     = repo;
        this.cache             = cache;
        this.analyticsPublisher = publisher;
    }

    // ─── Shorten ────────────────────────────────────────────────
    public String shorten(String longUrl, String userId, String customAlias,
                           LocalDateTime expiresAt) {
        validateUrl(longUrl);

        // Custom alias path
        if (customAlias != null && !customAlias.isBlank()) {
            return createWithCustomAlias(customAlias, longUrl, userId, expiresAt);
        }

        // Check if same URL was already shortened by this user → return existing
        Optional<String> existing = urlRepository.findByLongUrlAndUser(longUrl, userId);
        if (existing.isPresent()) return existing.get();

        // Generate new short code
        long id = idGenerator.nextId();
        String shortCode = encoder.encode(id);
        // Pad to 7 chars if shorter
        while (shortCode.length() < 7) shortCode = "0" + shortCode;

        ShortUrl shortUrl = new ShortUrl(shortCode, longUrl, userId, expiresAt);
        urlRepository.save(shortUrl);
        cache.set("url:" + shortCode, longUrl, 24 * 60 * 60); // cache 24h
        return shortCode;
    }

    private String createWithCustomAlias(String alias, String longUrl,
                                          String userId, LocalDateTime expiresAt) {
        if (!alias.matches("[a-zA-Z0-9_-]{3,20}"))
            throw new IllegalArgumentException("Alias must be 3-20 alphanumeric chars");

        if (urlRepository.existsByShortCode(alias))
            throw new ConflictException("Alias already taken: " + alias);

        ShortUrl shortUrl = new ShortUrl(alias, longUrl, userId, expiresAt);
        urlRepository.save(shortUrl);
        cache.set("url:" + alias, longUrl, 24 * 60 * 60);
        return alias;
    }

    // ─── Redirect ────────────────────────────────────────────────
    public String resolve(String shortCode, String ipAddress, String userAgent) {
        // 1. Cache check (hot path — must be <1ms)
        String cachedUrl = cache.get("url:" + shortCode);
        if (cachedUrl != null) {
            if ("EXPIRED".equals(cachedUrl)) throw new UrlExpiredException(shortCode);
            publishClickEvent(shortCode, ipAddress, userAgent); // async, non-blocking
            return cachedUrl;
        }

        // 2. DB lookup (cache miss)
        ShortUrl shortUrl = urlRepository.findByShortCode(shortCode)
            .orElseThrow(() -> new NotFoundException("Short code not found: " + shortCode));

        if (shortUrl.isExpired()) {
            cache.set("url:" + shortCode, "EXPIRED", 60); // cache expiry for 60s
            throw new UrlExpiredException(shortCode);
        }

        // 3. Warm cache for next request
        cache.set("url:" + shortCode, shortUrl.getLongUrl(), 24 * 60 * 60);
        publishClickEvent(shortCode, ipAddress, userAgent);
        return shortUrl.getLongUrl();
    }

    private void publishClickEvent(String shortCode, String ip, String ua) {
        // Non-blocking — don't slow down redirect for analytics
        CompletableFuture.runAsync(() ->
            analyticsPublisher.publish("clicks", new ClickEvent(shortCode, ip, ua,
                Instant.now()))
        );
    }

    private void validateUrl(String url) {
        try { new URL(url).toURI(); }
        catch (Exception e) { throw new IllegalArgumentException("Invalid URL: " + url); }
    }
}
```

---

## Component Choices

```
COMPONENT             CHOICE                   WHY
──────────────────────────────────────────────────────────────────────
ID generation         Snowflake                Globally unique without
                                               central coordination.
                                               No DB auto-increment needed.
                                               41-bit timestamp: ~69 years.
                                               vs UUID: too long to encode
                                               in 7 chars legibly.
                                               vs DB sequence: bottleneck.

Encoding              Base62                   URL-safe characters only.
                                               No +/= like Base64 (breaks URLs).
                                               62^7 = 3.5T codes (enough for
                                               10 years at 100M URLs/day).

Redirect caching      Redis, TTL=24h           Redirect is the hot path.
                                               10B reads/day = 115k/sec.
                                               Without cache: DB takes this.
                                               Redis handles millions of ops/sec.
                                               Cache hit = <1ms, DB = ~5ms.

Analytics             Async + Kafka            Don't block redirect for analytics.
                                               Fire-and-forget click event.
                                               Kafka consumer aggregates async.
                                               Real-time dashboard via Flink.

Redirect status code  301 vs 302              301 = Permanent (browser caches)
                                               → 0 server requests on repeat visits
                                               → BUT analytics breaks (browser
                                                  bypasses server entirely!)
                                               302 = Temporary (no browser cache)
                                               → Every click hits our server
                                               → Analytics accurate
                                               Production: 302 if analytics needed,
                                               301 if CDN offload is priority.
```

---

## Senior Trap Questions

**Q1: "What's the difference between 301 and 302 redirect? When do you use each?"**
```
301 Moved Permanently:
  Browser caches this redirect.
  Second visit: browser goes DIRECTLY to destination. Your server never sees it.
  Pros: reduced load on your server.
  Cons: analytics broken — you can't count repeat clicks.
        Can't update destination URL (browser ignores your new 301).

302 Found (Temporary):
  Browser does NOT cache.
  Every click: browser calls your server → you log the click → you redirect.
  Pros: accurate analytics, can change destination anytime.
  Cons: every click = server load.

Bit.ly uses 301 for non-analytics URLs, 302 for analytics-tracked URLs.
Production default: 302 unless you explicitly want to offload traffic.
```

**Q2: "Same long URL submitted by 1000 different users. Do they get the same short code or different?"**
```
Two design choices:

Option A: Same long URL → same short code (deduplication)
  Check DB: SELECT shortCode WHERE longUrl = ?
  If exists: return existing shortCode.
  PROBLEM: user A's URL expiry would affect user B's.
           Privacy: user A can see that their URL was already shortened.
           Index on longUrl column needed (long URL can be 2000 chars → big index).

Option B: Each user gets their own short code (no deduplication)
  Simple. Isolation between users.
  More codes generated, but 3.5T capacity handles it.
  
Production: Option B for general users (isolation + simplicity).
Optional dedup within SAME user's account (avoid duplicate shortenings).
```

**Q3: "How do you handle a malicious URL (phishing, malware)?"**
```
Multi-layer:
  1. At creation: check against Google Safe Browsing API.
     If flagged: reject the URL creation.
  2. Async background scanner: Malware detection service scans all new URLs.
     If later flagged: mark URL as SUSPENDED in DB.
     Redirect returns: 451 Unavailable For Legal Reasons.
  3. Cache: if URL is suspended, cache "SUSPENDED" status.
     Users see: "This link has been disabled for safety reasons."
  4. Abuse reporting: users can flag URLs → human review queue.
```

---

## Failure Modes

```
SCENARIO              WHAT HAPPENS             FIX
────────────────────────────────────────────────────────────────────
Redis cache down      All redirects go to DB   DB must handle the fallback.
                                               Circuit breaker: if Redis
                                               unavailable, bypass cache,
                                               hit DB directly (slower but
                                               functional). Alert + auto-heal.

ID generator clock    Snowflake throws          Detect on startup.
moves backward        IllegalStateException     NTP sync + machine clock
                                               drift alerting. Fall back to
                                               UUID-based generation temporarily.

DB write fails after  Short code returned       Use DB transaction: save
cache warm            to user but not          URL to DB FIRST, then warm
                      in DB                    cache. Never warm cache on
                                               a failed DB write.

Thundering herd on    Cache expires for         Jitter on cache TTL.
viral URL             viral URL →              Popular URL: refresh-ahead
                      everyone hits DB          before expiry.
```

---

## Interview Cheat Sheet

> "URL shortener is a read-heavy system — 100:1 read-to-write ratio — so optimize the redirect hot path first. Redis cache keyed by short code with 24h TTL handles almost all redirects at <1ms. For ID generation: Snowflake algorithm gives globally unique IDs without a central counter bottleneck — timestamp + machineId + sequence → encode to Base62 → 7 characters. 62^7 = 3.5 trillion codes, which is enough for 100M URLs/day for 10 years. The 301 vs 302 trap: 301 means browsers cache the redirect and stop hitting your server — analytics breaks because you never see repeat clicks; use 302 for analytics-tracked URLs. Custom aliases use a separate code path with uniqueness check. Analytics are fire-and-forget: publish click event to Kafka async so the redirect isn't blocked waiting for analytics writes."
