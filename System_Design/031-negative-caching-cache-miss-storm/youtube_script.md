# Negative Caching & Cache Miss Storm — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE | Episode: 31

## HOOK (0:00–0:30)

Picture this: your URL shortener is running fine. Then a spam bot shows up and fires one million requests — "zzz999", "abc000", "xyz123" — random short codes that don't exist. Not one of them is real.

Here's the shocking part: your cache is completely useless against this. Why? Because your cache only stores things that *exist*. It has never been told how to remember "this doesn't exist." So every single one of those million requests skips the cache, hits your database, gets a "not found," and the database just... collapses. At a thousand requests per second, your DB hits 100% CPU — and now your *real* users, the ones looking up URLs that actually exist, start timing out too.

[Screen cue: split-screen animation — left side "Bot: 1,000,000 requests" with a counter spinning up, right side a database gauge needle slamming into the red zone]

One missing feature took down a whole system. Today we fix that with negative caching.

## THE PROBLEM (0:30–2:00)

So think about it this way: a normal cache is a one-way street. Something exists in the DB, you fetch it, you cache it, next time it's fast. But what happens when the answer is "no, this doesn't exist"? Your code says "cache miss, go check the DB" — every single time, for that same non-existent key, forever. There's no cache entry to hit because you never created one for "not found."

This isn't some rare edge case. Any API where a user — or a bot, or a buggy client — can supply an arbitrary ID is exposed. User IDs, product IDs, order IDs, usernames, short codes. Someone enumerates them, guesses wrong 99% of the time, and every wrong guess is a full round trip to your database: acquire locks, scan indexes, come back with nothing.

[Screen cue: diagram — "Request 1 → Cache MISS → DB query → 'not found' → 404" repeated in a loop a dozen times, all pointing at the same key "zzz999", with a counter ticking up to 1,000,000 and the DB icon flashing red]

At scale this is brutal. Each query might only cost 1 to 5 milliseconds of CPU — sounds tiny — but multiply that by a million and you've burned real DB capacity for zero business value. Meanwhile your actual paying users' queries are stuck in line behind all this garbage traffic.

## THE SOLUTION (2:00–5:00)

Now watch what happens when we add negative caching. The idea is stupidly simple once you hear it: cache the absence. Cache the "not found" answer itself.

First request for "zzz999" — cache miss, go to the DB, DB says not found. Instead of just returning 404 and walking away, we store a sentinel value — something like the string `__NULL__` — in Redis, under that same key, with a short TTL, say 60 seconds. Now, request number two for "zzz999" — and remember, bots repeat the same guesses constantly — hits the cache, sees that sentinel, and returns 404 immediately. Sub-millisecond. Zero database queries.

[Screen cue: before/after diagram — "Request 2 through 1,000,000 → Cache HIT (NULL_SENTINEL) → return 404 → DB: 0 queries"]

One DB query total, for a million requests. That's the entire trick.

But here's where it gets really good — we don't stop at one layer. Production systems use three layers of defense stacked together.

Layer one: a Bloom filter. This is a probabilistic data structure that answers one question fast: "is this key definitely NOT in my dataset?" Every time you create a real short code, you add it to the Bloom filter. When "zzz999" comes in and the Bloom filter says "definitely never created," you return 404 immediately — no cache lookup, no DB lookup, nothing. For 10 million codes, a Bloom filter costs about 12 megabytes of memory and gives you roughly a 1% false-positive rate. That single layer eliminates 99% of this garbage traffic at near-zero cost.

Layer two is our negative cache, which we just covered — it catches the 1% that slip past the Bloom filter as false positives.

Layer three: API gateway rate limiting. Cap requests per key — say, no more than 10 requests per 60 seconds for the same code — and block the rest before they even reach your application.

[Screen cue: draw the three-layer funnel live — Bot Attack at top → API Gateway Rate Limiter → Bloom Filter → Redis Negative Cache → Database at the bottom, with request counts shrinking at each layer: 1,000,000 → ~10,000 → ~100 → ~1]

Stack these three together and DB load from non-existent keys drops from a million queries to essentially zero.

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)

Okay, this is the part where teams get burned. Let's go through the traps one at a time.

**Trap one: forgetting to invalidate on write.** This is the big one. Say a user tries to register as "user123." At time zero, "user123" doesn't exist, so you cache NULL with a 60-second TTL. At time 30 seconds, that same user successfully registers — the DB write succeeds. At time 31 seconds, someone — maybe the same user refreshing the page — checks if "user123" exists. Your cache still has the NULL entry! It returns 404. The user thinks their signup failed, tries again, gets a "username already taken" error, gets confused, and files a support ticket. The fix: your write path has to explicitly delete the negative cache entry the moment you insert the row, then set the positive cache. Insert into DB, delete the negative key, set the positive key, update the Bloom filter — in that order, every time.

