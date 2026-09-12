# Cache Stampede & Thundering Herd — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE | Episode: 30

## HOOK (0:00–0:30)

Taylor Swift tickets go on sale at midnight. A hundred thousand fans are hammering refresh on the homepage. The banner that says "TICKETS ON SALE NOW" is cached — for good reason, five minutes, to save the database. But somebody set that cache to expire at exactly 12:00:00 AM. The literal worst possible second.

The cache dies. All hundred thousand requests hit a miss at the same instant. All hundred thousand fire the same query at the database. The database — which was handling this fine ten seconds ago — falls over in under a second.

Tickets don't sell. Fans see error pages. And the thing that killed the database wasn't the traffic. It was the cache. The exact thing you built to protect the database became the weapon that killed it.

This is called a cache stampede, or a thundering herd. And by the end of this video you'll know three different ways engineers at scale actually prevent this — and why picking the wrong one can be just as bad as picking none.

[Screen cue: Countdown clock hitting 00:00, then a red "500 Internal Server Error" flooding across a grid of 100,000 user icons, all pointing to one small database icon that's on fire.]

## THE PROBLEM (0:30–2:00)

Okay, let's slow this down and think about it plainly.

Caches exist for one job: keep expensive computation out of the hot path. Your leaderboard, your trending list, your product page — these are expensive to compute from the database, so you compute it once, stick it in Redis, and every request for the next hour just reads that cached value. Cheap, fast, done.

But a cache entry doesn't live forever. It has a TTL — a time to live. And here's the part everyone glosses over: when that TTL hits zero, the cache doesn't gracefully degrade. It just... disappears. Gone. Null.

Now think about what happens if you have real traffic — not one user, but fifty thousand concurrent users — and they all ask for that same key in the same second that it expires. Every single one of them does `cache.get(key)`, gets `null`, and every single one of them independently decides "guess I'll go compute this myself" and fires a query at the database.

Here's the trap: your system is most fragile exactly when it's most popular. A cache miss at 2 AM with ten users on your site is a non-event — the DB barely notices one extra query. But a cache miss at your peak traffic moment, the exact second everyone's looking at the same thing, is fatal. The database that was cruising at 5% CPU is now getting 50,000 identical, expensive queries in under a second. CPU spikes to 100%. Connection pool exhausts. Every one of those users gets a timeout or a 500.

This isn't theoretical, by the way. Reddit has gone down from trending-post cache expiry storms. Facebook wrote an entire engineering paper about thundering herd problems at Memcached scale. Every flash sale, every ticket drop, every sneaker launch — these are all stampede risk moments by design, because that's exactly when a popular cache key is most likely to expire under peak load.

[Screen cue: Split-screen diagram — left side shows "T=0:00, cache populated, 1000 req/s, all served from cache, DB idle." Right side shows "T=1:00:00, cache expires, 50,000 requests arrive simultaneously, all miss, all hit DB, DB CPU bar shooting to 100%."]

## THE SOLUTION (2:00–5:00)

So how do you actually stop fifty thousand requests from all deciding to hit the database at once? There are three real patterns here, and each one trades off differently.

**Solution one: the mutex lock.** This is the simplest idea — only let ONE request recompute the value; make everyone else wait for it. Here's how it plays out. Cache expires. Request one comes in, sees a miss, and tries to grab a lock in Redis using `SET key value NX EX 30` — set-if-not-exists with a 30 second expiry. Request one gets the lock. It goes and queries the database, gets the fresh leaderboard, writes it back to cache, and releases the lock. Meanwhile, requests two through forty-nine-thousand-nine-hundred-ninety-nine all try to grab that same lock and fail, because request one already has it. So they sleep — say 100 milliseconds — and then retry the cache read. By then, request one has finished and populated the cache, so they get a hit.

Net result: the database gets exactly one query instead of fifty thousand. That's the win. The cost — and this matters — is that every single one of those 49,999 requests now has an extra 100 to 200 milliseconds of latency bolted on. And if request one crashes mid-query before releasing the lock? Everyone's stuck waiting until that lock's own TTL expires. That's why you always put a TTL on the lock itself, and why you use a unique UUID as the lock value with a Lua script for the release — so you're only ever releasing a lock you actually own, never someone else's.

**Solution two: probabilistic early expiry**, sometimes called PER. This one's clever. Instead of waiting for the TTL to hit zero and then reacting, you proactively refresh the cache before it expires — and you use randomness to decide when, so you don't get a coordinated stampede of "early" refreshes either. Every cache entry stores its value plus its creation time. On every read, you calculate: how much time is left before expiry? Then you roll a probabilistic formula — negative delta times beta times the log of a random number — and if that number is bigger than the remaining TTL, this particular request triggers an early recompute in the background. 

Here's the intuition: early in the TTL's life, almost nobody triggers early recompute. As you get closer to actual expiry, the odds climb — one in five hundred, then one in two hundred, then one in fifty. By the time you'd have hit the real expiry, the cache has almost certainly already been quietly refreshed by some earlier request, seconds before the deadline. The stampede moment never actually arrives, because the cache never actually goes to zero under load. With a one-hour TTL, you end up with one or two DB queries per hour, spread out, instead of fifty thousand in the same second.

**Solution three: stale-while-revalidate**, the two-TTL approach. This is probably the most user-friendly of the three, if you can tolerate a little staleness. You keep two timers on each entry: a soft TTL — say 5 minutes, meaning "still fresh" — and a hard TTL — say 10 minutes, meaning "must be thrown away." Inside the fresh window, everyone just gets the cached value instantly. Once you cross the soft TTL but you're still under the hard TTL, something interesting happens: the very first request that lands in that window gets served the stale value immediately — no waiting — AND it kicks off a single background async job to refresh the cache. Every other request in that same window also just gets the stale value instantly, zero added latency. Once the background job finishes, the cache is fresh again. Only if the hard TTL is somehow crossed — background refresh failed, whatever — do you fall back to a synchronous recompute.

The beauty here: nobody waits. Ever. Worst case, a user sees data that's up to five minutes old, but they never see a spinner, never see a timeout, and the database only gets one query per refresh cycle no matter how many concurrent users you have.

[Screen cue: Live-draw a timeline for stale-while-revalidate — a green "fresh zone" bar from 0 to 5 minutes, a yellow "stale but valid, serve immediately + async refresh" bar from 5 to 10 minutes, and a red "hard cutoff, synchronous recompute" mark at 10 minutes.]

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)

