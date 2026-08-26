# Rate Limiter - Complete LLD Interview Guide

**Interview Duration: 45 minutes | Difficulty: Medium | Must-Know: ⭐⭐⭐**

---

## CONVERSATIONAL SCRIPT (How to approach in interview)

### Phase 1: Requirements Clarification (3 mins)

**You:** "Let me clarify the requirements for the Rate Limiter."

**Functional Requirements:**
- "Limit number of requests per user/IP/API key within a time window"
- "Support different rate limiting strategies - per second, per minute, per hour"
- "Return success/failure for each request"
- "Should be configurable - different limits for different APIs"
- "Support burst traffic handling"

**Interviewer:** "Yes. Also support distributed rate limiting across multiple servers."

**You:** "Got it. For non-functional requirements:"
- "Low latency - shouldn't slow down requests significantly"
- "High availability - rate limiter failure shouldn't block all traffic"
- "Accurate - shouldn't allow significantly more/less than the limit"
- "Memory efficient"
- "Thread-safe for concurrent requests"

**Interviewer:** "Focus on different algorithms and their trade-offs."

---

### Phase 2: Rate Limiting Algorithms (5 mins)

**You:** "There are several popular algorithms. Let me explain each:"

```
┌──────────────────────────────────────────────────────────────┐
│           RATE LIMITING ALGORITHMS COMPARISON                │
└──────────────────────────────────────────────────────────────┘

1. TOKEN BUCKET
═══════════════════════════════════════════════════════
Bucket with tokens, refilled at constant rate
Allows bursts up to bucket capacity

Timeline (capacity=5, refill=1/sec):
Time  Tokens  Request  Result
────────────────────────────────
0s    5       -        -
1s    5       3 req    ✓ (2 left)
2s    3       2 req    ✓ (1 left)
3s    2       10 req   ✗ (only 2 available)
4s    3       2 req    ✓ (1 left)

Pros: ✓ Allows bursts, ✓ Smooth traffic
Cons: ✗ Complex implementation


2. LEAKY BUCKET
═══════════════════════════════════════════════════════
Requests fill a bucket, leaked at constant rate
Smooths out bursts

        [Request]
            ↓
     ┌─────────────┐
     │   BUCKET    │  ← Incoming requests
     │             │
     │  ░░░░░░░░░  │  ← Queue fills up
     └──────┬──────┘
            ↓
      [Leak Rate]    ← Constant outflow

Pros: ✓ Smooth traffic, ✓ No bursts
Cons: ✗ Slow during bursts


3. FIXED WINDOW
═══════════════════════════════════════════════════════
Count requests in fixed time windows

Time Windows (1-minute windows, limit=100):
┌────────────┬────────────┬────────────┐
│ 00:00-01:00│ 01:00-02:00│ 02:00-03:00│
│  95 req ✓  │  120 req ✗ │  80 req ✓  │
└────────────┴────────────┴────────────┘

Pros: ✓ Simple, ✓ Memory efficient
Cons: ✗ Burst at window edges

Edge Case Problem:
00:59 - 100 requests ✓
01:00 - counter resets
01:01 - 100 requests ✓
→ 200 requests in 2 seconds!


4. SLIDING WINDOW LOG
═══════════════════════════════════════════════════════
Keep timestamp of each request, count in sliding window

Current Time: 10:00:50
Window: Last 60 seconds (9:59:50 - 10:00:50)

Requests: [9:59:51, 9:59:55, 10:00:10, 10:00:45, ...]
                ↑ Remove old    ↑ Count these

Pros: ✓ Accurate, ✓ No edge case
Cons: ✗ Memory intensive (store all timestamps)


5. SLIDING WINDOW COUNTER
═══════════════════════════════════════════════════════
Hybrid: Fixed windows + weighted count

Current window: 10:00-11:00
Previous window: 09:00-10:00
Current time: 10:30 (50% into window)

Requests allowed = 
  (prev_count × 50%) + curr_count ≤ limit

Pros: ✓ Memory efficient, ✓ More accurate than fixed
Cons: ✗ Approximate (not perfectly accurate)
```

**You:** "For most production systems, I'd recommend **Token Bucket** for its balance of burst handling and accuracy. For strict rate limiting, **Sliding Window Counter** is a good compromise."

---

### Phase 3: Class Design (5 mins)

**You:** "Let me design the class structure:"

