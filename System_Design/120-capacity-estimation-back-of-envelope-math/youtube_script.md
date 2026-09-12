# Capacity Estimation: Back-of-the-Envelope Math for System Design Interviews — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE

## HOOK (0:00–0:30)

Quick question. If I tell you a system has "100 million daily active users," can you tell me — in the next 60 seconds — whether that system needs one database or two hundred?

Most engineers can't. And that's exactly the moment interviewers are watching for, because here's the number that should scare you: a social app with 100 million users, each posting just twice a day with a 200 KB photo attached, generates 14.7 petabytes of storage a year. Petabytes. From "just" 100 million people posting a couple times a day.

If you didn't do that math before you opened your mouth about databases, you'd have designed something that falls over on day one — or something so over-engineered you'd never ship it.

[Screen cue: Big bold number "14.7 PB/year" smashing onto screen, then zooming out to reveal it came from "100M users × 2 posts/day × 200KB"]

## THE PROBLEM (0:30–2:00)

Here's the thing about system design interviews — and real system design at your job — nobody hands you a spec sheet. They hand you a business number. "100 million users." "500 million URLs a month." "Design something for Instagram scale." And your brain wants to jump straight to the fun part: "Oh, I'll use Kafka for the write path, Cassandra for storage, Redis for caching, CDN in front..." 

Stop. You just designed a system without knowing if it needs to survive 100 requests per second or 100,000 requests per second. Those are wildly different problems. A single well-tuned Postgres instance can handle 10,000 simple read queries a second all day long. If your actual peak load is 500 QPS, you just proposed sharding for a problem you don't have. If your actual peak load is 70,000 QPS, a single Postgres instance was never going to survive, no matter how well you tuned it.

This is the skill interviewers are actually testing when they throw out "100 million DAU" at the start of the round. Not whether you can do algebra — whether you instinctively convert a vague human-scale number into a concrete engineering decision: one database or a sharded cluster? Does the cache fit on one box or do I need a cluster? Is my bottleneck going to be storage, bandwidth, or raw compute? Skip this step, and you can know every pattern in the book — sharding, caching, CDNs, the works — and still design something that's either laughably over-built or quietly doomed to fall over the first time it sees real traffic.

[Screen cue: Split screen — left side shows a confused engineer jumping straight to "Kafka + Cassandra + Redis" with a big red question mark over an unlabeled "QPS = ???" box; right side shows the same engineer with a calculator and a clean funnel diagram]

## THE SOLUTION (2:00–5:00)

So here's the funnel. It's the same shape every single time, no matter what system you're designing.

Step one: start with what you're given, or a number you can reasonably assume — Daily Active Users. Let's say 100 million.

Step two: convert that into actions per day. State your assumption out loud — that's actually part of what interviewers want to hear. Let's say each user posts twice a day and reads their feed twenty times a day. That's 200 million writes a day, and 2 billion reads a day.

Step three: turn that into AVERAGE queries per second. There are 86,400 seconds in a day, so 200 million writes divided by 86,400 gives you roughly 2,315 average writes per second. 2 billion reads divided by 86,400 gives you roughly 23,150 average reads per second.

Step four — and this is the step everyone forgets — traffic is NOT evenly spread across 24 hours. Nobody's posting at 3 AM the same rate they post at 8 PM. So you apply a peak factor, typically 2 to 3x for normal daytime-skewed consumer traffic. That turns your 2,315 average writes into roughly 7,000 peak writes per second, and your 23,150 average reads into roughly 70,000 peak reads per second. THIS peak number — not the average — is the number your architecture actually has to survive.

Step five: storage. Take your per-event size, multiply by event count. If each post is 1 KB of metadata plus 200 KB of average media, that's 201 KB per post. 200 million posts a day times 201 KB gives you about 40.2 terabytes a day — which is 14.7 petabytes a year. That number tells you immediately: raw media does NOT belong in your primary database, it belongs in object storage, S3-style. And even just the 1 KB of metadata alone, stripped of media, adds up to 73 terabytes a year — meaning your metadata database needs sharding well before year three.

Step six: bandwidth. Peak QPS times average response size. 70,000 reads per second times 201 KB average response comes out to about 14 gigabytes per second. That number tells you a CDN in front of your media is not a nice-to-have, it's mandatory — no set of origin servers realistically serves 14 GB/s directly.

And there's one more calculation worth doing every time: does your "hot set" fit in cache? Say 20% of your 100 million users are active in any given hour — that's 20 million users. Each one's cached session data is about 2 KB. Multiply those together and your hot-set size is about 40 gigabytes. That fits comfortably in a modest Redis cluster — a handful of nodes at 8 to 16 GB each. Not a single box, but nowhere close to hundreds of nodes either. One calculation, and you know exactly how many Redis nodes to provision instead of guessing.

[Screen cue: Draw the funnel live — DAU box, arrow down to "actions/day," arrow down to "avg QPS," arrow down to "peak QPS (×2-3)," then branch off to "storage/day→year" and "bandwidth" boxes, with a side box for "cache hot-set size"]

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)

Let's talk about the traps, because these are exactly what separates a senior engineer from someone who memorized a system design checklist.

Trap number one: skipping estimation entirely. Jumping straight to "we'll use Kafka and Cassandra" without ever establishing whether this system needs to handle 100 QPS or 100,000 QPS. That's not confidence, that's a guess dressed up as an architecture.

Trap number two, and this one's sneaky — going too far the OTHER direction: false precision. Spending ten minutes deriving a number out to three significant figures when the interview only needed you to know "are we in the thousands, millions, or billions." Nobody needs you to compute 23,148.6 QPS. They need to know it's "about 23K, call it 70K at peak." Round numbers, clearly stated assumptions, sanity-checked against a reference point — that's the right level of rigor. Not a spreadsheet.

