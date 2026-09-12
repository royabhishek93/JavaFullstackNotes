# Bloom Filter & HyperLogLog — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE | Episode: 27 of 29

## HOOK (0:00–0:30)

[SCREEN: Black background, bold white text types out — "5,000,000,000 URLs. One question: does this short code already exist?"]

Five billion. That's how many short codes a URL shortener might already have handed out. Every single time it mints a new one, it has to answer one question: does this code already exist?

[SCREEN: Split screen — left side "Naive: Query the DB" with a spinning loader, right side "Smart: Ask a 6GB bit array in memory" with an instant checkmark]

The naive answer is "just query the database." But do that on every single generation, millions of times a day, and you've built yourself a self-inflicted DDoS attack on your own DB.

[SCREEN: Title card — "Bloom Filter & HyperLogLog — Approximate Data Structures That Save You Gigabytes"]

Today we're talking about two data structures that answer "does this exist?" and "how many distinct things are there?" — without ever storing the actual data. Let's get into it.

## THE PROBLEM (0:30–2:00)

[SCREEN: Diagram — a giant database icon labeled "5 Billion Records" with a magnifying glass hovering over it, red "SLOW" stamp]

Here's the core problem. You've got a massive set — could be five billion URL codes, could be a billion user IDs, could be every email message-ID you've ever processed. And you need to ask it one of two questions, constantly, at high throughput.

Question one: "Is this thing in the set?" If you store the full set — a HashSet, a Redis SET — that's exact, but it grows linearly. Five billion codes at ten bytes each is fifty gigabytes just sitting there, and every membership check is a disk seek or a network round-trip you didn't need.

[SCREEN: Second diagram — a stream of user events flowing into a funnel, label "How many DISTINCT users today?"]

Question two: "How many distinct things have I seen?" Say you're counting daily active users across a billion events. To get an exact answer you need to store every unique user ID somewhere — a HashSet again — and that's eight gigabytes for a billion users. For a number you're going to look at on a dashboard once.

[SCREEN: Big red text — "You don't need EXACT. You need FAST and CLOSE ENOUGH."]

Both of these problems share the same shape: you're paying full, exact-storage cost for a question where an approximate answer — with a tunable, tiny error rate — is totally fine. That's exactly the gap Bloom filters and HyperLogLog fill.

## THE SOLUTION (2:00–5:00)

[SCREEN: Illustration — a bouncer at a velvet rope holding a small sticky note with checkboxes, contrasted against a giant filing cabinet labeled "10 million names" crossed out]

Let's start with the Bloom filter, and the mental model that makes it click: you're a bouncer at a club with a blacklist of ten million names. You obviously can't memorize ten million names, or carry that list around. Instead, you carry a sticky note with just a hundred checkboxes.

When someone gets added to the blacklist, you run their name through three different hash functions — three "codes" — and check those three boxes. Say, box 14, box 37, box 82 for "Alice Troublemaker."

[SCREEN: Bit array animation — 16 boxes, three getting checked with arrows labeled h1, h2, h3]

Now Alice shows up at the door. You hash her name again, get the same three boxes — 14, 37, 82 — and check: are they all set? Yes, yes, yes. You say "probably on the list, denied."

Bob shows up. You hash his name, get box 14, 91, 5. Box 14 is checked... but box 91 is NOT checked. You stop immediately and say "definitely NOT on the list, come on in."

[SCREEN: Two-column callout — LEFT: "ANY box unchecked → DEFINITELY NOT in set (100% certain)" RIGHT: "ALL boxes checked → PROBABLY in set (could be a false positive)"]

That asymmetry is the entire magic trick. If any required bit is unset, the answer is guaranteed correct — definitely not present. If all bits are set, it's probably present, but it might be a false positive, because those bits could've been set by other entries. There's never a false negative. You will never accidentally let a blacklisted person through.

[SCREEN: Concrete code trace — alice@email.com sets bits 3, 7, 12. bob@email.com sets bits 1, 5, 12. carol@email.com queries bits 3, 7, 12 → all set → "PROBABLY IN SET" but carol was NEVER inserted. dave@email.com queries bit 2 → not set → "DEFINITELY NOT IN SET"]