```
┌─────────────────────────────────────────────────────────────┐
│                    CLASS STRUCTURE                           │
└─────────────────────────────────────────────────────────────┘

┌────────────────────────┐
│    RateLimiter         │ (Interface)
│  ────────────────────  │
│  + allowRequest(key):  │
│      boolean           │
└────────┬───────────────┘
         │
         ▲
         │
    ┌────┴────┬─────────┬──────────┬──────────┐
    │         │         │          │          │
┌───▼────┐ ┌──▼────┐ ┌──▼─────┐ ┌──▼──────┐ ┌─▼────────┐
│ Token  │ │ Leaky │ │ Fixed  │ │ Sliding │ │ Sliding  │
│ Bucket │ │Bucket │ │ Window │ │ Window  │ │  Window  │
│        │ │       │ │        │ │  Log    │ │ Counter  │
└────────┘ └───────┘ └────────┘ └─────────┘ └──────────┘


┌────────────────────────┐
│  RateLimiterConfig     │
│  ────────────────────  │
│  - limit: int          │
│  - windowSizeMs: long  │
│  - refillRate: int     │
│  ────────────────────  │
│  + getLimit()          │
└────────────────────────┘


┌────────────────────────┐
│  RateLimiterFactory    │ (Factory Pattern)
│  ────────────────────  │
│  + create(algorithm,   │
│           config)      │
└────────────────────────┘


┌────────────────────────┐
│  DistributedRateLimiter│
│  ────────────────────  │
│  - redisClient         │
│  ────────────────────  │
│  + allowRequest(key)   │
└────────────────────────┘
```

---

### Phase 4: Core Implementation (20 mins)

**You:** "Let me implement the key algorithms:"

#### 1. RateLimiter Interface

```java
public interface RateLimiter {
    /**
     * Check if request should be allowed
     * @param key - user ID, IP address, or API key
     * @return true if allowed, false if rate limited
     */
    boolean allowRequest(String key);
    
    /**
     * Reset rate limiter for a key
     */
    void reset(String key);
}

public class RateLimiterConfig {
    private final int maxRequests;
    private final long windowSizeMs;
    
    public RateLimiterConfig(int maxRequests, long windowSizeMs) {
        this.maxRequests = maxRequests;
        this.windowSizeMs = windowSizeMs;
    }
    
    public int getMaxRequests() { return maxRequests; }
    public long getWindowSizeMs() { return windowSizeMs; }
    
    // Factory methods for common configs
    public static RateLimiterConfig perSecond(int maxRequests) {
        return new RateLimiterConfig(maxRequests, 1000);
    }
    
    public static RateLimiterConfig perMinute(int maxRequests) {
        return new RateLimiterConfig(maxRequests, 60 * 1000);
    }
    
    public static RateLimiterConfig perHour(int maxRequests) {
        return new RateLimiterConfig(maxRequests, 60 * 60 * 1000);
    }
}
```

---

#### 2. Token Bucket Algorithm

```java
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class TokenBucketRateLimiter implements RateLimiter {
    private final int capacity;              // Max tokens in bucket
    private final int refillRate;            // Tokens added per second
    private final Map<String, Bucket> buckets;
    
    public TokenBucketRateLimiter(int capacity, int refillRate) {
        this.capacity = capacity;
        this.refillRate = refillRate;
        this.buckets = new ConcurrentHashMap<>();
    }
    
    @Override
    public synchronized boolean allowRequest(String key) {
        Bucket bucket = buckets.computeIfAbsent(key, k -> new Bucket(capacity));
        
        // Refill tokens based on time elapsed
        bucket.refill(refillRate);
        
        // Try to consume a token
        if (bucket.tokens > 0) {
            bucket.tokens--;
            return true;
        }
        
        return false;
    }
    
    @Override
    public void reset(String key) {
        buckets.remove(key);
    }
    
    private static class Bucket {
        private double tokens;
        private long lastRefillTime;
        private final int capacity;
        
        Bucket(int capacity) {
            this.capacity = capacity;
            this.tokens = capacity;
            this.lastRefillTime = System.currentTimeMillis();
        }
        
        void refill(int refillRate) {
            long now = System.currentTimeMillis();
            long elapsedMs = now - lastRefillTime;
            
            // Calculate tokens to add
            double tokensToAdd = (elapsedMs / 1000.0) * refillRate;
            
            // Add tokens (max = capacity)
            tokens = Math.min(capacity, tokens + tokensToAdd);
            
            lastRefillTime = now;
        }
    }
    
    // For debugging
    public void printStatus(String key) {
        Bucket bucket = buckets.get(key);
        if (bucket != null) {
            System.out.printf("Key: %s | Tokens: %.2f/%d%n", 
                key, bucket.tokens, capacity);
        }
    }
}
```

---

#### 3. Fixed Window Algorithm

