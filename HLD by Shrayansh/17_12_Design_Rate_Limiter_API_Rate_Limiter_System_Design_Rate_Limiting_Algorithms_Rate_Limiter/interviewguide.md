# Interview Guide: Design a Rate Limiter

## 🗣️ The Interview Scenario

> "We're seeing an attacker fire tens of thousands of requests per second at one of our public POST endpoints, and it's starting to degrade the service for legitimate users. Design a rate limiter to sit in front of this API. Walk me through at least two different algorithms, their trade-offs, and how you'd make the rate limiter itself work correctly when it's deployed across many servers handling requests in parallel."

Interviewers ask this because it's a genuinely layered problem: pick an algorithm, understand its specific failure mode, and then solve the *distributed systems* problem of keeping counters correct across a fleet — most candidates only prepare the algorithms and skip that last, most important part.

## 🏗️ Architect's Explanation (For a New Developer)

Think of a rate limiter like a **bouncer with a fixed number of wristbands** at a club entrance. The bouncer's job isn't to be mean — it's to protect the venue (your server's RAM and disk, which are always limited) from being crushed by more people than it can safely hold. When an attacker tries to rush the door with thousands of fake guests per second, without a bouncer, the venue becomes so overcrowded that even the genuine guests who showed up with real tickets get turned away — that's the actual harm a rate limiter prevents: **it's not really about stopping the attacker, it's about protecting genuine users from an attacker's side effects.**

There are several different "bouncer strategies" (algorithms), each with a different personality: some hand out a fixed number of wristbands that slowly refill (Token Bucket), some let people in only at a steady drip regardless of how many are waiting (Leaky Bucket), some just count heads in fixed 5-minute blocks (Fixed Window Counter), and some keep a precise rolling log of exactly who entered in the last 60 seconds no matter what clock time it is (Sliding Window Log/Counter). The subtlety that trips people up isn't picking an algorithm — it's realizing that if you have **multiple bouncers (servers) sharing one guest list (rate limit counters)**, they need a fast, shared, atomic way to check and update that list, or two bouncers can both let in "the last wristband" at the same time.

## 📊 Visualize It

**Token Bucket mechanics (capacity 4, one refill worker):**

```
Bucket capacity: 4 tokens
                                                   Refill worker adds tokens
[●][●][●][●]  <- full bucket                       back on a timer (e.g. every
                                                     1 minute), never exceeding
Request arrives -> is a token present?              the bucket's capacity
   YES -> consume 1 token, process request           (extra tokens are discarded
   NO  -> reject request, HTTP 429                    as overflow)
```

**Fixed Window Counter's boundary problem (why it can double the allowed rate):**

```
Rule: max 3 requests per 5-minute window

Window A [0:00 - 0:05):  req, req, req   (3 allowed, at the END of the window)
Window B [0:05 - 0:10):  req, req, req   (3 allowed, at the START of next window)

-> In the actual ~5-minute span straddling the boundary (e.g. 0:03 - 0:08),
   as many as 6 requests can slip through, DOUBLE the intended limit,
   because the counters reset independently at the fixed boundary.
```

## 🔧 Deep Dive: How It Actually Works

### 1. The problem being solved
- An **attacker sends unwanted requests** to a server — thousands, even lakhs (hundreds of thousands), per second.
- The server has **limited resources** (RAM, disk space) — everything is finite.
- When those resources are consumed by the attack, the **server goes down**.
- The real damage: **genuine users' requests get declined** once the server is down or overloaded — this is framed explicitly as a denial-of-service (DoS) style attack, and the rate limiter's job is to prevent exactly this outcome.

### 2. The five algorithms

**Token Bucket**
- The bucket has a fixed **capacity** — the maximum number of tokens it can hold (example used: 4).
- A **refill worker** adds tokens back after a configured time interval (example: 1 token added back after 1 minute; the config is described as driven by a **config file**, so these values — capacity, refill rate — can be changed dynamically without redeploying code).
- Request flow: when a request arrives, check — **is a token present?** If yes, the request **consumes one token** and is processed. If the token count is zero, the request is **rejected**.
- If the refill worker tries to add a token but the bucket is already at capacity, the extra token **overflows and is discarded** — capacity is a hard ceiling.
- Practically implementable with a simple **counter**: e.g., a rule like *"3 tokens per user per API, per minute"* — the counter decrements per request and gets refilled back up toward capacity by the periodic refill logic, with any refill beyond capacity simply discarded.