Let's talk about where teams mess this up, because I've seen all of these.

Trap number one: picking mutex lock for a high-traffic, latency-sensitive endpoint. Mutex lock is genuinely the simplest to implement, and for low-traffic services it's totally fine. But if you've got 50,000 concurrent users on that leaderboard, you've just decided that 49,999 of them are going to eat an extra 100-plus milliseconds of latency, every single time that cache expires. That adds up, and on a latency-sensitive endpoint that's a real user experience regression you're choosing to accept without realizing it.

Trap number two: forgetting the lock TTL. If your mutex lock doesn't have its own expiry and the process holding it crashes — maybe it OOMs, maybe the pod gets rescheduled — that lock never releases. Now every other request is stuck retrying forever, waiting for a lock that will never be freed. This is a full outage caused by your own safety mechanism. Always put a TTL on the lock — 30 seconds is typical — so the system self-heals even in the crash case.

Trap number three, closely related: releasing a lock you don't own. If request one's lock TTL expires because it took too long, and meanwhile request two comes in, times out waiting, and gets its own lock — and THEN request one finally finishes and blindly does a DEL on the lock key — it just deleted request two's lock. Now you've got two requests both thinking they own the recompute. That's why the release has to be a Lua script that checks "is this still MY unique UUID?" before deleting. Atomic check-and-delete, not just delete.

Trap number four: synchronized TTLs across multiple keys. Say you've got ten different leaderboards — regional, global, by game type — and you set every single one of them to expire at exactly 3600 seconds from creation. If they were all created around the same time, guess what — they all expire at the same time too. Now you've built ten stampedes instead of one. The fix is embarrassingly simple and constantly forgotten: TTL jitter. Instead of a flat 3600 seconds, you do 3600 plus a random number between 0 and 300. Spreads the expiries out so they don't collide.

Trap number five: using probabilistic early expiry when freshness is non-negotiable, without understanding the tradeoff — actually no, PER's tradeoff is the opposite direction: it's excellent for freshness, since it refreshes ahead of expiry with no stale window at all. The real trap here is using stale-while-revalidate for data where staleness is actually unacceptable — a financial leaderboard, a live price, a live score — because SWR by definition serves old data on purpose. If your business can't tolerate showing "yesterday's rank," don't reach for the two-TTL approach; you want PER instead, precisely because it eliminates the stale window entirely by getting ahead of the expiry.