```java
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class FixedWindowRateLimiter implements RateLimiter {
    private final int maxRequests;
    private final long windowSizeMs;
    private final Map<String, Window> windows;
    
    public FixedWindowRateLimiter(int maxRequests, long windowSizeMs) {
        this.maxRequests = maxRequests;
        this.windowSizeMs = windowSizeMs;
        this.windows = new ConcurrentHashMap<>();
    }
    
    @Override
    public synchronized boolean allowRequest(String key) {
        long now = System.currentTimeMillis();
        Window window = windows.computeIfAbsent(key, k -> new Window(now));
        
        // Check if we're in a new window
        if (now - window.startTime >= windowSizeMs) {
            // Reset window
            window.startTime = now;
            window.requestCount = 0;
        }
        
        // Check if under limit
        if (window.requestCount < maxRequests) {
            window.requestCount++;
            return true;
        }
        
        return false;
    }
    
    @Override
    public void reset(String key) {
        windows.remove(key);
    }
    
    private static class Window {
        long startTime;
        int requestCount;
        
        Window(long startTime) {
            this.startTime = startTime;
            this.requestCount = 0;
        }
    }
    
    public void printStatus(String key) {
        Window window = windows.get(key);
        if (window != null) {
            System.out.printf("Key: %s | Requests: %d/%d | Window age: %dms%n",
                key, window.requestCount, maxRequests,
                System.currentTimeMillis() - window.startTime);
        }
    }
}
```

---

#### 4. Sliding Window Log Algorithm

```java
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class SlidingWindowLogRateLimiter implements RateLimiter {
    private final int maxRequests;
    private final long windowSizeMs;
    private final Map<String, LinkedList<Long>> requestLogs;
    
    public SlidingWindowLogRateLimiter(int maxRequests, long windowSizeMs) {
        this.maxRequests = maxRequests;
        this.windowSizeMs = windowSizeMs;
        this.requestLogs = new ConcurrentHashMap<>();
    }
    
    @Override
    public synchronized boolean allowRequest(String key) {
        long now = System.currentTimeMillis();
        LinkedList<Long> log = requestLogs.computeIfAbsent(key, k -> new LinkedList<>());
        
        // Remove timestamps outside the window
        while (!log.isEmpty() && now - log.getFirst() >= windowSizeMs) {
            log.removeFirst();
        }
        
        // Check if under limit
        if (log.size() < maxRequests) {
            log.addLast(now);
            return true;
        }
        
        return false;
    }
    
    @Override
    public void reset(String key) {
        requestLogs.remove(key);
    }
    
    public void printStatus(String key) {
        LinkedList<Long> log = requestLogs.get(key);
        if (log != null) {
            System.out.printf("Key: %s | Requests in window: %d/%d%n",
                key, log.size(), maxRequests);
        }
    }
}
```

---

#### 5. Sliding Window Counter Algorithm

```java
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class SlidingWindowCounterRateLimiter implements RateLimiter {
    private final int maxRequests;
    private final long windowSizeMs;
    private final Map<String, WindowData> windows;
    
    public SlidingWindowCounterRateLimiter(int maxRequests, long windowSizeMs) {
        this.maxRequests = maxRequests;
        this.windowSizeMs = windowSizeMs;
        this.windows = new ConcurrentHashMap<>();
    }
    
    @Override
    public synchronized boolean allowRequest(String key) {
        long now = System.currentTimeMillis();
        WindowData data = windows.computeIfAbsent(key, k -> new WindowData(now));
        
        // Calculate current window number
        long currentWindow = now / windowSizeMs;
        
        // If we're in a new window
        if (currentWindow > data.currentWindowStart) {
            // Move current to previous
            data.previousCount = data.currentCount;
            data.previousWindowStart = data.currentWindowStart;
            
            // Reset current
            data.currentCount = 0;
            data.currentWindowStart = currentWindow;
        }
        
        // Calculate weighted count using sliding window
        long windowStartTime = currentWindow * windowSizeMs;
        long elapsedInWindow = now - windowStartTime;
        double percentageInCurrentWindow = (double) elapsedInWindow / windowSizeMs;
        
        double estimatedCount = 
            data.previousCount * (1 - percentageInCurrentWindow) +
            data.currentCount;
        
        // Check if under limit
        if (estimatedCount < maxRequests) {
            data.currentCount++;
            return true;
        }
        
        return false;
    }
    
    @Override
    public void reset(String key) {
        windows.remove(key);
    }
    
    private static class WindowData {
        long currentWindowStart;
        int currentCount;
        long previousWindowStart;
        int previousCount;
        
        WindowData(long now) {
            this.currentWindowStart = now / 1000; // Window number
            this.currentCount = 0;
            this.previousWindowStart = currentWindowStart - 1;
            this.previousCount = 0;
        }
    }
    
    public void printStatus(String key) {
        WindowData data = windows.get(key);
        if (data != null) {
            System.out.printf("Key: %s | Current: %d | Previous: %d%n",
                key, data.currentCount, data.previousCount);
        }
    }
}
```

---

#### 6. Factory Pattern