Here's a real trace. We insert alice — sets bits 3, 7, 12. We insert bob — sets bits 1, 5, and 12 again, since 12 was already set from alice. Now carol queries — her hashes happen to land on 3, 7, 12 too, all already set from other people — so the filter says "probably in set." But carol was never inserted! That's your false positive. Meanwhile dave queries, hits an unset bit immediately, and gets a rock-solid "definitely not in set."

[SCREEN: Election exit poll graphic — "100 million voters" crossed out, replaced by "10,000 sampled voters, ±0.5% error, done in minutes"]

Now flip to HyperLogLog. Think of an election exit poll. You could interview all hundred million voters to get an exact turnout count — that takes forever and eight hundred megabytes of voter IDs. Or you interview ten thousand random voters and extrapolate. Minutes, tiny memory, half a percent error.

[SCREEN: Binary hash strings for u1 through u7, with "leading zeros" highlighted in each, max = 3, formula "2^3 × 0.72 ≈ 6" appearing]

HyperLogLog automates that idea for counting distinct values in a stream. It hashes every element to a binary number and tracks one statistic: the maximum count of leading zeros it's ever seen across all those hashes. Why leading zeros? Because the more distinct values you throw at a hash function, the more likely you are to eventually see a rare pattern — like four zeros in a row — purely by chance. The rarer the pattern you've observed, the more distinct items you must have processed to find it. Plug that max into the formula — two to the power of max leading zeros, times a correction constant — and you get a cardinality estimate.

[SCREEN: Big comparison table — "HashSet: 8 GB | HyperLogLog: 12 KB | Error: 0.81%"]

And the numbers here are almost absurd. For a billion distinct users, an exact HashSet costs eight gigabytes. HyperLogLog costs twelve kilobytes — flat, whether you're tracking a thousand users or a trillion — with an error rate of just 0.81%. That's a seven-hundred-thousand-times reduction in memory for a rounding error in accuracy.

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)

[SCREEN: Bold red header — "TRAP #1: Bloom filters CANNOT delete"]

First trap: engineers reach for a Bloom filter, then someone asks "how do I remove an entry?" — and the answer is you can't. Unsetting a bit could break membership checks for other entries that share that bit. If your use case needs deletions — say, a cache of "active sessions" where sessions expire — you need a Counting Bloom Filter, which uses small counters instead of single bits, so a delete just decrements the counter instead of blindly clearing it. Standard Bloom filters are insert-and-check only.

[SCREEN: Formula on screen — "p = (1 - e^(-kn/m))^k" then below it "k_optimal = (m/n) × ln(2) ≈ 0.693 × (m/n)"]

Second trap: treating the false positive rate as a fixed cost of doing business instead of a tunable dial. The formula is p equals one minus e to the power of negative k times n over m, all raised to the k. Where k is your number of hash functions, n is elements inserted, m is bits in the array. And there's an optimal k that minimizes false positives for a given size: k-optimal equals m over n, times the natural log of 2 — about 0.693 times m over n.

[SCREEN: Two use-case cards side by side — LEFT: "URL Shortener — FPP 1% is FINE" RIGHT: "Spam Filter — FPP 0.001% or lower"]

Here's where engineers get the tuning wrong: they pick one FPP and use it everywhere. For a URL shortener with five billion codes, one percent false positive rate needs about 9.6 bits per element — roughly six gigabytes — with seven hash functions. And one percent is genuinely fine there, because a false positive just means "generate another code and retry." Negligible overhead, no correctness issue.

But use that same one-percent tolerance on a spam filter, and you've got a real problem — because a false positive there means a legitimate email gets silently dropped as a duplicate. For that, you need something like 0.001%, one in a hundred thousand, or lower. Same data structure, wildly different tuning, because the cost of being wrong is completely different.

[SCREEN: Red X over a shield icon labeled "is this user admin?"]

Third trap, and this one's serious: using a Bloom filter for anything security-critical where you need an exact answer. "Is this user an admin?" is NOT a Bloom filter question. A false positive there means an unauthorized user gets treated as an admin. Bloom filters are for eliminating unnecessary work — extra DB lookups, wasted disk reads, redundant re-crawls — never for making authorization or financial decisions. If being wrong causes a security or correctness violation, you need an exact structure, full stop.

[SCREEN: Bold header — "TRAP #2: HyperLogLog only counts — it doesn't remember WHO"]

Fourth trap, and it trips people up on the HyperLogLog side: you cannot ask HyperLogLog "which specific users visited today?" It gives you a count, a single number, with 0.81% error baked in — it throws away identity entirely by design. If your actual requirement is "list of users who did X" or "exact revenue today," HyperLogLog is the wrong tool. It's for "how many," never for "which ones" or "the precise total."