Trap number six: treating a predictable spike like an unpredictable one. If you already KNOW a product launch or a ticket sale starts at a specific time — and you almost always do — don't rely purely on reactive mechanisms like mutex or PER. Pre-warm the cache. Run a scheduled job 60 seconds before the known event time that proactively computes and populates the cache, so the expiry moment never coincides with the traffic spike in the first place. This is the one case where you get to cheat — you know the future, so use it.

[Screen cue: Comparison table on screen — rows: Mutex Lock, Probabilistic Early Expiry, Stale-While-Revalidate, Pre-Warming, TTL Jitter. Columns: Best for, DB load, Added latency, Staleness.]

Here's that comparison, spelled out:

Mutex Lock — best for low traffic, simple data. DB load: exactly one query. Added latency: yes, for every non-lock-holder, roughly 100 to 200 milliseconds. Staleness: none.

Probabilistic Early Expiry — best for high traffic where freshness is critical, like live prices. DB load: one to two queries per cycle, spread out. Added latency: none. Staleness: effectively none, because it refreshes ahead of time.

Stale-While-Revalidate — best for high traffic where some staleness is tolerable, like trending feeds or leaderboards. DB load: one query per refresh cycle. Added latency: none, ever. Staleness: bounded by your soft TTL, so a few minutes typically.

Pre-Warming — best for predictable spikes, scheduled sales and launches. DB load: however many keys you're warming, done ahead of time. Added latency: none for users. Staleness: none, if timed correctly.

TTL Jitter — not a standalone solution, it's a multiplier you apply on top of everything else, to stop multiple keys from expiring in sync.

## REAL WORLD (8:00–9:30)

Let's ground this in scale, Indian tech companies specifically.

Think about Flipkart during a Big Billion Days sale, or Swiggy during an IPL match when everyone's ordering food at halftime simultaneously. Both of these are the same pattern as the ticket-sale example — a massive number of concurrent users hitting the same cached resource, like a product page or a restaurant listing, at the same coordinated moment. For Flipkart's product detail pages during peak sale hours, you're realistically talking tens of thousands of concurrent reads per second on the top SKUs. A naive TTL expiry there without mutex protection or pre-warming would mean tens of thousands of identical, expensive product-pricing queries slamming into the database in the same second — exactly the mechanism we walked through with the leaderboard.

Now think about Paytm or PhonePe around a specific timed event — a flash cashback offer that goes live at a specific second, or a scratch-card campaign announcement. That's a textbook pre-warming scenario: you know the exact second the traffic spike happens, so you populate the cache ahead of time rather than letting fifty thousand users discover a cold cache at the worst possible instant.

And for something like Zomato's "trending restaurants near you" — that's much closer to the Reddit trending-post example from earlier. It's the kind of data where a few minutes of staleness genuinely doesn't matter to the end user, so stale-while-revalidate is the natural fit: users always get an instant response, and the backend refreshes quietly in the background every five minutes or so, without ever making the database eat a traffic spike.

The common thread across every one of these companies: the failure mode is never "too much traffic." Modern databases and caches can handle massive scale. The failure mode is specifically "too much SIMULTANEOUS identical traffic hitting the database at once because the cache protecting it disappeared at exactly the wrong second." That's the entire disease this whole video has been about.

[Screen cue: Three logos on screen in sequence — Flipkart with "50K+ concurrent reads/sec on peak SKUs," Paytm/PhonePe with "flash offer goes live at :00:00 — pre-warm 60s before," Zomato with "trending list, 5-min staleness tolerated, SWR."]

## OUTRO + NEXT EPISODE (9:30–10:00)

So next time someone asks you in an interview, "your cache expires and fifty thousand users hit it at once, what do you do" — you've now got three real answers, not one. Mutex lock if it's simple and low-traffic. Stale-while-revalidate if users can tolerate a few minutes of staleness. Probabilistic early expiry if freshness is non-negotiable. And pre-warming plus TTL jitter layered on top of any of them, always.

If this saved you from a future 3 AM page, hit subscribe — this is episode 30 in a full system design series building toward interview-ready mastery, one failure mode at a time.

Next episode, we're staying right next door to this problem: episode 31, negative caching and the cache-miss storm — what happens when the thing everyone's asking for doesn't even exist in your database, and why that can be just as dangerous as a stampede on data that does. See you there.

[Screen cue: End card — "Episode 31: Negative Caching & Cache-Miss Storm" with subscribe button animation and channel logo.]