```java
public enum RateLimitAlgorithm {
    TOKEN_BUCKET,
    FIXED_WINDOW,
    SLIDING_WINDOW_LOG,
    SLIDING_WINDOW_COUNTER
}

public class RateLimiterFactory {
    public static RateLimiter create(RateLimitAlgorithm algorithm, 
                                     RateLimiterConfig config) {
        switch (algorithm) {
            case TOKEN_BUCKET:
                int refillRate = config.getMaxRequests() / 
                                (int)(config.getWindowSizeMs() / 1000);
                return new TokenBucketRateLimiter(
                    config.getMaxRequests(), 
                    refillRate
                );
                
            case FIXED_WINDOW:
                return new FixedWindowRateLimiter(
                    config.getMaxRequests(),
                    config.getWindowSizeMs()
                );
                
            case SLIDING_WINDOW_LOG:
                return new SlidingWindowLogRateLimiter(
                    config.getMaxRequests(),
                    config.getWindowSizeMs()
                );
                
            case SLIDING_WINDOW_COUNTER:
                return new SlidingWindowCounterRateLimiter(
                    config.getMaxRequests(),
                    config.getWindowSizeMs()
                );
                
            default:
                throw new IllegalArgumentException("Unknown algorithm: " + algorithm);
        }
    }
}
```

---

#### 7. Distributed Rate Limiter (Redis-based)

```java
// Pseudo-code for Redis-based distributed rate limiter
public class DistributedRateLimiter implements RateLimiter {
    private final RedisClient redis;
    private final int maxRequests;
    private final long windowSizeMs;
    
    public DistributedRateLimiter(RedisClient redis, int maxRequests, long windowSizeMs) {
        this.redis = redis;
        this.maxRequests = maxRequests;
        this.windowSizeMs = windowSizeMs;
    }
    
    @Override
    public boolean allowRequest(String key) {
        String redisKey = "rate_limit:" + key;
        long now = System.currentTimeMillis();
        
        // Sliding window log using Redis sorted set
        // Remove old entries
        redis.zRemRangeByScore(redisKey, 0, now - windowSizeMs);
        
        // Count current entries
        long count = redis.zCard(redisKey);
        
        if (count < maxRequests) {
            // Add new entry with current timestamp as score
            redis.zAdd(redisKey, now, UUID.randomUUID().toString());
            
            // Set expiry to prevent memory leak
            redis.expire(redisKey, (int)(windowSizeMs / 1000) + 1);
            
            return true;
        }
        
        return false;
    }
    
    @Override
    public void reset(String key) {
        redis.del("rate_limit:" + key);
    }
}

// Alternative: Fixed Window with Redis
public class RedisFixedWindowRateLimiter implements RateLimiter {
    private final RedisClient redis;
    private final int maxRequests;
    private final long windowSizeMs;
    
    @Override
    public boolean allowRequest(String key) {
        long now = System.currentTimeMillis();
        long windowKey = now / windowSizeMs;
        String redisKey = "rate_limit:" + key + ":" + windowKey;
        
        // Atomic increment
        long current = redis.incr(redisKey);
        
        // Set expiry on first request
        if (current == 1) {
            redis.expire(redisKey, (int)(windowSizeMs / 1000) + 1);
        }
        
        return current <= maxRequests;
    }
    
    @Override
    public void reset(String key) {
        // Delete all keys for this user
        Set<String> keys = redis.keys("rate_limit:" + key + ":*");
        for (String k : keys) {
            redis.del(k);
        }
    }
}
```

---

### Phase 5: Usage Example (5 mins)

**You:** "Here's a complete demo comparing all algorithms:"