**Leaky Bucket**
- Also a fixed-capacity bucket, but modeling the opposite direction: requests arrive at an **irregular** rate (bursty — sometimes more, sometimes less), while the bucket **processes ("leaks") requests out at a constant, fixed rate**.
- If the incoming rate exceeds the constant processing rate, the bucket **overflows** and the excess requests are **rejected** (HTTP 429).
- Implemented via a **queue** — incoming requests queue up and are drained at the fixed rate.
- **Advantage:** guarantees a smooth, constant output rate — useful when downstream systems specifically need traffic evened out (the example given: an application like Amazon during a period where traffic is naturally lower, e.g. daytime vs. evening/night, where a constant processing rate is an acceptable/desired trade-off).
- **Disadvantage:** it does not adapt to legitimately bursty valid traffic — new (fresher) requests get stuck waiting behind older queued ones, adding latency; this makes it a poor fit when the specific application legitimately needs to absorb bursts (the walkthrough explicitly frames this as **use-case dependent** — some applications need a constant rate and are fine with this trade-off, others aren't).

**Fixed Window Counter**
- Time is divided into **fixed windows** (example: 5 minutes), each with its own **counter** and a configurable limit (example: 3 requests per window; both the count limit — e.g. changeable from 3→4→5 — and the window size — e.g. changeable from 5 minutes→2 minutes — are described as config-driven).
- Very **simple and intuitive** to implement: increment the counter per request within the window; reset it when a new window starts.
- **Disadvantage (the boundary problem):** because windows are strictly fixed and independent, requests clustering right around a window boundary can result in **up to double the intended rate** slipping through in the real time span straddling that boundary (e.g., a limit of 3 per 5 minutes could allow 6 requests to land within an actual ~5-minute span that happens to straddle two windows).

**Sliding Window Log**
- Solves the fixed-window boundary problem by **not using fixed calendar windows at all** — instead, the window continuously **slides** with time, and instead of a simple counter, the algorithm keeps a **log of individual request timestamps**.
- Flow: for each incoming request, check how many previously logged timestamps fall within the trailing window (e.g., last 1 minute). If the count is under the limit (example: 3/minute), the request is **allowed and its timestamp is logged**; otherwise it is **denied**, but the attempt is still tracked/logged in the walkthrough's description.
- As the window slides forward, timestamps that fall outside the trailing window are **dropped from the front** of the log.
- **Advantage:** precisely fixes the fixed-window boundary problem — there's no artificial reset point where double-counting can sneak in.
- **Disadvantage:** it's **memory-heavy** — a timestamp entry must be stored for essentially every request (including denied ones), which gets expensive at high request volume/scale.

**Sliding Window Counter**
- A **hybrid** of Fixed Window Counter (cheap, low memory) and Sliding Window Log (accurate, no boundary bug) — combining the low memory footprint of counters with sliding-window accuracy.
- Mechanism: maintain counts in small fixed sub-windows (e.g., 10-second buckets) within a larger rolling window (e.g., 60 seconds/1 minute). To estimate the current effective count, use a **weighted formula** combining the previous window's count (weighted by how much of it still overlaps the current trailing window) with the current window's actual count — e.g., if the overlap portion is 10 seconds out of a 60-second window, the previous window's count is weighted by `10/60` and added to the current window's actual count, then compared against the limit (example: "less than 5") to decide allow/deny.
- This gives an **approximate but very close** answer to the true sliding-window count, at a fraction of the memory cost of logging every timestamp individually.

### 3. Configuration and architecture
- Rate rules (e.g., "3 requests per minute per user per API") are stored as **configuration** — not hardcoded — and are described as changing very **infrequently**, so it's efficient to **load the config into cache** when the host application starts, and read the active rate-limiting rules from that cache rather than hitting a config store on every request.
- **High-level flow:** Client request → **API Gateway** (hosting the rate limiter logic) → checks against the algorithm/config → either forwards the request to the backend **server**, or returns **HTTP 429** directly.

### 4. The distributed-correctness problem (the real hard part)
- The rate limiter needs somewhere to store and update counters/tokens that is **shared across all instances** handling requests, since clients and parallel requests can land on different rate-limiter/API-gateway instances.
- A **centralized data store** is needed so that everyone accessing it can maintain **atomicity** for the bucket/counter operations (e.g., decrementing a token count) even under concurrent/parallel requests.
- **Redis** is the answer given: Redis operations are described as being **much faster than a database** (milliseconds vs. minutes-scale synchronization overhead implied for cross-cluster DB sync), and Redis already has **existing solutions for bringing atomicity** to this kind of counter operation — so teams don't need to build atomicity from scratch. This is explicitly framed as "a bit loose" compared to a hypothetical perfectly centralized single-threaded counter, but is considered a solid, pragmatic trade-off given the massive latency win.

## 🔥 Real Production Incident & Fix

**What broke:** A public API rate-limited to "100 requests/minute per API key" started allowing a single malicious key to sustain roughly 3-4x that rate during a coordinated abuse campaign, without tripping any 429 responses in the logs for that key — while the backend service behind it still showed clear signs of overload (elevated CPU, growing queue depth).

**How it was detected/diagnosed:** On-call cross-referenced access logs filtered by API key against the rate limiter's own decision logs and found the discrepancy: the *backend* was seeing far more traffic for that key than the rate limiter's 429 count would suggest was possible. Infrastructure metrics showed the API Gateway was horizontally scaled across multiple instances, and — critically — each instance was maintaining its own **local, in-process counter** for the token bucket rather than reading/writing a shared store. The attacker's traffic was, likely deliberately, load-balanced across multiple gateway instances, and each instance independently believed the key still had its full quota of tokens available.

**Root cause:** The rate limiter's counters lived in local process memory per API Gateway instance instead of a shared, atomic, centralized store. This is exactly the gap the design calls out: without a centralized data store providing atomicity across parallel requests (potentially landing on different machines), each instance's view of "how many requests has this key made" is incomplete and effectively multiplies the true allowed rate by the number of gateway instances the attacker's traffic happens to spread across.

**The fix:** Counters were migrated to a **Redis-backed** shared store, using Redis's atomic increment/decrement primitives so that every API Gateway instance reads and writes the *same* counter state for a given key, regardless of which instance a particular request lands on. Post-fix, the same abusive key was correctly capped at the configured 100 requests/minute across the entire fleet, and 429 responses appeared in logs at the expected volume.

```
BEFORE (per-instance local counters):          AFTER (shared Redis-backed counters):

Gateway A: local counter for KeyX (0/100)      Gateway A --\
Gateway B: local counter for KeyX (0/100)      Gateway B ---> shared Redis counter
Gateway C: local counter for KeyX (0/100)      Gateway C --/    for KeyX (atomic)
  -> attacker effectively gets 300/min           -> attacker correctly capped at 100/min
     instead of the intended 100/min               no matter which gateway is hit
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Why would you choose Token Bucket over Leaky Bucket for a typical public API?**
Token Bucket naturally allows legitimate bursts of traffic (as long as tokens are available) while still enforcing a long-run average rate via the refill mechanism, which fits how real client traffic behaves. Leaky Bucket enforces a strictly constant output rate regardless of burstiness, which is the right choice only when the downstream system specifically needs smoothed, constant-rate traffic (e.g., protecting a fixed-capacity resource that can't handle spikes at all) — otherwise it adds unnecessary latency to legitimate bursty clients.

**Q2: How do you fix the Fixed Window Counter's boundary problem without paying the full memory cost of a Sliding Window Log?**
Use the **Sliding Window Counter** hybrid: keep cheap per-sub-window counters (e.g., 10-second buckets) instead of a full timestamp log, and estimate the true rolling-window count with a weighted combination of the previous sub-window's count (weighted by its overlap with the current trailing window) plus the current sub-window's count. This gets you very close to sliding-window accuracy at counter-level memory cost.

**Q3: Why use Redis instead of a traditional database for storing rate-limit counters in a distributed setup?**
Redis operations are dramatically faster (millisecond-scale) than coordinating counters through a database across a distributed cluster, and Redis provides ready-made atomic primitives (like atomic increment/decrement) that let multiple rate-limiter/gateway instances safely update the same counter concurrently without building custom distributed-locking logic from scratch.

**Q4: How would you rate-limit per-user AND per-API at the same time?**
Structure the config/counter keys as a composite of both dimensions — e.g., a Redis key like `ratelimit:{user_id}:{api_name}` — so each user/API pair gets its own independent bucket or window counter, with rules (limit, window size) still driven by the same config file described in the design, just keyed more specifically.

**Q5: What HTTP status code and response details should a rate-limited request receive?**
The design explicitly uses **HTTP 429 (Too Many Requests)** when a request is denied by any of the algorithms. Beyond the status code, it's standard practice to include a `Retry-After` header (and often `X-RateLimit-Limit` / `X-RateLimit-Remaining` headers) so clients know how long to back off before retrying, rather than immediately hammering the API again.

**Q6: How would this design work in a multi-region deployment where Redis is region-local?**
If Redis is deployed per-region rather than globally, each region's rate limiter would only see traffic that lands in that region, effectively multiplying a user's true global rate limit by the number of regions their traffic spreads across — the same failure mode as the local-in-process-counter incident above, just at a regional rather than per-instance scale. This needs either a globally-replicated/cross-region-aware counter store, or accepting a looser global bound (e.g., dividing the global limit across regions) as an explicit trade-off.

## 🔑 Key Takeaway

Say this out loud in the interview: **"Picking the algorithm (Token Bucket, Leaky Bucket, Fixed/Sliding Window) is the easy half of this problem — the half that actually matters in production is making sure the counters are atomic and shared (typically via Redis) across every instance of your rate limiter, otherwise a distributed deployment silently multiplies the limit you thought you'd configured."**