[SCREEN: Decision checklist — "Need exact answer? → HashSet. Need 'definitely not present' at scale? → Bloom Filter. Need approximate distinct count? → HyperLogLog. Need to know WHO or the exact number? → Neither."]

So the rule of thumb: reach for a Bloom filter only when false positives cost you extra work, never correctness — and reach for HyperLogLog only when you need a count, not identities, and a sub-one-percent error is acceptable.

## REAL WORLD (8:00–9:30)

[SCREEN: Cassandra logo, with SSTable files on disk and a small "Bloom Filter" chip sitting in memory in front of them]

Let's ground this in production. Apache Cassandra's storage engine writes SSTables to disk, and without help, a read for a key that doesn't exist would mean scanning multiple SSTable files — expensive disk I/O. So each SSTable carries an in-memory Bloom filter, built at compaction time. On every read, Cassandra checks the Bloom filter first — if it says "definitely not present," that SSTable is skipped entirely, zero disk I/O. The result: seventy to ninety percent of unnecessary SSTable reads get eliminated. That's configurable too — Cassandra lets you set `bloom_filter_fp_chance` per table, trading memory for fewer wasted reads.

[SCREEN: Redis command block — "BF.RESERVE usernames_bloom 0.001 10000000" then "BF.ADD" then "BF.EXISTS"]

In application code, Redis Stack gives you this directly. `BF.RESERVE` sets up a filter with a target error rate and capacity. `BF.ADD` inserts an element. `BF.EXISTS` checks it — and returns zero for "definitely absent," meaning you skip the database entirely, or one for "probably present," meaning you go verify against the DB. That's your fast path versus your verify path, in two Redis calls.

[SCREEN: Redis command block — "PFADD dau:2024-01-15 user:123" then "PFCOUNT dau:2024-01-15" then "PFMERGE wau:week1 dau:mon dau:tue ..."]

And for HyperLogLog, Redis has native support — no extra module needed. `PFADD` adds a user ID to today's set. `PFCOUNT` gives you the estimated distinct count, 0.81% error, twelve kilobytes total. `PFMERGE` merges multiple HyperLogLogs together — say, seven daily active-user sets into one weekly active-user estimate — and it correctly deduplicates across the union.

[SCREEN: Three use-case cards — "01 Tiny URL: 5B codes, 1% FPP, ~6GB, skips 99% of DB checks" | "05 Social Media: per-user seen-post filter, 1% FPP, ~12KB each" | "20 Email System: spam dedup at 0.01% FPP + HyperLogLog for daily active senders"]

Three concrete places this shows up. Tiny URL: five billion existing codes, Bloom filter at one percent false positive rate costs about six gigabytes and lets ninety-nine percent of code generations skip the database completely — the one percent that hit a false positive just retry with a new code. Social media feeds: "has this user already seen this post?" — a per-user Bloom filter sized for ten thousand posts at one percent FPP costs about twelve kilobytes per user, and an occasional false-positive-hidden post is totally tolerable. And email systems: spam deduplication needs a very low FPP, around 0.01%, because a false positive there means a real email doesn't get delivered — while a separate HyperLogLog tracks distinct daily senders and recipients for analytics without storing billions of addresses.

## OUTRO + NEXT EPISODE (9:30–10:00)

[SCREEN: The architect's quote appears word by word over a dark background, then holds]

If you remember one thing from this video, remember this:

"Bloom filters tell you what definitely isn't there — eliminating unnecessary lookups at scale — and HyperLogLog tells you approximately how many distinct things are there — both trading a tunable sliver of accuracy for orders-of-magnitude savings in memory."

[SCREEN: "Episode 27 of 29" checkmark, then "NEXT: Episode 28 — B-Tree vs LSM-Tree" with MySQL and Cassandra/RocksDB logos side by side]

That's Bloom filters and HyperLogLog. Next episode, we go one layer deeper into storage engines themselves — B-Tree versus LSM-Tree, why MySQL reaches for one and Cassandra and RocksDB reach for the other, and what that choice actually costs you in read and write performance.

[SCREEN: Subscribe button animation, series playlist thumbnail]

If this series is helping you prep for system design interviews, subscribe so you don't miss episode 28. See you there.