```java
public class RateLimiterDemo {
    public static void main(String[] args) throws InterruptedException {
        System.out.println("╔══════════════════════════════════════════╗");
        System.out.println("║    RATE LIMITER COMPARISON               ║");
        System.out.println("╚══════════════════════════════════════════╝\n");
        
        // Config: 10 requests per 5 seconds
        RateLimiterConfig config = new RateLimiterConfig(10, 5000);
        String userId = "user123";
        
        // Test 1: Token Bucket
        System.out.println("=== TEST 1: Token Bucket ===");
        RateLimiter tokenBucket = RateLimiterFactory.create(
            RateLimitAlgorithm.TOKEN_BUCKET, config
        );
        testRateLimiter(tokenBucket, userId, 15);
        
        Thread.sleep(2000);
        
        // Test 2: Fixed Window
        System.out.println("\n=== TEST 2: Fixed Window ===");
        RateLimiter fixedWindow = RateLimiterFactory.create(
            RateLimitAlgorithm.FIXED_WINDOW, config
        );
        testRateLimiter(fixedWindow, userId, 15);
        
        Thread.sleep(2000);
        
        // Test 3: Sliding Window Log
        System.out.println("\n=== TEST 3: Sliding Window Log ===");
        RateLimiter slidingLog = RateLimiterFactory.create(
            RateLimitAlgorithm.SLIDING_WINDOW_LOG, config
        );
        testRateLimiter(slidingLog, userId, 15);
        
        Thread.sleep(2000);
        
        // Test 4: Sliding Window Counter
        System.out.println("\n=== TEST 4: Sliding Window Counter ===");
        RateLimiter slidingCounter = RateLimiterFactory.create(
            RateLimitAlgorithm.SLIDING_WINDOW_COUNTER, config
        );
        testRateLimiter(slidingCounter, userId, 15);
        
        // Test 5: Burst Traffic
        System.out.println("\n=== TEST 5: Burst Traffic with Token Bucket ===");
        TokenBucketRateLimiter burst = new TokenBucketRateLimiter(50, 10);
        
        System.out.println("Sending 30 requests immediately...");
        int allowed = 0;
        for (int i = 0; i < 30; i++) {
            if (burst.allowRequest("burst_user")) {
                allowed++;
            }
        }
        System.out.println("Allowed: " + allowed + "/30 (burst capacity)");
        
        // Wait and try again
        System.out.println("\nWaiting 3 seconds for refill...");
        Thread.sleep(3000);
        
        allowed = 0;
        for (int i = 0; i < 50; i++) {
            if (burst.allowRequest("burst_user")) {
                allowed++;
            }
        }
        System.out.println("Allowed: " + allowed + "/50 (after refill)");
        
        // Test 6: Different users
        System.out.println("\n=== TEST 6: Multiple Users ===");
        RateLimiter multiUser = new TokenBucketRateLimiter(5, 1);
        
        String[] users = {"alice", "bob", "charlie"};
        for (String user : users) {
            int userAllowed = 0;
            for (int i = 0; i < 10; i++) {
                if (multiUser.allowRequest(user)) {
                    userAllowed++;
                }
            }
            System.out.println(user + ": " + userAllowed + "/10 allowed");
        }
        
        System.out.println("\n╔══════════════════════════════════════════╗");
        System.out.println("║           TESTS COMPLETE                 ║");
        System.out.println("╚══════════════════════════════════════════╝");
    }
    
    private static void testRateLimiter(RateLimiter limiter, String key, int requests) {
        int allowed = 0;
        int denied = 0;
        
        for (int i = 1; i <= requests; i++) {
            boolean result = limiter.allowRequest(key);
            if (result) {
                allowed++;
                System.out.print("✓");
            } else {
                denied++;
                System.out.print("✗");
            }
            
            if (i % 5 == 0) {
                System.out.println();
            }
        }
        
        System.out.println("\nResults: " + allowed + " allowed, " + denied + " denied");
    }
}
```

---

### Phase 6: Algorithm Comparison (3 mins)

**You:** "Let me summarize the trade-offs:"

```
┌─────────────────────────────────────────────────────────────┐
│          ALGORITHM COMPARISON TABLE                          │
└─────────────────────────────────────────────────────────────┘

Algorithm           Memory    Accuracy   Burst      Use Case
──────────────────────────────────────────────────────────────
Token Bucket        O(n)      High       ✓ Yes      APIs, general
Leaky Bucket        O(n)      High       ✗ No       Smooth traffic
Fixed Window        O(n)      Low        ✓ Yes      Simple, fast
Sliding Window Log  O(n*m)    Perfect    ✓ Yes      Critical APIs
Sliding Window Ctr  O(n)      High       ✓ Yes      Production

n = number of keys (users/IPs)
m = max requests in window (for log)

RECOMMENDATIONS:
────────────────────────────────────────────────────────────
Scenario                          Best Algorithm
────────────────────────────────────────────────────────────
General API rate limiting         Token Bucket
Strict no-burst requirement       Leaky Bucket
High performance needed           Fixed Window
Perfect accuracy required         Sliding Window Log
Balance of all factors            Sliding Window Counter
Distributed system                Redis Fixed Window
```

---

## SOLID PRINCIPLES IN DEPTH

**You:** "Let me explain how SOLID principles apply to rate limiter design. This is crucial for building extensible throttling systems."

---

### 1. Single Responsibility Principle (SRP)

**Purpose:** Each class should have only ONE reason to change.

**Problem it solves:**
Without SRP, rate limiter logic becomes tangled:
```java
// BAD: RateLimiter doing everything
class RateLimiter {
    // Token bucket logic
    public boolean allowRequest(String userId) { ... }
    
    // Storage management
    public void saveToRedis() { ... }
    public void loadFromRedis() { ... }
    
    // Metrics tracking
    public void recordAllowed() { ... }
    public void recordDenied() { ... }
    
    // User management
    public void addUser() { ... }
    public void removeUser() { ... }
}
// Too many responsibilities! Changing storage affects rate limiting logic.
```

**Advantages:**
- ✅ **Clear purpose** - Each class does one thing well
- ✅ **Easy to test** - Test algorithms independently from storage
- ✅ **Easy to maintain** - Changes are localized
- ✅ **Easy to understand** - Small, focused classes