Trap number three, and this is a big one: getting your read-to-write ratio backwards. Here's the split that matters. A social feed system commonly has a reads-to-writes ratio of 100 to 1, sometimes even 1000 to 1 — which means your architecture should be optimizing aggressively for the READ path: caching, CDN, read replicas, precomputed feeds. But a payment or ledger system? That ratio is often close to 1 to 1, sometimes even write-heavy during settlement batches — which means you optimize for WRITE correctness and durability: write-ahead logs, idempotency keys, strong consistency, not raw read throughput. The common interview mistake is proposing heavy caching for a system that's actually write-dominated, or proposing complex write-optimized sharding for a system that's actually read-dominated and would be far better served by just adding read replicas and a cache. Same skillset, applied backwards, and it tanks the whole design.

Trap number four: not sanity-checking against known single-node limits. This is your safety net. A single well-provisioned Postgres or MySQL instance commonly handles low thousands up to 10,000-plus simple read QPS with proper indexing before you need read replicas or sharding at all. A single Redis instance commonly handles 50,000 to 100,000-plus GET/SET operations a second on modest hardware. So if your estimate comes out to 500 QPS, you probably don't need to shard — that would be over-engineering. But if your estimate says you need 2 million ops per second, now you know you need a whole cluster, not a config tweak on one box.

And while we're deep in the numbers — the latency cheat sheet every engineer should have memorized. An L1 cache reference is about 1 nanosecond. Main memory, about 100 nanoseconds. An SSD random read, about 100 microseconds. A round trip within the same data center, about half a millisecond. A Redis GET over the network, about 1 millisecond. A round trip across regions — say US to Europe — 100 to 150 milliseconds. Memory is roughly 100,000 times faster than a cross-region network round trip. That's not trivia — that's WHY you never put a synchronous cross-region call on a request's hot path if you can possibly avoid it.

[Screen cue: Side-by-side comparison table — "Social Feed: 100:1 to 1000:1 reads:writes → optimize READ (cache/CDN/replicas)" vs "Payment Ledger: ~1:1 or write-heavy → optimize WRITE (WAL/idempotency/consistency)." Below it, a latency bar chart from 1ns to 150ms on a log scale]

## REAL WORLD (8:00–9:30)

Let's ground this in real numbers you'd actually walk through in an interview.

Picture a URL shortener interview question: "500 million new URLs created per month, 100 to 1 read-to-write ratio." Walk the funnel: 500 million divided by 30 days divided by 86,400 seconds gives you roughly 193 average writes per second. Apply a 2 to 3x peak factor and you're at 500 to 600 peak writes per second. Apply the 100 to 1 ratio and you get 50,000 to 60,000 peak reads per second. That read number is the one that drives the whole design — 50,000-plus QPS on simple key lookups is well beyond what you'd want hitting a database directly, so a Redis cache in front, keyed by short-code, isn't optional, it's load-bearing. Meanwhile the database itself, at only ~600 writes per second, is comfortably within a single well-indexed instance — so sharding the write path here would be solving a problem you don't have. And storage? 500 bytes per record times 500 million a month is about 250 GB a month, roughly 3 TB a year — small enough that a single database with room to grow handles years of this. One estimation exercise, and you know exactly where to spend your design effort: read-path scaling, not database sharding.

Now think about how that same skill plays out at Indian scale. Picture a food-delivery platform like Swiggy during the 8 PM to 9 PM dinner rush — if a "normal" hour sees roughly 15,000 order-placement requests per second platform-wide, that rush hour alone can realistically spike traffic to 3 to 4x baseline, meaning your order-service and payment-gateway integration need to survive north of 50,000 QPS for that one-hour window, not the daily average — exactly the "average vs peak" distinction from earlier.

Or think about a UPI-style payments platform like PhonePe processing tens of millions of transactions a day. That's a read:write ratio close to 1:1, sometimes write-heavy during EOD reconciliation batches — meaning the entire design conversation shifts away from "how big should my cache be" toward "how do I guarantee exactly-once processing with idempotency keys and a durable write-ahead log," because a duplicated payment is a far worse failure than a slow read.

And picture an e-commerce flash sale like Flipkart's Big Billion Days — a normal day's 2 to 3x peak factor doesn't even come close; a flash-sale event can realistically push traffic to 10 to 20x normal peak in short bursts, which is exactly why that kind of event gets its own dedicated capacity planning exercise, months in advance, instead of relying on the everyday peak-factor assumption.

[Screen cue: Three company-style cards fading in one at a time — "Swiggy: 15K→50K+ QPS dinner rush," "PhonePe: ~1:1 read:write, idempotency + WAL over caching," "Flipkart Big Billion Days: 10-20x normal peak, dedicated capacity planning"]

## OUTRO + NEXT EPISODE (9:30–10:00)

So here's your takeaway: before you draw a single box in your next system design interview, run the funnel — DAU to actions per day, to average QPS, to peak QPS, to storage, to bandwidth, to cache size — and sanity-check every one of those numbers against "a single DB does about 10K QPS, a single Redis does 50 to 100K ops per second." That's the whole skill. Round numbers, stated assumptions, a gut check. Not a spreadsheet.

If this made your next interview a little less scary, hit subscribe — because next episode, we're taking the read-heavy design this video just justified and going deep on fan-out: write versus read fan-out for feed systems, and exactly when precomputing a feed for every follower stops being smart and starts being a nightmare. See you there.

[Screen cue: Subscribe button animation, end card teasing "NEXT: Fan-Out Write vs Fan-Out Read"]
