Pre-Interview Memory Refresher
18 min revision
Updated 2026-01-26
Bonus: beyond the video + interview questions
URL Shortener (Bit.ly / TinyURL)

"Long URL → Server generates unique ID (Zookeeper counter/Snowflake) → Base62 encode → Store mapping (DB + Redis cache) → Redirect requests via short URL with analytics tracking"

1. Functional Requirements

Feature 1: Create a short url from a long url (e.g., https://www.facebook.com/anindya.s.dasgupta/ → http://bit.ly/4kycpo)
Feature 2: Optional: support custom url (user chooses short code like 'mylink' instead of random)
Feature 3: Optional: support expiration date (short URL expires after 30 days, 1 year, etc.)
Feature 4: User should get redirected to the original url from short url (301/302 redirect)
Feature 5: Optional: Track analytics (click count, user metadata, timestamps for each redirect)
2. Non-Functional Requirements

Scale & Latency
Scale — 100M DAU / 1B url - massive read traffic (billions of redirects daily)
Latency — Low latency (url-creating, on redirect ~200ms) - redirect must be fast (<100ms)
Consistency & Availability
Short url uniqueness — Short url should be unique (no collisions, two users can't get same short URL)
CAP Theorem — Availability >> Consistency (eventual consistency acceptable for analytics)
3. Core Entity (from image)

Entity 1: short_url - The shortened URL code (e.g., '4kycpo', '9i91c0')
Entity 2: long_url - Original full URL
Entity 3: user - User who created the short URL (optional, for tracking user's URLs)
Entity 4: From image shows: User metadata (user info), URL (shortURL, longURL, expirationDate, customURL)
4. API Designing (from image)

API Creation (from image shows POST /s/url ->short-url)
POST /s/url ->short-url — Create short URL from long URL with optional custom alias and expiration
GET /s/url/{shortURL} ->longURL — Get long URL for given short URL (for redirect or analytics)
Request body example — {longURL: 'https://www.facebook.com/...', customURL: 'myprofile' (optional), expirationDate: '2026-12-31' (optional)}
Response example — {shortURL: 'http://bit.ly/4kycpo', longURL: 'https://www.facebook.com/...', createdAt: '2026-01-26', expiresAt: '2026-12-31'}
5. High Level Design (from image)

From image shows: Client → redirect(short) / longURL → Server (generate the short url) → Database (User metadata, URL shortURL/longURL/expirationDate/customURL)
Client: Web browser, mobile app, API client sending requests
Server: Generates short URL using counter/Snowflake ID, handles redirects, encryption/decryption
Database: Stores URL mappings (short → long), user metadata, expiration dates, custom URLs
6. Deep Dive Design (Low Level - from image)

Step 1: URL Shortening - ID Generation (from image shows multiple approaches)
From image: Shows three approaches - Counter (Zookeeper), Snowflake, and Encryption Logic
Challenge: Generate unique short code (6-7 characters) for each long URL, must be collision-free
Approach 1 - Counter with Zookeeper (from image shows 'counter' with Zookeeper): Use distributed counter to generate sequential IDs, Base62 encode to short string. Flow: (1) User submits: POST /s/url with {longURL: 'https://www.facebook.com/anindya.s.dasgupta/'}, (2) Server requests counter: Zookeeper atomic increment: counter++ (e.g., counter = 3748547), (3) Base62 encode: encode(3748547) → '9i91c0' (6 chars), (4) Store mapping: INSERT INTO urls (short_url, long_url, created_at) VALUES ('9i91c0', 'https://www.facebook.com/...', now()), (5) Cache: SET url:9i91c0 {longURL, metadata} EX 86400 (24 hour TTL), (6) Response: {shortURL: 'http://bit.ly/9i91c0', longURL: '...'}
From image note: 'Counter' with 'Zms-3ms' latency, Redis shown for caching counter values
Base62 encoding: Characters: [0-9a-zA-Z] = 62 chars (0-9: 10, a-z: 26, A-Z: 26), Algorithm: num = 3748547; result = ''; while (num > 0) { result = chars[num % 62] + result; num = Math.floor(num / 62); }, Example: 3748547 → '9i91c0'. Length: 62^6 = 56 billion unique URLs (6 chars), 62^7 = 3.5 trillion (7 chars)
From image: 'Zookeeper: Zookeeper is a distributed, open-source coordination service for distributed applications, providing centralized services for configuration management, naming, synchronization, and group services, making it easy to build large clusters. Used for: maintaining configuration information, naming, providing distributed synchronization, and providing group service etc'
Zookeeper counter implementation: (1) Zookeeper node: /counters/url_counter with value = 0, (2) Atomic increment: zk.setData('/counters/url_counter', currentValue + 1), guaranteed atomic across all servers, (3) Multiple servers: All encryption servers read from same Zookeeper counter → no collisions, (4) High availability: Zookeeper cluster (3-5 nodes), if one fails → others maintain counter state
From image shows: Multiple encryption servers (round robin load balancing) → Zookeeper counter → ensures same counter value never reused
Step 2: Approach 2 - Snowflake ID (from image shows Snowflake with timestamp, workerID)
From image: 'Snowflake' with 'workerID: 123, workerID: 234, workerID: 345' and 'timestamp' component
Snowflake ID structure (64-bit): [1 bit unused][41 bits timestamp][10 bits workerID][12 bits sequence], Total: 64 bits = can represent 2^64 unique IDs
Components: (1) Timestamp (41 bits): Milliseconds since custom epoch (e.g., Jan 1, 2020), 41 bits → 2^41 ms ≈ 69 years, (2) WorkerID (10 bits): Unique ID per server (0-1023), 10 bits → 2^10 = 1024 workers, (3) Sequence (12 bits): Counter within same millisecond per worker, 12 bits → 2^12 = 4096 IDs per ms per worker
Example generation: (1) Current time: Jan 26, 2026 10:30:45.123 → ms since epoch: 189432045123, (2) WorkerID: Server 123, (3) Sequence: 1st ID this millisecond → 0, (4) Combine: ID = (189432045123 << 22) | (123 << 12) | 0 = 792345678901234567 (64-bit number), (5) Base62 encode: encode(792345678901234567) → 'aBc123XyZ' (10 chars)
From image shows: Snowflake ID formula with bit positions: 2^41 / 365 / 24 / 3600 / 1000 = 69.73 Years, 41 bit timestamp
Advantages: (1) No coordination needed (unlike Zookeeper counter), each worker generates IDs independently, (2) Time-ordered: IDs increase monotonically (newer URLs have higher IDs), (3) High throughput: 4096 IDs/ms/worker × 1024 workers = 4M IDs/sec, (4) Decentralized: Workers don't communicate, no single point of failure
Disadvantages: (1) Longer short URLs: 64-bit number → 10-11 chars in Base62 (vs 6-7 for counter), workaround: Use only lower 42 bits (still 69 years + 1024 workers + 1 sequence) → 7-8 chars, (2) Clock dependency: Requires synchronized clocks (NTP), clock drift can cause collisions
Step 3: Approach 3 - Encryption/Hash Logic (from image shows 'sha1(longUrl) -> (shortURL, 6, 7)')
From image: 'Encryption Logic: sha1(longUrl) -> (shortURL, 6, 7) -> response' with note about encryption/decryption overhead
Hash-based approach: Hash long URL → extract 6-7 characters → use as short URL
Flow: (1) User submits: POST /s/url with {longURL: 'https://www.facebook.com/anindya.s.dasgupta/'}, (2) Hash URL: hash = SHA1(longURL) = 'd3e8f9a2b1c4e5f6a7b8c9d0e1f2a3b4c5d6e7f8' (40 hex chars), (3) Extract substring: shortCode = hash.substring(0, 7) = 'd3e8f9a' (7 chars), (4) Check collision: SELECT COUNT(*) FROM urls WHERE short_url='d3e8f9a', if exists → try hash.substring(7, 14), hash.substring(14, 21), etc. (multiple attempts), if all 5 attempts collide → append timestamp: hash(longURL + timestamp), (5) Store: INSERT INTO urls (short_url, long_url), (6) Response: {shortURL: 'http://bit.ly/d3e8f9a'}
From image note: 'Server - encryption (20%), decryption (80%)' - shows read-heavy workload
Collision handling: (1) Probability: SHA1 output space = 2^160, 7 chars from hash = 16^7 possible values, with 1M URLs → collision probability ≈ (1M^2) / (2 × 16^7) ≈ 0.000002% (extremely low), (2) If collision detected: Try next 7 characters from hash, or rehash with salt: hash(longURL + random_salt), (3) Max retries: 5 attempts, if all fail → fall back to counter-based ID
Advantages: (1) No external dependency (no Zookeeper, no coordination), (2) Same long URL → same hash → same short URL (deterministic, deduplication), if user creates same long URL twice → returns existing short URL, (3) Stateless: Any server can generate short URL without querying database first
Disadvantages: (1) Collision risk: Need retry logic, more complex than counter, (2) Cannot guarantee short URL length (hash extraction might need 8-9 chars after retries), (3) No time-ordering: Random distribution, can't query 'recent URLs' easily
Step 4: URL Redirect Flow (from image shows redirect path)
From image: Client → redirect(short) / longURL → Server → generatedLongURL → Database
User clicks short URL: GET http://bit.ly/9i91c0 (browser request)
Server redirect flow: (1) Extract short code: '9i91c0' from URL path, (2) Check Redis cache: GET url:9i91c0 → {longURL: 'https://www.facebook.com/anindya.s.dasgupta/', expiresAt: '2027-01-26'}, if cache hit (90% of requests) → skip DB query, (3) If cache miss: Query DB: SELECT long_url, expires_at FROM urls WHERE short_url='9i91c0', if not found → return 404 'Short URL not found', if found but expired (expires_at < now()) → return 410 'Link expired', if valid → cache result: SET url:9i91c0 {longURL, expiresAt} EX 86400, (4) Return redirect: HTTP 301 Moved Permanently with Location: https://www.facebook.com/anindya.s.dasgupta/, (5) Browser automatically redirects to long URL
From image note: 'encrypt: 1ms' for encryption, '5ms' for server to DB latency, total '=16ms + 16ms' round trip
301 vs 302 redirect: (1) 301 Permanent: Browser caches redirect, future clicks go directly to long URL (no server request), Pros: Reduces server load (cached redirects), Cons: Can't track analytics after first click (browser bypasses server), (2) 302 Temporary: Browser doesn't cache, every click goes through server, Pros: Can track every click for analytics, Cons: Higher server load, (3) Bit.ly uses 302 for analytics tracking
Performance: (1) Cache hit: <10ms (Redis lookup + redirect response), (2) Cache miss: ~50ms (DB query + Redis write + redirect), (3) 90% cache hit rate → avg latency ~15ms
Step 5: Custom Short URLs (from image shows customURL field)
From image: Database schema shows 'customURL' as optional field
User wants custom alias: POST /s/url with {longURL: 'https://myportfolio.com', customURL: 'mywork'}
Server validates custom URL: (1) Check length: 3-20 characters (enforce minimum to prevent single-char URLs like 'a'), (2) Check allowed chars: [a-zA-Z0-9-_] only (no special chars, no spaces), (3) Check profanity: Filter against blacklist (e.g., 'badword', 'spam'), (4) Check availability: SELECT COUNT(*) FROM urls WHERE short_url='mywork', if exists → return 409 'Custom URL already taken', (5) Reserve: INSERT INTO urls (short_url: 'mywork', long_url: 'https://myportfolio.com', is_custom: true)
Response: {shortURL: 'http://bit.ly/mywork', longURL: 'https://myportfolio.com'}
Collision with auto-generated: (1) Problem: Counter generates 'abc123', user later requests custom 'abc123' → collision, (2) Solution: Separate namespaces, Partition ID space: Counter uses range [0 - 100B], custom URLs are strings (can include hyphens, underscores not in Base62), OR prefix custom URLs: /c/mywork vs /a/abc123 (auto), (3) Bit.ly approach: No prefix, custom URLs checked first before auto-generation (custom has priority)
Step 6: Expiration & Cleanup (from image shows expirationDate)
From image: Database schema includes 'expirationDate' field
User creates URL with expiration: POST /s/url with {longURL: '...', expirationDate: '2026-12-31'}
Store: INSERT INTO urls (short_url, long_url, expires_at: '2026-12-31 23:59:59')
Redirect check: (1) User clicks short URL after expiration (Jan 1, 2027), (2) Server queries: SELECT long_url, expires_at FROM urls WHERE short_url='...', (3) Check: if expires_at < NOW() → return 410 Gone with message 'This link has expired', else redirect normally
From image shows: 'cron' job for cleanup
Cleanup job (cron): (1) Runs daily at 2 AM, (2) Query: SELECT short_url FROM urls WHERE expires_at < NOW() - INTERVAL '30 days' AND expires_at IS NOT NULL (find expired URLs older than 30 days), (3) Delete: DELETE FROM urls WHERE short_url IN (...) (batch delete 10K at a time), (4) Invalidate cache: DEL url:{short_url} for each deleted URL, (5) Reclaim IDs: Expired short URLs can be reused (counter doesn't go backward but hash space is reusable)
TTL optimization: (1) Default expiration: If user doesn't specify → expires_at = NULL (never expires), (2) Common presets: 1 day, 7 days, 30 days, 1 year, never, (3) Storage savings: Delete expired URLs frees DB space (with 1B URLs × 1KB = 1TB, deleting 10% = 100GB saved)
Step 7: Analytics Tracking (from image shows metadata)
From image: Database stores 'User metadata' for analytics
Track redirect events: (1) User clicks: GET http://bit.ly/9i91c0, (2) Server logs event: INSERT INTO analytics (short_url, timestamp, ip_address, user_agent, referrer, country, device_type), Example: {short_url: '9i91c0', timestamp: '2026-01-26 10:30:45', ip: '203.0.113.5', user_agent: 'Mozilla/5.0...', referrer: 'https://twitter.com', country: 'US' (from IP geolocation), device_type: 'mobile' (from user agent)}, (3) Async insert: Don't block redirect, publish to Kafka → Analytics Consumer inserts to DB
Kafka event: {event_type: 'url_click', short_url: '9i91c0', timestamp, metadata: {ip, user_agent, referrer}}
Analytics aggregation: (1) Real-time: Redis counters: INCR click_count:9i91c0 (total clicks), HINCRBY click_count:9i91c0:daily {date} 1 (clicks per day), PFADD unique_users:9i91c0 {ip} (HyperLogLog for unique visitors), (2) Batch: Hourly job aggregates: SELECT short_url, COUNT(*) as clicks, COUNT(DISTINCT ip) as unique_users FROM analytics WHERE timestamp >= NOW() - INTERVAL '1 hour' GROUP BY short_url, UPDATE urls SET click_count = click_count + {clicks}
Dashboard: GET /api/v1/analytics/{shortURL} returns: {totalClicks: 15234, uniqueVisitors: 8765, clicksByDate: {'2026-01-25': 543, '2026-01-26': 432}, topReferrers: [{'twitter.com': 4532}, {'facebook.com': 2341}], topCountries: [{'US': 6543}, {'IN': 3421}], deviceBreakdown: {'mobile': 60%, 'desktop': 35%, 'tablet': 5%}}
Performance: (1) Async logging: Redirect responds in <10ms, analytics inserted later (doesn't block user), (2) Sampling: For very popular URLs (>1M clicks/day), sample 10% of clicks (reduces storage, maintains accuracy)
Step 8: Caching Strategy (from image shows Redis with 2ms latency)
From image: Redis shown with '2ms' latency for caching layer
Cache design: (1) Key: url:{short_url} e.g., url:9i91c0, (2) Value: JSON {longURL, expiresAt, isCustom}, (3) TTL: 24 hours (86400 sec), popular URLs stay cached, unpopular expire and free memory
Cache flow: (1) Redirect request: GET url:9i91c0 from Redis, if hit → return longURL (<1ms), if miss → query DB → cache result: SET url:9i91c0 {longURL, expiresAt} EX 86400 → return longURL (~50ms first request)
Cache hit rate: (1) Target: 90%+ hit rate, (2) Popular URLs: Clicked thousands of times/day → always cached (TTL refreshed on each access), (3) Unpopular URLs: Clicked once a month → may not be cached (acceptable, DB can handle 10% traffic)
Write-through cache: (1) URL creation: INSERT INTO urls (...) → immediately SET url:{short_url} (...) EX 86400 (cache on creation), (2) Ensures first redirect is fast (no cache miss)
Cache invalidation: (1) URL updated: User changes longURL or expiration → UPDATE urls → DEL url:{short_url} (invalidate cache, next request rebuilds), (2) URL deleted: DELETE FROM urls → DEL url:{short_url}, (3) Expiration: Cron deletes expired URLs → DEL url:{short_url}
Bloom filter optimization: (1) Problem: Cache miss for non-existent short URL → DB query returns nothing → wasted query, (2) Solution: Bloom filter (5MB for 10M URLs, 1% false positive rate), (3) Check Bloom filter before DB: if bf.contains('xyz123') == false → return 404 immediately (no DB query), if bf.contains('xyz123') == true → might exist, query DB, (4) Update Bloom filter: On URL creation → bf.add(short_url)
Step 9: Load Balancing & High Availability (from image shows load balancer)
From image: Client → Load Balancer (round robin) → Multiple Encryption Servers
Load balancer: (1) Round robin: Distributes requests evenly across servers (Server 1 → Server 2 → Server 3 → Server 1), (2) Health checks: Ping each server every 10 sec, if server unresponsive → remove from pool, (3) Sticky sessions: Not needed (stateless servers, any server can handle any request)
Server scaling: (1) URL creation: CPU-bound (Base62 encoding, DB write), 10 servers × 1000 req/sec = 10K URL creations/sec, (2) Redirects: I/O-bound (Redis/DB read), 100 servers × 10K req/sec = 1M redirects/sec, (3) Auto-scale: If CPU > 80% → add servers, if CPU < 20% → remove servers
Database replication: (1) Master-slave: Master handles writes (URL creation), 5 slaves handle reads (redirects), (2) Read/write split: URL creation → master, redirects → slaves (round robin across slaves), (3) Replication lag: <1 sec acceptable (user creates URL → might not redirect immediately for 1 sec → eventually consistent)
Zookeeper cluster: (1) 5 nodes: Quorum = 3 (majority), can tolerate 2 node failures, (2) Leader election: One node is leader (handles counter increments), if leader fails → new leader elected (<10 sec), (3) Counter persistence: Zookeeper persists counter to disk, survives cluster restart
Step 10: Security & Abuse Prevention
Rate limiting: (1) Per IP: 100 URL creations/hour (prevent spam), Redis: INCR rate_limit:{ip} EX 3600, if count > 100 → return 429 'Too many requests', (2) Per user: Authenticated users get 1000/hour (higher limit), (3) Per short URL: 10K clicks/min (prevent DDoS via popular short URL)
Malicious URL detection: (1) Blacklist check: Query Google Safe Browsing API: POST https://safebrowsing.googleapis.com/v4/threatMatches:find with {url: longURL}, if response.matches.length > 0 → return 400 'Malicious URL detected', (2) Phishing patterns: Regex check for common phishing domains (e.g., 'paypa1.com' instead of 'paypal.com'), (3) User reports: If URL reported 10 times → flag for manual review, if confirmed malicious → DELETE short URL
CAPTCHA: (1) Trigger: If IP creates 10 URLs in 1 minute → require CAPTCHA, (2) reCAPTCHA v3: Invisible, scores user 0-1 (bot likelihood), if score < 0.5 → challenge with image CAPTCHA, (3) Prevents: Bots generating millions of short URLs (spam, abuse)
URL validation: (1) Length: longURL < 2048 chars (browser limit), (2) Protocol: Must start with http:// or https:// (no javascript:, data:, file: schemes → XSS prevention), (3) Domain: Valid DNS (resolve domain name, if fails → invalid URL)
Authentication: (1) Optional: Allow anonymous URL creation (like Bit.ly), (2) Authenticated users: OAuth login (Google, GitHub), benefits: (a) Track user's URLs (GET /api/v1/users/{userId}/urls), (b) Edit/delete URLs, (c) Private URLs (only creator can access analytics), (3) API keys: For programmatic access, rate limit per API key (10K req/day)
Step 11: Database Schema Design
From image: Shows 'User metadata', 'URL (shortURL, longURL, expirationDate, customURL)'
URLs table: CREATE TABLE urls (short_url varchar(10) PRIMARY KEY, long_url text NOT NULL, user_id uuid (nullable, for authenticated users), created_at timestamptz NOT NULL, expires_at timestamptz (nullable), is_custom boolean DEFAULT false, click_count bigint DEFAULT 0, INDEX on (user_id, created_at) for user's URL listing, INDEX on (expires_at) for cleanup job);
Analytics table: CREATE TABLE analytics (id bigserial PRIMARY KEY, short_url varchar(10) NOT NULL, clicked_at timestamptz NOT NULL, ip_address inet, user_agent text, referrer text, country varchar(2), device_type varchar(20), INDEX on (short_url, clicked_at) for time-series queries, PARTITION BY RANGE (clicked_at) (analytics_2026_01, analytics_2026_02) for performance);
Users table (optional): CREATE TABLE users (user_id uuid PRIMARY KEY, email varchar(255) UNIQUE, created_at timestamptz, quota_used int DEFAULT 0, quota_limit int DEFAULT 1000);
Sharding strategy: (1) Shard URLs by short_url hash: hash('9i91c0') mod 10 → shard 3, (2) 10 shards: Each handles 100M URLs (total 1B URLs), (3) Cross-shard queries: User's URLs (user_id) → query all shards, aggregate results (acceptable for small result set)
Storage estimation: (1) 1 URL: short_url (10 bytes) + long_url (500 bytes avg) + metadata (100 bytes) ≈ 610 bytes, (2) 1B URLs: 610 bytes × 1B = 610 GB (~600 GB), (3) With indexes (30% overhead): 600 GB × 1.3 = 780 GB, (4) Analytics: 1B clicks/day × 200 bytes = 200 GB/day, with 90 day retention = 18 TB (partition by month, archive old data to S3)
Step 12: Encoding Comparison (Base62 vs Base64 vs Hex)
Base62: (1) Characters: [0-9a-zA-Z] = 62 chars, (2) Example: encode(3748547) → '9i91c0' (6 chars), (3) Pros: URL-safe (no special chars), human-readable (no confusing chars like 0 vs O), short output (62^6 = 56B URLs), (4) Cons: Case-sensitive (9i91c0 ≠ 9I91C0, users may mistype)
Base64: (1) Characters: [0-9a-zA-Z+/] = 64 chars, (2) Example: encode(3748547) → '9i91c+' (6 chars), (3) Pros: Slightly more compact than Base62, standard encoding (libraries available), (4) Cons: Not URL-safe (+ and / need escaping: %2B, %2F → makes URL longer), less human-readable
Hexadecimal (Base16): (1) Characters: [0-9a-f] = 16 chars, (2) Example: encode(3748547) → '392b23' (6 chars for small numbers, but 3748547 in hex = '392b23' also 6 chars), (3) Pros: Case-insensitive (392b23 = 392B23), very simple, (4) Cons: Much longer for large numbers (16^6 = 16M URLs vs 62^6 = 56B), need 8-10 chars for 1B URLs
Why Base62 chosen: (1) Optimal balance: URL-safe + short + readable, (2) 62^7 = 3.5 trillion URLs (enough for decades), (3) Bit.ly, TinyURL, Google (goo.gl) all use Base62, (4) Case-sensitive caveat: Use lowercase-only variant [0-9a-z] (36 chars) for case-insensitive systems (36^7 = 78B URLs, still enough)
Step 13: Monitoring & Debugging
Metrics: (1) URL creation rate: URLs created/sec (track spikes, capacity planning), (2) Redirect latency: p50, p95, p99 latency for redirects, (3) Cache hit rate: Redis hit rate (should be >90%), (4) Error rate: 404 rate (broken links), 410 rate (expired links), 5xx errors, (5) Popular URLs: Top 100 URLs by click count (identify viral links)
Dashboards: (1) Real-time: Current requests/sec, active connections, server health, (2) Historical: Daily URL creation trend, redirect volume over time, (3) Alerts: If error rate > 1% → alert, if cache hit rate < 80% → alert (Redis issue?), if Zookeeper down → alert (critical, counter unavailable)
Logging: (1) Access logs: Timestamp, IP, short_url, status_code, latency, (2) Error logs: Stack traces for 5xx errors, invalid URL requests, (3) Audit logs: URL creations (who, when, what), deletions, updates, (4) Retention: Access logs 7 days (high volume), error logs 30 days, audit logs 1 year
Debugging: (1) Short URL not working: Check DB: SELECT * FROM urls WHERE short_url='...', check Redis: GET url:..., check expiration: expires_at < now()?, (2) Redirect slow: Check cache hit: Did request hit Redis or DB?, check DB replication lag, check network latency, (3) Counter collision: Check Zookeeper: Is counter value correct?, check for duplicate short_url in DB (should be impossible with unique constraint)
Testing: (1) Load test: Simulate 100K req/sec redirects (JMeter, Locust), measure latency, identify bottlenecks, (2) Chaos engineering: Kill random server, kill Zookeeper leader, partition network → system should recover gracefully, (3) Edge cases: Expired URL redirect, custom URL collision, very long URL (2KB), malicious URL detection
7. Database Schema Details (from image)

URLs Table (Primary storage)
short_url — varchar(10) PRIMARY KEY - Unique short code (e.g., '9i91c0', 'mywork')
long_url — text NOT NULL - Original URL (up to 2048 chars)
user_id — uuid (nullable) - FK to Users table for authenticated users
created_at — timestamptz NOT NULL - When short URL was created
expires_at — timestamptz (nullable) - Expiration date, NULL = never expires
is_custom — boolean DEFAULT false - True if user chose custom alias
click_count — bigint DEFAULT 0 - Total clicks (aggregated from analytics)
Indexes — INDEX on (user_id, created_at) for user's URLs, INDEX on (expires_at) for cleanup job
Sharding — Shard by hash(short_url) mod N for horizontal scaling
Analytics Table (Click tracking)
id — bigserial PRIMARY KEY
short_url — varchar(10) NOT NULL - FK to URLs table
clicked_at — timestamptz NOT NULL - When redirect happened
ip_address — inet - User IP (for geolocation, unique visitor count)
user_agent — text - Browser/device info
referrer — text - Where user came from (twitter.com, facebook.com)
country — varchar(2) - Country code from IP geolocation (US, IN, UK)
device_type — varchar(20) - mobile, desktop, tablet, bot
Indexes — INDEX on (short_url, clicked_at) for time-series queries
Partitioning — PARTITION BY RANGE (clicked_at) - Monthly partitions (analytics_2026_01, analytics_2026_02)
Users Table (Optional - for authenticated users)
user_id — uuid PRIMARY KEY
email — varchar(255) UNIQUE - User email
oauth_provider — varchar(50) - google, github, twitter
created_at — timestamptz
quota_used — int DEFAULT 0 - URLs created this month
quota_limit — int DEFAULT 1000 - Monthly creation limit
Redis - Caching (from image shows Redis with 2ms latency)
url:{shortURL} — STRING (JSON) - {longURL, expiresAt, isCustom} - TTL 24 hours (86400 sec)
click_count:{shortURL} — INT - Real-time click counter (INCR on each redirect)
click_count:{shortURL}:daily — HASH - {date: count} - Clicks per day (HINCRBY)
unique_users:{shortURL} — HYPERLOGLOG - Unique visitor count (PFADD ip_address)
rate_limit:{ip} — INT - Rate limiting counter, TTL 3600 sec (1 hour)
Zookeeper - Counter (from image shows Zookeeper for distributed counter)
Node path — /counters/url_counter
Value — Current counter (e.g., 3748547), atomically incremented
Purpose — Distributed counter for sequential ID generation across multiple servers
Cluster — 3-5 Zookeeper nodes for high availability, quorum = majority
8. ID Generation Approaches - Deep Comparison (from image shows 3 approaches)

From image shows: Three distinct approaches - Counter (Zookeeper), Snowflake, Hash-based (sha1)
Approach 1 - Counter with Zookeeper (from image): Centralized counter incremented atomically. Flow: Server → Zookeeper: increment counter → get 3748547 → Base62 encode → '9i91c0'. Pros: (1) Sequential IDs (predictable, time-ordered), (2) Shortest possible URLs (6-7 chars for billions of URLs), (3) Guaranteed uniqueness (atomic increment = no collisions). Cons: (1) Single point of coordination (Zookeeper required, adds latency ~3ms), (2) Bottleneck: All servers must query same counter (though Zookeeper handles 10K+ req/sec), (3) Dependency: If Zookeeper down → cannot create URLs (mitigated by Zookeeper cluster). When to use: Production systems requiring shortest URLs (Bit.ly, TinyURL use this), can tolerate Zookeeper dependency.
Approach 2 - Snowflake ID (from image shows timestamp + workerID): Decentralized ID generation per server. Flow: Server generates 64-bit ID locally (timestamp + workerID + sequence) → Base62 encode → 'aBc123XyZ'. Structure: [41 bits timestamp][10 bits workerID][12 bits sequence] = 69 years + 1024 workers + 4096 IDs/ms. Pros: (1) No coordination needed (each worker independent), (2) High throughput (4096 IDs/ms/worker = 4M IDs/sec across 1K workers), (3) No single point of failure (workers don't communicate), (4) Time-ordered (IDs increase monotonically). Cons: (1) Longer URLs (10-11 chars vs 6-7 for counter), (2) Clock dependency (requires NTP synchronization, clock drift = collisions), (3) WorkerID management (must assign unique ID to each server). When to use: High-throughput systems, decentralized architecture, can tolerate longer URLs (Twitter uses Snowflake for tweet IDs).
Approach 3 - Hash-based (from image shows 'sha1(longUrl)'): Hash long URL, extract substring as short code. Flow: SHA1(longURL) → 'd3e8f9a2b1c4e5f6...' (40 hex chars) → substring(0, 7) → 'd3e8f9a'. Pros: (1) Deterministic (same long URL → same short URL = deduplication), if user creates same URL twice → returns existing short URL without DB check, (2) No external dependency (no Zookeeper, no coordination), (3) Stateless (any server can generate without querying others). Cons: (1) Collision risk (birthday paradox: ~1M URLs → 0.01% collision probability with 7-char hash), need retry logic: try substring(7, 14), (14, 21), etc., (2) Cannot guarantee URL length (retries may need 8-9 chars), (3) No time-ordering (random distribution). When to use: Systems where deduplication is valuable, can tolerate retry logic, lower creation volume (<1M URLs).
From image note: Encryption overhead shown as 'encrypt: 1ms' for hash approach, 'Zms-3ms' for Zookeeper approach
Production choices: (1) Bit.ly: Counter-based (Zookeeper-like system), prioritizes shortest URLs, (2) Twitter: Snowflake for tweets, high throughput > short length, (3) Google (goo.gl, discontinued): Hash-based with retry, leveraged deduplication, (4) Hybrid approach: Use counter for normal users, Snowflake for API/high-volume users (different URL prefixes: /s/ vs /a/)
Collision handling: Counter approach: No collisions (atomic increment guarantees uniqueness). Snowflake: Collision if (timestamp, workerID, sequence) tuple repeats → requires unique workerID + clock sync. Hash approach: Collision probability = (n^2) / (2 × 62^k) where n=URLs, k=chars, with k=7, n=1M → 0.01% collision → retry with different substring or append timestamp salt.
Migration strategy: (1) Start with counter (simple, reliable), (2) If Zookeeper becomes bottleneck (>100K URL creations/sec) → migrate to Snowflake (allocate workerID to each server), (3) If deduplication becomes important (same URLs shortened repeatedly) → add hash-based caching layer (check if long URL already shortened before generating new ID)
9. Scaling & Optimization Techniques

Technique 1: Base62 encoding - Converts sequential counter (3748547) to short string ('9i91c0'), 6 chars = 56B URLs, URL-safe and human-readable
Technique 2: Redis caching - 90% cache hit rate, <10ms redirect latency, 24-hour TTL balances freshness and memory
Technique 3: Zookeeper counter - Distributed atomic counter, guarantees unique IDs across servers, 3-5 node cluster for high availability
Technique 4: Snowflake ID - Decentralized generation, 4M IDs/sec, no coordination, 64-bit structure (timestamp + workerID + sequence)
Technique 5: Database sharding - Shard by hash(short_url), 10 shards = 100M URLs each, scales to billions
Technique 6: Read replicas - 1 master (writes) + 5 slaves (reads), read/write split, handles 1M redirects/sec
Technique 7: Bloom filter - 5MB filter for 10M URLs, avoids DB queries for non-existent short URLs, 1% false positive acceptable
Technique 8: Analytics partitioning - Monthly partitions (analytics_2026_01), archive old data to S3, keeps recent queries fast
Technique 9: Async analytics - Kafka event stream, don't block redirect, insert analytics later, <10ms redirect latency
Technique 10: Rate limiting - 100 URLs/hour per IP, prevents spam, Redis INCR with TTL, CAPTCHA for suspicious traffic
Technique 11: CDN for redirects - Cache popular short URLs at edge, <50ms global latency, reduces server load 80%
Technique 12: Custom URL namespace - Separate custom from auto-generated, prevents collisions, custom gets priority
10. Common Interview Questions

Q
How do you generate unique short URLs? Compare different approaches (counter, hash, Snowflake).
A
Three main approaches for unique short URL generation: Approach 1 - Counter with Zookeeper (from image): Centralized distributed counter. Implementation:

(1) Zookeeper maintains counter: /counters/url_counter with current value (e.g., 3748547),

(2) Server requests ID: zk.getData('/counters/url_counter') → 3748547, zk.setData('/counters/url_counter', 3748548) (atomic increment),

(3) Base62 encode: encode

(3748547) → characters = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ', num = 3748547; result = ''; while (num > 0) { result = chars[num % 62] + result; num = floor(num / 62); } → result = '9i91c0',

(4) Store: INSERT INTO urls (short_url: '9i91c0', long_url: 'https://...'),

(5) Response: {shortURL: 'http://bit.ly/9i91c0'}. Uniqueness guarantee: Zookeeper atomic increment ensures no two servers get same counter value, even under concurrent requests. Zookeeper cluster (3-5 nodes) maintains consistency via Paxos consensus, if leader fails → new leader elected, counter state preserved. Base62 encoding: 62^6 = 56.8 billion unique URLs with 6 characters, 62^7 = 3.5 trillion with 7 characters, sufficient for decades. Pros:

(1) Shortest possible URLs (6-7 chars), optimal for user experience,

(2) Sequential IDs (time-ordered, can query 'recent URLs'),

(3) Guaranteed uniqueness (no collision handling needed),

(4) Predictable capacity (know exactly when to add more chars). Cons:

(1) Zookeeper dependency (single point of coordination, adds 2-3ms latency),

(2) Bottleneck: All servers query same counter (though Zookeeper handles 10K+ req/sec, can scale to 100K with read replicas),

(3) If Zookeeper down → cannot create URLs (mitigated by cluster). Production: Bit.ly uses counter-based approach. Approach 2 - Hash-based (SHA1/MD5): Hash long URL, extract substring. Implementation:

(1) Hash URL: hash = SHA1('https://www.facebook.com/...') = 'd3e8f9a2b1c4e5f6a7b8c9d0e1f2a3b4c5d6e7f8' (160 bits = 40 hex chars),

(2) Extract 7 chars: shortCode = hash.substring(0, 7) = 'd3e8f9a',

(3) Check collision: SELECT COUNT(*) FROM urls WHERE short_url='d3e8f9a', if count > 0: Try next 7 chars: hash.substring(7, 14), hash.substring(14, 21), ... (up to 5 attempts), if all collide: Append timestamp: hash(longURL + currentTimestamp),

(4) Store: INSERT INTO urls (short_url: 'd3e8f9a', long_url: 'https://...'),

(5) Response: {shortURL: 'http://bit.ly/d3e8f9a'}. Collision probability: SHA1 output space = 2^160, 7 hex chars = 16^7 = 268M possible values, with 1M URLs created: collision_prob = (1M^2) / (2 × 268M) ≈ 0.002% (extremely low), with 10M URLs: ≈ 0.2% (need retries). Pros:

(1) Deterministic (same long URL → same hash → same short URL), enables deduplication: if user creates same URL twice → SELECT * FROM urls WHERE long_url='...' → return existing short URL (no new creation),

(2) No external dependency (no Zookeeper, no coordination), each server generates independently,

(3) Stateless (any server can generate without DB query first),

(4) Deduplication saves storage (10% of URLs are duplicates → 10% storage saving). Cons:

(1) Collision risk (requires retry logic, complex),

(2) Cannot guarantee URL length (after retries might need 8-9 chars),

(3) No time-ordering (hash output is random),

(4) More DB queries (check collision on each attempt). Production: Google's goo.gl used hash-based approach (now discontinued). Approach 3 - Snowflake ID (Twitter-style): Decentralized 64-bit ID generation. Structure: [1 bit unused][41 bits timestamp][10 bits workerID][12 bits sequence], Components:

(1) Timestamp (41 bits): Milliseconds since custom epoch (e.g., Jan 1, 2020 00:00:00 UTC), 41 bits → 2^41 ms ≈ 69 years, current time: Jan 26, 2026 10:30:45.123 → ms since epoch: 189432045123,

(2) WorkerID (10 bits): Unique ID per server (0-1023), assigned during server startup (e.g., from config, environment variable, or auto-assigned), 10 bits → 2^10 = 1024 workers (servers),

(3) Sequence (12 bits): Counter within same millisecond per worker, resets every millisecond, 12 bits → 2^12 = 4096 IDs per millisecond per worker. Generation:

(1) Get current timestamp: ts = currentTimeMillis() - CUSTOM_EPOCH,

(2) Check sequence: if (lastTimestamp == ts) { sequence = (sequence + 1) & 0xFFF; if (sequence == 0) wait until next ms; } else { sequence = 0; lastTimestamp = ts; },

(3) Combine bits: id = (ts << 22) | (workerID << 12) | sequence, Example: ts=189432045123, workerID=123, sequence=0 → id = (189432045123 << 22) | (123 << 12) | 0 = 792345678901234567 (64-bit number),

(4) Base62 encode: encode

(792345678901234567) → 'aBc123XyZ' (10 chars). Pros:

(1) No coordination (each worker generates IDs independently, no Zookeeper),

(2) High throughput: 4096 IDs/ms/worker × 1024 workers = 4M IDs/sec,

(3) No single point of failure (workers don't communicate),

(4) Time-ordered (IDs increase monotonically, newer URLs have higher IDs),

(5) Scalable (add more workers up to 1024). Cons:

(1) Longer URLs: 64-bit number → 10-11 chars in Base62 (vs 6-7 for counter), can mitigate by using only lower 42 bits (still 69 years) → 7-8 chars,

(2) Clock dependency: Requires synchronized clocks (NTP), clock drift/going backward can cause collisions,

(3) WorkerID management: Must assign unique ID to each server (manual config or centralized registry). Production: Twitter uses Snowflake for tweet IDs (IDs visible in URLs). Decision matrix: Choose Counter if:

(1) Need shortest URLs (6-7 chars critical),

(2) Can tolerate Zookeeper dependency,

(3) Creation rate <100K/sec. Choose Hash if:

(1) Deduplication important (same URLs shortened repeatedly),

(2) Want stateless generation (no coordination),

(3) Can handle retry logic. Choose Snowflake if:

(1) High throughput (>100K creations/sec),

(2) Want decentralization (no coordination),

(3) Can tolerate longer URLs (10-11 chars). Hybrid approach: Use counter for normal users (/s/ prefix), Snowflake for API/high-volume users (/a/ prefix), best of both worlds.

Q
How do you handle 1 billion redirects per day with low latency (<100ms)?
A
Handling 1B redirects/day with low latency requires aggressive caching and optimized architecture: Scale calculation: 1B redirects/day = 1,000,000,000 / 86400 sec ≈ 11,500 req/sec average, Peak (10× average) = 115,000 req/sec during traffic spikes. Caching strategy (critical from image shows Redis with 2ms latency): Redis cache layer stores URL mappings in-memory. Cache design:

(1) Key: url:{short_url}, Example: url:9i91c0,

(2) Value: JSON {longURL: 'https://www.facebook.com/...', expiresAt: '2027-01-26', isCustom: false},

(3) TTL: 86400 sec (24 hours), Popular URLs stay cached (TTL refreshed on access), Unpopular URLs expire after 24h (free memory). Redirect flow with caching:

(1) User clicks: GET http://bit.ly/9i91c0,

(2) Server extracts short code: '9i91c0',

(3) Redis lookup: result = redis.get('url:9i91c0'), if (result != null): Parse JSON, check expiration: if (expiresAt && expiresAt < now()) return 410 'Link expired', else return 301 redirect to longURL, Latency: <1ms (Redis in-memory lookup),

(4) Cache miss (10% of requests): Query database: SELECT long_url, expires_at FROM urls WHERE short_url='9i91c0', if not found: return 404 'Short URL not found', if found: Write to cache: redis.set('url:9i91c0', JSON.stringify({longURL, expiresAt}), 'EX', 86400), return 301 redirect, Latency: ~50ms (DB query + Redis write + redirect),

(5) Browser redirects to long URL automatically. Cache hit rate optimization: Target: >90% hit rate (90% requests served from Redis, 10% hit DB). Popular URLs: Clicked thousands of times/day → always in cache (TTL refreshed on each access via GET), Example: Viral link shared on Twitter → 1M clicks/day → cached after first request, next 999,999 requests from cache (<1ms each). Unpopular URLs: Clicked once a month → may not be cached → acceptable (DB can handle 10% of traffic = 11.5K req/sec), Example: Old link from 2020 → user clicks → cache miss → DB query → cache for 24h → if no more clicks → expires from cache. Write-through caching: On URL creation: INSERT INTO urls (...), Immediately: redis.set('url:' + shortURL, ..., 'EX', 86400), Ensures first redirect is fast (no cache miss). Database optimization: Read replicas: 1 master (writes: URL creation) + 5 read replicas (reads: redirects), Read/write split: URL creation → master, Redirects → replicas (round-robin load balancing), Each replica handles: 11.5K req/sec ÷ 5 = 2.3K req/sec (easily handled by PostgreSQL). Connection pooling: Each application server: 50 DB connections (connection pool), Reuse connections across requests (avoid connection overhead ~10ms), PgBouncer: DB connection pooler (100 connections from 1000 app servers → 100 connections to DB = connection multiplexing). Indexes: PRIMARY KEY on short_url (B-tree index, O(log N) lookup), With 1B URLs: Index depth ≈ 4-5 levels, Query time: <10ms even at 1B scale. Database sharding (if needed): Shard by hash(short_url) mod 10 → 10 shards, Each shard: 100M URLs, Query routing: Determine shard from short code, route request to correct shard. Application server scaling: Redirect handling: CPU-light (Redis lookup, JSON parse), I/O-bound (network calls to Redis/DB), Servers: 100 servers × 1K req/sec = 100K req/sec capacity (handles peak 115K with headroom). Auto-scaling: If CPU > 70% → add servers (horizontal scaling), If CPU < 30% → remove servers (cost optimization), Kubernetes: Auto-scale based on CPU/memory metrics. Load balancing: Round-robin: Distributes requests evenly across 100 servers, Health checks: Ping each server every 10 sec, remove unhealthy servers from pool, Sticky sessions: NOT needed (stateless, any server can handle any request). Redis cluster: Single Redis instance: 10K-50K req/sec (bottleneck at high scale), Redis Cluster: 10 master nodes + 10 replicas, Sharding: Shard by short_url hash, each node handles 11.5K req/sec (total 115K req/sec), Replication: Each master has 1 replica (failover if master crashes). Bloom filter optimization (avoid DB queries for non-existent URLs): Problem: User typos short URL: http://bit.ly/xyz123 (doesn't exist), Cache miss → DB query → returns nothing → wasted query (happens 1% of requests = 1.15K req/sec). Solution: Bloom filter (probabilistic data structure), Size: 5 MB for 10M URLs (1% false positive rate), Check: if (bloomFilter.contains('xyz123') == false) return 404 immediately (no Redis/DB query), if (bloomFilter.contains('xyz123') == true) might exist → proceed with Redis/DB query. Benefit: Eliminates 1% of unnecessary DB queries = 1.15K req/sec saved, False positives: 1% of bloom filter checks → query DB anyway (acceptable overhead). CDN for popular URLs (optional): Cache redirects at CDN edge: For top 1000 most-clicked URLs, Cloudflare/Fastly caches 301 redirects at edge (200+ global locations), User request → CDN edge → cached redirect (no origin server request), Latency: <50ms globally (vs 100-200ms to origin), Benefit: Reduces origin server load 80% (top 1000 URLs account for 80% of traffic). Latency breakdown: Cache hit (90% requests): Redis lookup: 0.5ms, JSON parse: 0.1ms, Redirect response: 0.5ms, Total: ~1-2ms (well under 100ms target). Cache miss (10% requests): DB query: 30ms (replica, indexed lookup), Redis write: 0.5ms, Redirect response: 0.5ms, Total: ~31ms (still under 100ms). Monitoring: Track p50, p95, p99 latency: p50: <5ms (median, mostly cache hits), p95: <50ms (some cache misses), p99: <100ms (DB queries, acceptable tail latency), Alert if p99 > 100ms (investigate: DB slow? Redis down? Network issue?). Result: System handles 1B redirects/day (115K req/sec peak) with <100ms latency, 90%+ cache hit rate = <2ms for most requests, 10% cache misses = <50ms (DB optimized), scales horizontally (add servers/Redis nodes as needed).

Q
How do you prevent abuse (spam URLs, malicious links) and implement rate limiting?
A
Comprehensive abuse prevention with multiple layers: Rate limiting (prevent spam URL creation): Per-IP rate limiting:

(1) Limit: 100 URL creations per hour per IP address,

(2) Implementation: Redis counter, On POST /s/url request: key = 'rate_limit:create:' + ip_address, count = redis.incr(key), if (count == 1) redis.expire(key, 3600) (set 1-hour TTL on first request), if (count > 100) return 429 'Too Many Requests, try again in ' + (ttl / 60) + ' minutes',

(3) Bypass for authenticated users: If user logged in (OAuth) → higher limit (1000/hour), Encourages users to create accounts. Per-user rate limiting (authenticated):

(1) Limit: 1000 URLs per day per user,

(2) Implementation: Database counter, On URL creation: SELECT quota_used, quota_limit FROM users WHERE user_id={user_id}, if (quota_used >= quota_limit) return 429 'Daily quota exceeded, upgrade to premium for unlimited', UPDATE users SET quota_used = quota_used + 1,

(3) Reset daily: Cron job runs at midnight: UPDATE users SET quota_used = 0. CAPTCHA challenge (detect bots):

(1) Trigger conditions: If IP creates 10 URLs in 1 minute → require CAPTCHA, If IP has 5 failed attempts → require CAPTCHA, New IP (first-time user) creating URL → optional CAPTCHA (based on risk score),

(2) Implementation: Google reCAPTCHA v3 (invisible, scores user 0.0-1.0), Frontend: Include reCAPTCHA widget, on form submit: token = await grecaptcha.execute(SITE_KEY, {action: 'create_url'}), POST /s/url with {longURL, captchaToken: token}, Backend: Verify token with Google: response = await fetch('https://www.google.com/recaptcha/api/siteverify', {method: 'POST', body: {secret: SECRET_KEY, response: captchaToken}}), score = response.score (0.0 = bot, 1.0 = human), if (score < 0.5) return 400 'CAPTCHA failed, please try again' (show image challenge), if (score >= 0.5) proceed with URL creation. Malicious URL detection (prevent phishing, malware): Blacklist check:

(1) Google Safe Browsing API: On URL creation: response = await fetch('https://safebrowsing.googleapis.com/v4/threatMatches:find', {method: 'POST', body: {client: {clientId: 'myapp', clientVersion: '1.0'}, threatInfo: {threatTypes: ['MALWARE', 'SOCIAL_ENGINEERING', 'UNWANTED_SOFTWARE'], platformTypes: ['ANY_PLATFORM'], threatEntryTypes: ['URL'], threatEntries: [{url: longURL}]}}}), if (response.matches && response.matches.length > 0) return 400 'Malicious URL detected: ' + response.matches[0].threatType,

(2) Cost: Free tier (10K lookups/day), paid tier (500K lookups/day). Phishing pattern detection:

(1) Domain similarity check: User submits 'http://paypa1.com' (phishing paypal.com with '1' instead of 'l'), Check edit distance: levenshteinDistance('paypa1.com', 'paypal.com') = 1 (very similar), if distance < 2 and domain in popular_domains_list → flag as suspicious,

(2) URL obfuscation: Check for IP addresses: /^https?:\/\/\d+\.\d+\.\d+\.\d+/ (e.g., http://192.168.1.1), Check for excessive subdomains: 'http://login.secure.account.paypal-verify.com' (red flag), Check for URL shorteners in long URL: 'http://bit.ly/...' (shortening a short URL = suspicious). User reporting:

(1) Report button: Each short URL page has 'Report abuse' button,

(2) Submission: POST /api/v1/report with {shortURL, reason: 'phishing'/'spam'/'malware'/'inappropriate'},

(3) Threshold: If URL reported 10 times → auto-flag for review, If URL reported 3 times by trusted users (verified accounts) → auto-flag,

(4) Manual review: Moderator views reported URLs, decides:

(a) Confirmed malicious → DELETE FROM urls, DEL url:{shortURL} from cache,

(b) False positive → mark as reviewed, ignore future reports. Content scanning (for uploaded pages):

(1) If long URL points to user-uploaded content (e.g., image hosting site), Scan content: Virus scan (ClamAV), Image moderation (AWS Rekognition for inappropriate content),

(2) If flagged → reject URL creation. Abuse monitoring:

(1) Metrics: Track: URLs created per IP histogram (identify IPs creating 100s of URLs), Track: Short URLs with 0 clicks after 24 hours (likely spam), Track: URLs with high report rate,

(2) Automated bans: If IP creates 500 URLs in 1 hour (despite rate limit, using multiple IPs) → ban IP range, If user account creates 50 reported URLs → ban account,

(3) Honeypot: Create fake short URLs (never shared publicly), If clicked → IP is likely bot (scanning URL space) → ban. URL validation:

(1) Protocol check: Must start with http:// or https://, Reject: javascript:alert('XSS'), data:text/html,<script>..., file:///etc/passwd,

(2) Length check: longURL < 2048 chars (browser limit),

(3) DNS check: Resolve domain: dns.lookup(domain), if fails → reject 'Invalid domain', if domain is internal IP (192.168.x.x, 10.x.x.x) → reject (SSRF prevention). Authentication & authorization:

(1) Optional login: Allow anonymous URL creation (Bit.ly model) OR require login (enterprise model),

(2) OAuth providers: Google, GitHub, Twitter (trusted identity),

(3) Benefits: Track user's URLs: GET /api/v1/users/{userId}/urls, Edit/delete URLs (only creator can modify), Private URLs (only creator sees analytics), Higher rate limits (1000/day vs 100/day for anonymous). API keys (for programmatic access):

(1) Generate API key: user.api_key = generateRandomString

(32), Store hash: users.api_key_hash = bcrypt.hash(api_key),

(2) Usage: POST /s/url with header 'Authorization: Bearer {api_key}',

(3) Rate limit per API key: 10K requests/day, Track: redis.incr('api_key_quota:' + api_key_hash),

(4) Revocation: If API key compromised → regenerate, old key invalidated. Legal compliance:

(1) Terms of Service: Users agree not to create malicious/spam URLs, Violation → account termination,

(2) DMCA takedown: Copyright holders can request URL removal, Process: Verify request → DELETE URL → notify creator,

(3) Law enforcement: Comply with legal requests (court orders) for URL creator identity. Result: Multi-layered defense: Rate limiting (100/hour per IP, 1000/day per user), CAPTCHA (bot detection, reCAPTCHA v3 scoring), Malicious URL detection (Safe Browsing API, pattern matching), User reporting (community moderation), Monitoring & bans (automated abuse detection), reduces spam 99%, legitimate users unaffected, malicious URLs blocked before creation or flagged post-creation.

11. Key Numbers to Remember

Scale & Performance
DAU / URLs — 100M DAU, 1B URLs stored, 1B redirects/day (11.5K req/sec average, 115K peak)
Latency — Redirect <100ms target (Redis cache hit <2ms, DB miss ~50ms)
Cache hit rate — 90%+ (popular URLs always cached, 24-hour TTL)
Read:Write ratio — 100:1 (reads >> writes, redirect-heavy workload)
ID Generation (from image shows 3 approaches)
Base62 capacity — 62^6 = 56.8 billion (6 chars), 62^7 = 3.5 trillion (7 chars)
Zookeeper counter — 2-3ms latency (from image: 'Zms-3ms'), atomic increment, sequential IDs
Snowflake structure — 64-bit: [41 bits timestamp][10 bits workerID][12 bits sequence] = 69 years + 1024 workers + 4096 IDs/ms
Hash collision — SHA1 7 chars: 0.01% collision at 1M URLs, 0.2% at 10M URLs (need retries)
Caching & Database (from image)
Redis latency — From image: '2ms' for cache lookup, <1ms in-memory read
DB latency — From image: '5ms' server to DB, ~10ms indexed query, 30-50ms total for cache miss
Encryption overhead — From image: 'encrypt: 1ms' for hash-based approach, 20% encryption / 80% decryption workload
Total redirect time — From image: '=16ms + 16ms' round trip (server processing + DB query)
Storage & Scaling
Storage per URL — ~610 bytes (short_url 10B + long_url 500B avg + metadata 100B)
1B URLs storage — 610B × 1B ≈ 600 GB (with indexes ~780 GB)
Analytics storage — 200 bytes/click, 1B clicks/day = 200 GB/day, 90 days = 18 TB
Bloom filter — 5 MB for 10M URLs (1% false positive rate)
Key Interview Tips

⚠️
CRITICAL: Short URL uniqueness is NON-NEGOTIABLE. Use Zookeeper atomic counter (guaranteed uniqueness) OR Snowflake with proper workerID management OR hash-based with collision retry. Database UNIQUE constraint on short_url column is mandatory backup. Two users getting same short URL = catastrophic failure.

⭐
Interviewers ALWAYS ask: 'How generate unique short URLs?'. Answer: Three approaches from image: (1) Counter (Zookeeper atomic increment → Base62 encode, shortest 6-7 chars), (2) Snowflake (64-bit: timestamp + workerID + sequence, 10-11 chars), (3) Hash (SHA1 → substring, deterministic deduplication). Production: Bit.ly uses counter, Twitter uses Snowflake.

💡
Base62 encoding (from image): Characters [0-9a-zA-Z] = 62 chars. Algorithm: num=3748547; result=''; while(num>0){result=chars[num%62]+result; num=floor(num/62);} → '9i91c0'. Capacity: 62^6 = 56B URLs (6 chars), 62^7 = 3.5T (7 chars). URL-safe, human-readable, optimal for shortening.

⭐
Must explain: Redis caching (from image shows 2ms latency). Cache hit 90%+ → <2ms redirect. Cache miss 10% → DB query ~50ms. Write-through: INSERT DB → SET cache immediately. TTL 24 hours (popular URLs stay cached). Bloom filter prevents DB queries for non-existent URLs (5MB for 10M URLs).

⚠️
NEVER skip malicious URL detection. Use Google Safe Browsing API before URL creation. Check phishing patterns (paypa1.com vs paypal.com edit distance). Validate protocol (reject javascript:, data:, file: schemes → XSS/SSRF prevention). User reports + manual review for flagged URLs. Abuse = service shutdown risk.

💡
From image: Zookeeper counter with 'Zms-3ms' latency. Distributed coordination for unique IDs across multiple encryption servers (round-robin load balancing). 3-5 node cluster (quorum = majority), leader election on failure. Atomic increment guarantees no collisions. Alternative: Snowflake if Zookeeper is bottleneck (>100K creations/sec).

⭐
Interviewers love: 'Handle 1B redirects/day?'. Answer: (1) Redis cache 90% hits <2ms, (2) 5 DB read replicas handle 10% misses (11.5K req/sec ÷ 5 = 2.3K/replica), (3) 100 app servers × 1K req/sec = 100K capacity (peak 115K), (4) CDN caches top 1000 URLs (80% traffic) at edge <50ms globally. Scales horizontally.

⚠️
NEVER use simple hash as short URL without collision handling. Hash collision at 1M URLs ≈ 0.01% (birthday paradox). MUST implement retry logic: try substring(0,7), (7,14), (14,21) or append timestamp salt. Database UNIQUE constraint catches collisions. 5 retry attempts max, fallback to counter if all fail.

💡
Rate limiting (abuse prevention): 100 URLs/hour per IP (Redis INCR with 3600 sec TTL), 1000/day for authenticated users. CAPTCHA if 10 URLs/minute (reCAPTCHA v3 scoring). Ban IP if 500 URLs/hour despite limits. Malicious URL detection via Safe Browsing API. User reporting threshold: 10 reports → manual review.

⭐
Must mention from image: Three approaches compared. Counter (Zookeeper): shortest URLs 6-7 chars, sequential, 2-3ms overhead. Snowflake: decentralized, 10-11 chars, 4M IDs/sec, no coordination. Hash (SHA1): deterministic deduplication, same URL → same short code, 0.01% collision need retry. Choose based on: shortest URL (counter), highest throughput (Snowflake), deduplication (hash).