**In our design:**
```java
// GOOD: Separated responsibilities

// RateLimiter: ONLY enforces rate limits
interface RateLimiter {
    boolean allowRequest(String key);
}

// TokenBucketRateLimiter: ONLY implements token bucket algorithm
class TokenBucketRateLimiter implements RateLimiter {
    @Override
    public boolean allowRequest(String key) {
        // Only token bucket logic
    }
}

// SlidingWindowRateLimiter: ONLY implements sliding window algorithm
class SlidingWindowRateLimiter implements RateLimiter {
    @Override
    public boolean allowRequest(String key) {
        // Only sliding window logic
    }
}

// RateLimiterStorage: ONLY handles persistence (separate class)
interface RateLimiterStorage {
    void save(String key, RateLimiterState state);
    RateLimiterState load(String key);
}

// RateLimiterMetrics: ONLY tracks metrics (separate class)
class RateLimiterMetrics {
    private int allowed, denied;
    
    public void recordAllowed() { allowed++; }
    public void recordDenied() { denied++; }
    public double getAllowRate() { return (double) allowed / (allowed + denied); }
}
```

**Interview tip:** "The RateLimiter class only enforces limits. If I need to add persistence, I create `RateLimiterStorage`. If I need metrics, I create `RateLimiterMetrics`. Each class has one clear job."

---

### 2. Open/Closed Principle (OCP)

**Purpose:** Classes should be OPEN for extension but CLOSED for modification.

**Problem it solves:**
Without OCP, adding algorithms requires modifying existing code:
```java
// BAD: Hard-coded algorithm logic
class RateLimiter {
    private String algorithm;
    
    public boolean allowRequest(String userId) {
        if (algorithm.equals("TOKEN_BUCKET")) {
            // Token bucket logic
        } else if (algorithm.equals("LEAKY_BUCKET")) {
            // Leaky bucket logic
        } else if (algorithm.equals("FIXED_WINDOW")) {
            // Fixed window logic
        }
        // To add Sliding Window, you must MODIFY this method - RISKY!
    }
}
```

**Advantages:**
- ✅ **Zero regression** - Existing algorithms unaffected
- ✅ **Easy to add algorithms** - Just create new class
- ✅ **A/B testing** - Deploy new algorithms without changing core
- ✅ **Stable core** - Main system never changes

**In our design:**
```java
// GOOD: Interface-based extensibility

interface RateLimiter {
    boolean allowRequest(String key);
}

class TokenBucketRateLimiter implements RateLimiter {
    @Override
    public boolean allowRequest(String key) {
        // Token bucket algorithm
    }
}

class LeakyBucketRateLimiter implements RateLimiter {
    @Override
    public boolean allowRequest(String key) {
        // Leaky bucket algorithm
    }
}

class SlidingWindowLogRateLimiter implements RateLimiter {
    @Override
    public boolean allowRequest(String key) {
        // Sliding window log algorithm
    }
}

// NEW: Add Adaptive Rate Limiter - zero changes to existing code!
class AdaptiveRateLimiter implements RateLimiter {
    @Override
    public boolean allowRequest(String key) {
        // Adjust limits based on system load
    }
}

// Factory to create rate limiters
class RateLimiterFactory {
    public static RateLimiter create(RateLimiterType type, int capacity, long refillRate) {
        switch (type) {
            case TOKEN_BUCKET:
                return new TokenBucketRateLimiter(capacity, refillRate);
            case LEAKY_BUCKET:
                return new LeakyBucketRateLimiter(capacity, refillRate);
            case SLIDING_WINDOW:
                return new SlidingWindowLogRateLimiter(capacity, refillRate);
            case ADAPTIVE:  // NEW - just add case!
                return new AdaptiveRateLimiter(capacity, refillRate);
            default:
                throw new IllegalArgumentException("Unknown type");
        }
    }
}
```

**Interview tip:** "To add a new algorithm like 'Adaptive Rate Limiter', I create `AdaptiveRateLimiter` implementing the interface. Zero changes to existing code. The system is closed for modification but open for extension."

---

### 3. Liskov Substitution Principle (LSP)

**Purpose:** Subclasses must be substitutable for their parent classes without breaking behavior.

**Problem it solves:**
Without LSP, some rate limiters violate contracts:
```java
// BAD: Violates LSP
interface RateLimiter {
    boolean allowRequest(String key);
    // Contract: Returns true if allowed, false if rate limited
}

class TokenBucketRateLimiter implements RateLimiter {
    @Override
    public boolean allowRequest(String key) {
        // Returns true/false as expected
    }
}

class BrokenRateLimiter implements RateLimiter {
    @Override
    public boolean allowRequest(String key) {
        throw new UnsupportedOperationException("Not implemented!");  // BREAKS CONTRACT!
    }
}

// Code expecting boolean will crash:
RateLimiter limiter = new BrokenRateLimiter();
if (limiter.allowRequest(userId)) {  // BOOM! Exception instead of boolean
    processRequest();
}
```

**Advantages:**
- ✅ **Predictable behavior** - All limiters work the same way
- ✅ **Polymorphism works** - Can swap limiters at runtime
- ✅ **Testing is easy** - Mock limiters behave like real ones
- ✅ **No surprises** - Code doesn't break when switching implementations