[Screen cue: timeline diagram — t=0 cache NULL, t=30 user registers, t=31 stale cache still returns 404, red "X" over the missing invalidation step]

**Trap two: never setting negative TTL to infinite.** If you cache "not found" forever, and that key later becomes real, your users get a permanent phantom 404. Rule of thumb: negative TTL should equal how long you're comfortable serving a stale "not found" after a key might actually get created. For user signups, that's 30 to 60 seconds. For a static keyspace like discontinued product IDs, you can go much longer — an hour or more — because nothing's going to un-discontinue that product.

**Trap three: negative caching doesn't stop infinite unique-key attacks.** If a bot generates a brand-new random key on every single request — never repeating — your negative cache fills up with millions of one-time entries, and worse, every single one of those still costs you one DB lookup on the first miss. Negative caching only helps when the *same* key is requested repeatedly. For truly random, never-repeating keys, you need rate limiting at the ingress — by IP, not by key — plus the Bloom filter doing the heavy lifting on cost-per-request.

**Trap four: cache stampede on a popular non-existent key.** Imagine a single non-existent key suddenly gets hit by a thousand concurrent requests before the very first one finishes writing the negative cache entry. All thousand see a cache miss simultaneously and all thousand hit the DB at once. The fix is the same one used for regular cache stampedes — a distributed lock so only one request goes to the DB, or probabilistic early refresh.

**Trap five: data that changes too rapidly.** If keys get created and deleted multiple times a minute, negative caching barely helps — you'd need a TTL under 5 seconds to stay safe, and at that point the protection is marginal. Negative caching shines when "not found" is a *stable* answer for at least the TTL window.

[Screen cue: comparison table — "Cache Null vs No Entry" — Option A: sentinel value (recommended, clear intent), Option B: empty string (ambiguous, breaks on legit empty values), Option C: separate notfound: keyspace (clean but double lookup)]

And one more number worth remembering: a negative cache entry costs about 90 bytes — 20 bytes for the key, 10 for the sentinel value, 60 bytes of Redis overhead. A million of those is 90 megabytes. Compare that to the cost of *not* caching: a million DB queries at 2 milliseconds each is 2,000 CPU-seconds — over 33 CPU-minutes — completely wasted. 90 megabytes of RAM against 33 minutes of burned CPU is an easy trade every single time.

## REAL WORLD (8:00–9:30)

Let's ground this in systems you actually use.

Think about a platform like **Swiggy** during a flash sale — bots and scrapers constantly probe for coupon codes and promo IDs that don't exist, hammering the same handful of invalid codes over and over trying to find one that works. Without negative caching on that lookup, every failed guess is a full database round trip; with it, after the first miss, every repeat guess for the same invalid code resolves in under a millisecond from Redis.

Or take a username-lookup flow like you'd see on a social platform — something **Flipkart** or any e-commerce player with social/seller-handle features has to deal with. Bot enumeration constantly probes usernames like "@testuser1," "@testuser2," and so on, checking availability. A 30-second negative cache on "does this username exist" absorbs that entire enumeration pattern without the user table ever seeing repeat traffic for the same guess.

And for a large product catalog — like **Paytm's** marketplace or any big e-commerce catalog during a sale event — discontinued or removed product IDs get probed constantly by old bookmarked links, scrapers, and stale mobile app caches. Caching "product ID 12345 = NOT_FOUND" for 5 to 60 minutes means the product table doesn't get flooded by traffic for SKUs that no longer exist — which matters most exactly when your DB is already under the heaviest load, during a big sale.

[Screen cue: three company-style cards — "Swiggy: promo code probing" / "Flipkart-style: username enumeration, 30s TTL" / "Paytm-style: discontinued SKU lookups, 5-60min TTL" — each with a small database icon showing near-zero query count]

The pattern is the same everywhere: whenever a user-supplied ID can miss, and misses repeat, negative caching turns a database-hammering problem into a 90-byte Redis entry.

## OUTRO + NEXT EPISODE (9:30–10:00)

So remember the one-liner: cache the "not found" answer with a short TTL — a negative cache entry costs about 100 bytes but saves a full database round trip on every repeat miss.

If this saved you from a future 3 AM page, hit subscribe — we're going through one system design pattern per episode, all the ones that actually show up in interviews and in production incidents.

Next episode, we're moving from "is this key even real" to "is this *node* even alive" — episode 32, heartbeat detection, and how distributed systems tell the difference between a node that's dead and one that's just slow. That distinction breaks more systems than people expect. See you there.

[Screen cue: end card — "Episode 32: Heartbeat Detection — Dead vs Slow Node" with subscribe button animation]
