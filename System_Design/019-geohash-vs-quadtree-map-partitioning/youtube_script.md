# Geohash vs QuadTree — Map Partitioning for Location-Based Systems — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE | Episode: 19 of 29

## HOOK (0:00–0:30)

[Screen cue: title card — "1,000,000,000 restaurants. Find me the ones within 5km. Go."]

Imagine your database has 1 billion restaurants. A user opens the app and taps "restaurants near me." Sounds simple, right? You write:

```sql
SELECT * FROM restaurants
WHERE latitude BETWEEN 40.7 AND 40.8
  AND longitude BETWEEN -74.0 AND -73.9;
```

You put a B-tree index on `latitude`, another on `longitude`. Ship it. Then production traffic hits, and this query takes 30 seconds instead of 5 milliseconds.

[Screen cue: red X over the SQL query, text overlay — "B-TREE INDEXES ARE 1D. YOUR MAP IS 2D."]

Here's the part almost nobody explains in an interview: a B-tree index is built to sort values along ONE line. Latitude by itself, fine. Longitude by itself, fine. But the moment you ask "give me both conditions together," Postgres can only use ONE of those indexes efficiently — it scans a huge latitude range and then filters longitude row by row. On a billion rows, that's a full-blown bottleneck. Today we fix that — with Geohash and QuadTree.

## THE PROBLEM (0:30–2:00)

[Screen cue: whiteboard sketch — a number line labeled "B-tree: 1D" next to a 2D map grid labeled "Space: 2D"]

Let's slow down and really understand why this breaks. A B-tree is a sorted structure — like a phone book sorted by last name. Great at "find everyone between Smith and Thompson." Terrible the second you ALSO want "and their first name starts with J" as a combined range — because sorting by last name tells you nothing about how first names are arranged inside that range.

That's exactly what's happening with `latitude BETWEEN ... AND longitude BETWEEN ...`. The database picks one index — say latitude — narrows down to everyone in that latitude band, which could still be millions of rows scattered across the entire globe east-to-west. Then it has to check longitude on every single one of those rows manually. No shortcut. That's your 30-second query.

[Screen cue: two-column comparison appears — "GEOHASH: fixed grid, string prefix" | "QUADTREE: adaptive, recursive split"]

So the real engineering question is: how do we collapse two dimensions — latitude and longitude — into something a normal index CAN understand, while still preserving "things that are near each other in real life stay near each other in our data structure"?

Two answers dominate real systems:

**Geohash** — carve the entire world into a grid, and give every cell a short string code. Nearby places get strings that share the same prefix. That turns "find nearby" into a boring string-prefix lookup, which any B-tree index handles beautifully.

**QuadTree** — recursively slice the map into four quadrants, over and over, but only where there's actually data. Dense areas like Manhattan get sliced down to tiny blocks. Empty areas like the Sahara stay as one giant cell.

Same problem, two very different trade-offs. Let's build both.

## THE SOLUTION (2:00–5:00)

[Screen cue: animated zoom — world map splitting into 32 cells, then one cell splitting into 32 more]

Start with Geohash. The world is divided into 32 cells using base-32 encoding of interleaved latitude/longitude bits. Each of those cells divides into 32 more. Each character you add to the hash string narrows your area by roughly another factor of 32.

Here's the precision table that actually matters in an interview:

[Screen cue: table on screen]
```
1 char  ≈ 5000km × 5000km   — continent
3 chars ≈ 156km  × 156km    — large region
4 chars ≈ 39km   × 20km     — city level
6 chars ≈ 1.2km  × 0.6km    — neighborhood  ← the sweet spot for "nearby"
8 chars ≈ 38m    × 19m      — building level
```

Six characters is the number you should remember. That's the "restaurants near me" precision — roughly a 1.2 by 0.6 kilometer box.

[Screen cue: zoom into NYC coordinate lat=40.748, lng=-73.985 → text "dr5reu" appears letter by letter]

Take a real restaurant in Manhattan: latitude 40.748, longitude -73.985. Its 6-character geohash is `dr5reu`. Now watch the prefix hierarchy — this is the part that makes geohash click:

- `d` alone = northeastern USA plus Canada, a cell 5000km wide
- `dr` = the NYC metro area
- `dr5` = Manhattan and nearby boroughs
- `dr5r` = Midtown Manhattan
- `dr5re` = a few city blocks
- `dr5reu` = the specific building

Every extra character zooms in further, and — this is the key trick — two restaurants on the same block will share the same 6-character prefix. So "find nearby restaurants" becomes:

```sql
WHERE geohash LIKE 'dr5re%'
```

That's a plain B-tree range scan. Fast. Works on any SQL database, no special extension required.

[Screen cue: 3x3 grid diagram appears, center cell highlighted "dr5re — YOU ARE HERE", a red dot placed just across the border in the cell to the right labeled "dr5rf"]

But here's the trap — and it's the single most common mistake engineers make with geohash, so pay attention. Grid cells have hard edges. Imagine you're standing right at the border of cell `dr5re`. A restaurant is 10 meters away from you — practically next door — but it happens to fall on the other side of that invisible line, inside cell `dr5rf`. If your query only checks `WHERE geohash LIKE 'dr5re%'`, you will MISS that restaurant entirely, even though it's closer than restaurants three blocks away that happen to share your cell.

The fix: you never query just the center cell. You ALWAYS query the center plus its 8 surrounding neighbors — 9 cells total.

```sql
WHERE geohash IN (
  'dr5reu','dr5res','dr5ret','dr5rev','dr5rew',
  'dr5ref','dr5reg','dr5ree','dr5reb'
)
```

Nine prefix lookups, each hitting the same B-tree index. That's the real production pattern — remember "9 neighbors" and you'll sound like someone who's actually shipped this.

[Screen cue: tree diagram — world splitting into NW/NE/SW/SE, NE branch (labeled "NYC — dense") splitting 12 levels deep into tiny leaves, NW branch (labeled "Sahara — sparse") staying as one giant leaf]

Now QuadTree — the adaptive alternative. Instead of a fixed grid, you recursively split into four quadrants, but only when a cell gets too crowded. Each node has a `MAX_CAPACITY`, say 50 points. Add a 51st restaurant to a cell, and it splits into four children, redistributing the points.

The beautiful part is what this does to real geography. A leaf cell over the Sahara Desert — zero restaurants — never splits. It stays one massive 500km by 500km cell. Meanwhile a leaf cell over Manhattan, packed with restaurants, keeps splitting and splitting until each leaf is roughly 100 meters by 100 meters, maybe 12 levels deep. The tree structure literally mirrors where your data actually lives. That's density adaptivity, and it's the thing geohash's fixed grid can never give you.

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)

[Screen cue: Redis logo + "GEOADD / GEORADIUS" + Uber-style map pin icon]

Let's go to the numbers, because this is where interviews separate people who've read a blog post from people who've actually operated this at scale.

Redis's `GEOADD` and `GEORADIUS` commands use geohash under the hood — they store coordinates as a 52-bit integer inside a sorted set. Picture Uber: 1 million active drivers, each pushing a location update every 3 seconds.

[Screen cue: math appears on screen — "1,000,000 drivers ÷ 3 sec = 333,333 GEOADD/sec"]

Do that division: 1,000,000 divided by 3 equals 333,333 writes per second, sustained. Now, Redis is single-threaded for command execution, and on modern hardware it tops out around 500,000 operations per second. So 333K writes alone is already two-thirds of your entire single-node budget — before you've served a single read.

The fix engineers actually use in production: Redis Cluster, sharded by city or geographic region. Don't put all 1 million drivers in one Redis instance — split by geohash prefix, so drivers in the eastern US land on shard 1, drivers in western Europe land on shard 2. Each shard now only handles a fraction of that 333K/sec.

[Screen cue: PostGIS logo + "GiST index" + comparison bar chart: "5ms with index" vs "30+ seconds without"]

Next, PostGIS — the SQL-native option. It uses a GiST index, which is functionally a variant of an R-Tree. Picture 50 million restaurants in Postgres, and you run:

```sql
WHERE ST_DWithin(location, ST_Point(-73.985, 40.748)::geography, 5000)
```

With the GiST index in place: about 5 milliseconds. Without it — a sequential scan across all 50 million rows — 30-plus seconds. Same query, same data, the only difference is whether that spatial index exists. If you ever see an `EXPLAIN ANALYZE` in an interview showing a sequential scan on a location query, that's your answer: missing GiST index.