**In our design:**
```java
// GOOD: All rate limiters honor the contract

interface RateLimiter {
    boolean allowRequest(String key);
    // Contract: Returns true if request allowed, false if rate limited
}

class TokenBucketRateLimiter implements RateLimiter {
    @Override
    public boolean allowRequest(String key) {
        // Token bucket logic
        if (hasTokens(key)) {
            consumeToken(key);
            return true;  // ✓ Returns boolean as promised
        }
        return false;  // ✓ Returns boolean as promised
    }
}

class SlidingWindowRateLimiter implements RateLimiter {
    @Override
    public boolean allowRequest(String key) {
        // Sliding window logic
        long now = System.currentTimeMillis();
        cleanupOldRequests(key, now);
        
        if (getRequestCount(key) < limit) {
            addRequest(key, now);
            return true;  // ✓ Returns boolean as promised
        }
        return false;  // ✓ Returns boolean as promised
    }
}

class NoOpRateLimiter implements RateLimiter {
    @Override
    public boolean allowRequest(String key) {
        return true;  // ✓ Always allows, but returns boolean as promised (testing/staging)
    }
}

// Polymorphism works perfectly:
RateLimiter limiter = new TokenBucketRateLimiter(100, 10);  // Or any other implementation
if (limiter.allowRequest(userId)) {  // Works for ANY limiter
    processRequest();
} else {
    sendRateLimitResponse();
}
```

**Interview tip:** "Any code that works with `RateLimiter` will work with `TokenBucket`, `SlidingWindow`, or `NoOp` limiters. They all honor the contract - `allowRequest()` always returns a boolean, never throws unexpected exceptions."

---

### 4. Interface Segregation Principle (ISP)

**Purpose:** Clients should not be forced to depend on interfaces they don't use.

**Problem it solves:**
Without ISP, interfaces force unnecessary dependencies:
```java
// BAD: Fat interface forces implementations of unused methods
interface RateLimiter {
    boolean allowRequest(String key);
    void resetLimit(String key);
    int getRemainingTokens(String key);  // Not all algorithms have "tokens"
    long getNextRefillTime(String key);  // Not all algorithms refill
    void saveState();                    // Not all need persistence
    void loadState();                    // Not all need persistence
    void exportMetrics();                // Not all need metrics
}

// Sliding Window must implement ALL methods!
class SlidingWindowRateLimiter implements RateLimiter {
    @Override
    public int getRemainingTokens(String key) { 
        throw new UnsupportedOperationException("No tokens in sliding window!");  // Forced!
    }
    
    @Override
    public long getNextRefillTime(String key) {
        throw new UnsupportedOperationException("No refill in sliding window!");  // Forced!
    }
}
```

**Advantages:**
- ✅ **Lean interfaces** - Only necessary methods
- ✅ **Better cohesion** - Related methods together
- ✅ **No dummy code** - No forced implementations
- ✅ **Clear contracts** - Interface tells you what to expect

**In our design:**
```java
// GOOD: Segregated interfaces

// Core: Every rate limiter must implement this
interface RateLimiter {
    boolean allowRequest(String key);
}

// Optional: Only for limiters with resettable state
interface ResettableRateLimiter extends RateLimiter {
    void reset(String key);
    void resetAll();
}

// Optional: Only for token-based limiters
interface TokenBasedRateLimiter extends RateLimiter {
    int getRemainingTokens(String key);
    long getNextRefillTime(String key);
}

// Optional: Only for limiters with observable state
interface ObservableRateLimiter extends RateLimiter {
    RateLimiterStats getStats(String key);
}

// Optional: Only for persistent limiters
interface PersistentRateLimiter extends RateLimiter {
    void saveState();
    void loadState();
}

// Implement only what you need:

// Token Bucket: Core + Token-based + Resettable
class TokenBucketRateLimiter implements RateLimiter, 
                                        TokenBasedRateLimiter, 
                                        ResettableRateLimiter {
    @Override
    public int getRemainingTokens(String key) {
        // Token bucket has tokens
    }
    
    @Override
    public void reset(String key) {
        // Can reset token count
    }
}

// Sliding Window: Just core + Observable
class SlidingWindowRateLimiter implements RateLimiter, ObservableRateLimiter {
    // No token methods - doesn't implement TokenBasedRateLimiter!
    
    @Override
    public RateLimiterStats getStats(String key) {
        // Can observe request counts
    }
}

// Fixed Window: Core only (simplest)
class FixedWindowRateLimiter implements RateLimiter {
    // Just basic rate limiting - nothing else!
}

// Distributed Redis Limiter: Core + Persistent
class RedisRateLimiter implements RateLimiter, PersistentRateLimiter {
    @Override
    public void saveState() {
        // Save to Redis
    }
}
```

**Interview tip:** "Core interface has only `allowRequest()`. If a limiter uses tokens, it implements `TokenBasedRateLimiter`. If it needs persistence, it implements `PersistentRateLimiter`. Clients depend only on what they need."

---

### 5. Dependency Inversion Principle (DIP)

**Purpose:** High-level modules should not depend on low-level modules. Both should depend on abstractions.

**Problem it solves:**
Without DIP, high-level code is tightly coupled:
```java
// BAD: API Gateway tightly coupled to concrete implementation
class APIGateway {
    private TokenBucketRateLimiter limiter = new TokenBucketRateLimiter(100, 10);  // TIGHT!
    
    public Response handleRequest(Request request) {
        if (limiter.allowRequest(request.getUserId())) {
            return processRequest(request);
        }
        return new Response(429, "Too Many Requests");
        
        // Can't switch to Sliding Window without modifying APIGateway!
    }
}
```

**Advantages:**
- ✅ **Loose coupling** - Easy to swap algorithms
- ✅ **Testability** - Inject mock limiters for testing
- ✅ **Flexibility** - Change algorithms at runtime
- ✅ **Maintainability** - Low-level changes don't affect high-level

**In our design:**
```java
// GOOD: Depend on abstraction (interface)

interface RateLimiter {
    boolean allowRequest(String key);
}

class TokenBucketRateLimiter implements RateLimiter { ... }
class SlidingWindowRateLimiter implements RateLimiter { ... }
class LeakyBucketRateLimiter implements RateLimiter { ... }

class APIGateway {
    private RateLimiter limiter;  // Interface, not concrete class!
    
    // Dependency Injection via constructor
    public APIGateway(RateLimiter limiter) {
        this.limiter = limiter;
    }
    
    // Or via setter (more flexible)
    public void setRateLimiter(RateLimiter limiter) {
        this.limiter = limiter;
    }
    
    public Response handleRequest(Request request) {
        if (limiter.allowRequest(request.getUserId())) {  // Don't care about implementation!
            return processRequest(request);
        }
        return new Response(429, "Too Many Requests");
    }
}

// Production usage - inject real limiter:
RateLimiter tokenBucket = new TokenBucketRateLimiter(100, 10);
APIGateway gateway = new APIGateway(tokenBucket);

// Later, switch algorithm at runtime:
gateway.setRateLimiter(new SlidingWindowRateLimiter(100, 60000));

// Test usage - inject mock limiter:
class MockRateLimiter implements RateLimiter {
    private boolean shouldAllow = true;
    
    @Override
    public boolean allowRequest(String key) {
        return shouldAllow;  // Controllable for testing
    }
    
    public void setShouldAllow(boolean allow) {
        this.shouldAllow = allow;
    }
}

MockRateLimiter mockLimiter = new MockRateLimiter();
APIGateway testGateway = new APIGateway(mockLimiter);

// Test rate limiting behavior:
mockLimiter.setShouldAllow(false);
Response response = testGateway.handleRequest(request);
assert response.getStatusCode() == 429;  // Predictable testing!
```

**Interview tip:** "APIGateway doesn't know if it's using Token Bucket or Sliding Window - it just calls `allowRequest()` on the interface. I can swap algorithms at runtime. For testing, I inject a mock limiter that returns predictable values, no need to hit real rate limiting logic."

---

## KEY TAKEAWAYS

### Design Patterns:
✅ **Strategy Pattern** - Different algorithms (Token Bucket, Sliding Window, etc.)
✅ **Factory Pattern** - Create rate limiters based on type
✅ **Singleton** - Could use for global limiter

### Algorithms:
✅ **Token Bucket** - Best general purpose (allows bursts)
✅ **Sliding Window** - Most accurate (no boundary issues)
✅ **Fixed Window** - Simplest, fastest (but has burst at boundaries)
✅ **Leaky Bucket** - Smooth traffic (no bursts allowed)

### SOLID Principles Applied:
✅ **Single Responsibility (SRP)** - RateLimiter enforces limits, Storage handles persistence, Metrics tracks stats
✅ **Open/Closed (OCP)** - Add new algorithms by creating new classes, zero changes to existing code
✅ **Liskov Substitution (LSP)** - All RateLimiter implementations are interchangeable
✅ **Interface Segregation (ISP)** - Separate interfaces for core limiting, tokens, persistence, observability
✅ **Dependency Inversion (DIP)** - APIGateway depends on RateLimiter interface, not concrete implementations

---

## COMMON MISTAKES TO AVOID

❌ Not thread-safe (use synchronized or concurrent collections)
❌ Memory leaks (clean up old entries)
❌ Not handling edge cases (window boundaries)
❌ Ignoring distributed scenarios
❌ Not considering clock skew in distributed systems

---

## REAL-WORLD APPLICATIONS

✅ **API Rate Limiting** - GitHub, Twitter APIs
✅ **Login Attempts** - Prevent brute force
✅ **DDoS Protection** - CloudFlare, AWS WAF
✅ **Resource Throttling** - Database connections
✅ **Cost Control** - Cloud API billing

---

**END OF RATE LIMITER GUIDE**

Covers throttling, quota management, and API protection!