[Screen cue: clock icon ticking down, text "TTL 10s" + "background cleanup job"]

Now the trap almost nobody mentions unprompted: stale drivers. A driver goes offline — phone dies, app crashes, they log out — but their last location is still sitting in Redis's geo sorted set. If you don't clean that up, users start seeing "available" drivers who vanished ten minutes ago.

The real solution: every `GEOADD` also refreshes a companion key like `driver:42:last_seen` with a TTL of 10 seconds. A background job periodically sweeps the geo set and removes any driver whose `last_seen` key expired. Two moving parts — the geo data and a separate expiring heartbeat key — working together.

[Screen cue: decision framework table fills in row by row]

Let's put the whole picture into one table, because this is exactly what you'd draw on a whiteboard in a system design interview:

```
                    Geohash        QuadTree        PostGIS R-Tree     Redis GEORADIUS
Write throughput    ~10K/s         RAM-only         ~5K/s              ~500K/s
Query latency       1-10ms         <1ms             2-10ms             <1ms
Data volume         100M+ rows     fits in RAM      100M+ rows         ~100M members
Density adaptive?   No             Yes              Yes                No
```

Notice the pattern: Redis wins on raw write throughput because it's all in-memory and single-threaded-fast. QuadTree wins on density adaptivity and latency because it lives in application RAM. PostGIS wins when you need this to live natively inside a relational database you already operate. Geohash wins when you want the absolute simplest thing that works on any SQL database with zero extensions.

## REAL WORLD (8:00–9:30)

[Screen cue: map icons — Uber logo, food delivery bike icon, magnifying glass over a pin]

Let's connect this to systems you've probably already designed or will be asked to design.

**Driver location at scale** — this is the Uber problem, and it's just as real for Ola and Uber in the Indian market, where dense metros like Bangalore and Mumbai push driver density even higher than US cities. 1 million active drivers, updates every 3 seconds, 333,333 writes per second sustained. Redis GEOADD as the write path, sharded by city so Bangalore traffic doesn't compete with Mumbai traffic on the same node.

**Food delivery radius search** — think Swiggy or Zomato figuring out "which restaurants can deliver to this address within their radius." This is a PostGIS problem, not a Redis problem, because restaurant locations don't move every 3 seconds — they're relatively static. `ST_DWithin` with a GiST index against 50 million restaurant rows, 5ms with the index, 30-plus seconds without it. The user's delivery address becomes a geography point, and one indexed query returns everything in range, sorted by distance.

**Proximity search as a hybrid architecture** — this is where geohash and QuadTree work TOGETHER instead of competing. Geohash becomes your database sharding key: all restaurants whose geohash starts with `dr5` physically live on the same database shard, because they're geographically clustered anyway. On top of that, an in-memory QuadTree sits inside your proximity service, giving you sub-millisecond lookups before you ever touch the database — you only fall through to the DB shard when the in-memory tree doesn't have a fresh enough answer.

[Screen cue: architect quote card]

If there's one line to remember for the interview whiteboard, it's this: *"B-tree indexes are 1D — they can't answer spatial queries, so we either collapse 2D coordinates into a geohash string for prefix-based indexed lookups, or we use a QuadTree to adaptively partition dense areas like city centers into much smaller cells than sparse areas like deserts."*

## OUTRO + NEXT EPISODE (9:30–10:00)

[Screen cue: recap bullet list — "B-tree = 1D", "Geohash = fixed grid + prefix + 9 neighbors", "QuadTree = adaptive splitting", "Redis GEOADD for writes, PostGIS GiST for scale"]

So that's Geohash versus QuadTree: fixed grid with string prefixes versus adaptive recursive splitting, always remembering the 9-neighbor rule, and knowing when Redis, PostGIS, or an in-memory tree is the right tool for your write volume and data size.

[Screen cue: next episode title card — "Episode 20: The Hot Partition Problem"]

Next episode, we tackle a problem that geo-sharding by prefix can actually CAUSE if you're not careful — the hot partition problem. What happens when one shard — say, everyone in Manhattan — gets ten times the traffic of every other shard, and your "evenly distributed" system suddenly isn't even at all. See you in episode 20.
