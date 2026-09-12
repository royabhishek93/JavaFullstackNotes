# Geohash vs QuadTree: Map Partitioning for Location-Based Systems
### How distributed systems answer "find me the 10 closest things to this point"

---

## PART 1 — THE STUDENT CONVERSATION

Imagine you have a map of the world with 1 billion restaurants. A user opens their app and asks: "Find restaurants within 5km of me."

Your database has a `restaurants` table with `latitude` and `longitude` columns. You think: I'll just do:

```sql
SELECT * FROM restaurants
WHERE latitude BETWEEN 40.7 AND 40.8
  AND longitude BETWEEN -74.0 AND -73.9;
```

That works... sort of. You can put a B-tree index on `latitude` and another on `longitude`. But a B-tree index works great on ONE dimension — it sorts values in a line. The moment you add the second dimension (`AND longitude BETWEEN ...`), the database has to scan the entire latitude range and then filter by longitude. For 1 billion rows, this is slow.

The problem: **a B-tree index doesn't understand 2D space.** It can't answer "what's near this point" — it only knows "what's between these two values on a number line."

You need to collapse 2D coordinates into 1D in a way that preserves spatial proximity. Two approaches dominate:

**Geohash:** Divide the world into a grid. Assign each grid cell a short string code. "ezjmg" is a cell in New York City. Critically, nearby locations share a common prefix — "ezjmg" and "ezjmh" are adjacent cells. To find nearby restaurants, you find all restaurants whose geohash STARTS with the same prefix. That's a standard B-tree range scan — fast, simple, works with any SQL database.

**QuadTree:** Recursively split the map into 4 quadrants. Keep splitting until each cell has at most K points. The trick: cells are smaller where data is dense (NYC has tiny cells, split 15 levels deep) and larger where data is sparse (the Sahara has one massive cell covering thousands of kilometers). The tree structure adapts to your actual data distribution.

Think of Geohash as a fixed grid and QuadTree as an adaptive grid. Both solve the same problem. Your choice depends on whether you need simplicity (Geohash) or adaptive density handling (QuadTree).

---

## PART 2 — THE SPATIAL INDEXING DIAGRAMS

### Geohash: Fixed Grid Encoding

```
World → divide into 32 cells (base-32 encoding of lat/lng interleaved bits)
Each cell → divide into 32 sub-cells (append one character to hash)
Each sub-cell → divide into 32 sub-sub-cells (append another character)
...

Precision levels:
  1 char  = ~5000km x 5000km  (continent level)
  2 chars = ~1250km x 625km   (country level)
  3 chars = ~156km  x 156km   (large region)
  4 chars = ~39km   x 20km    (city level)
  5 chars = ~4.9km  x 4.9km   (district)
  6 chars = ~1.2km  x 0.6km   (neighborhood) <-- typical for "nearby restaurants"
  7 chars = ~152m   x 152m    (street block)
  8 chars = ~38m    x 19m     (building level)

Example: NYC restaurant at lat=40.748, lng=-73.985
  geohash(6) = "dr5reu"

Geohash prefix hierarchy:
  "d"       = NE USA + Canada (5000km wide cell)
  "dr"      = NYC metro area
  "dr5"     = Manhattan + nearby boroughs
  "dr5r"    = Midtown Manhattan area
  "dr5re"   = Few city blocks
  "dr5reu"  = Specific building

Nearby search: find all restaurants within ~1km
  SELECT * FROM restaurants
  WHERE geohash LIKE 'dr5re%'  -- center cell
     OR geohash LIKE 'dr5rf%'  -- east neighbor
     OR geohash LIKE 'dr5rd%'  -- west neighbor
     OR geohash LIKE 'dr5rg%'  -- north neighbor
     OR geohash LIKE 'dr5rs%'  -- south neighbor
     -- ... 4 more diagonal neighbors
  -- Total: 9 prefix queries, each uses B-tree index on geohash column
```

### The 9-Neighbor Problem (Critical Edge Case)

```
+----------+----------+----------+
|          |          |          |
|  dr5rb   |  dr5re   |  dr5rg   |
|          |   YOU    |          |
|          |  (here)  |          |
+----------+----------+----------+
|          |          |          |
|  dr5r8   |  dr5rd   |  dr5rf   |  <-- restaurant here is in "dr5rf"
|          |          |    *     |      NOT in "dr5re" (your cell)
|          |          |          |      but only 10m away from border!
+----------+----------+----------+
|          |          |          |
|  dr5r2   |  dr5r9   |  dr5ru   |
|          |          |          |
+----------+----------+----------+

Always query center cell + all 8 neighbors = 9 total cells.
Never query just the center cell alone.
```

### QuadTree: Adaptive Recursive Splitting

```
World
├── NW Quadrant  (Arctic, Pacific, Canada)
│   ├── NW-NW  [3 restaurants] → LEAF (below threshold K=50)
│   ├── NW-NE  [1 restaurant]  → LEAF
│   ├── NW-SW  [47 restaurants] → LEAF
│   └── NW-SE  [89 restaurants] → SPLIT FURTHER
│       ├── NW-SE-NW [12 rest] → LEAF
│       ├── NW-SE-NE [8 rest]  → LEAF
│       ├── NW-SE-SW [31 rest] → LEAF
│       └── NW-SE-SE [38 rest] → LEAF
│
└── NE Quadrant  (NYC, Boston, DC — DENSE!)
    ├── NY-NW  → split → split → split → ... (12 levels deep = city blocks)
    └── NY-NE  → split → split → split → ...
         └── Leaf cell = a single NYC block
              [3 restaurants]

Key property:
  Sahara Desert leaf cell = 500km x 500km  (0 restaurants, never split)
  Manhattan leaf cell     = 100m x 100m    (max K restaurants, split many times)

Search "find restaurants within 5km":
  1. Start at root
  2. Traverse toward your coordinates
  3. Find leaf cells that overlap with your 5km radius circle
  4. Return all restaurants in those leaf cells
  5. Post-filter: calculate actual distance, return within 5km
```

---

## PART 3 — INTERNALS, IMPLEMENTATION, AND REAL NUMBERS

### Geohash in PostgreSQL

```sql
-- PostGIS extension required (or pgcrypto + manual encoding)
-- Option 1: PostGIS built-in
ALTER TABLE restaurants ADD COLUMN geohash VARCHAR(12);
UPDATE restaurants SET geohash = ST_GeoHash(location::geometry, 6);

-- Index the geohash column (standard B-tree works perfectly)
CREATE INDEX idx_restaurants_geohash ON restaurants(geohash);

-- EXPLAIN ANALYZE: this is an index scan, not a seq scan
SELECT id, name, latitude, longitude
FROM restaurants
WHERE geohash LIKE 'dr5re%'

-- Full 9-cell query (production query)
SELECT id, name, latitude, longitude,
       ST_Distance(location, ST_Point(-73.985, 40.748)::geography) AS dist_meters
FROM restaurants
WHERE geohash IN (
    'dr5reu', 'dr5res', 'dr5ret', 'dr5rev', 'dr5rew',  -- center + N neighbors
    'dr5ref', 'dr5reg', 'dr5ree', 'dr5reb'              -- remaining neighbors
)
ORDER BY dist_meters
LIMIT 20;

-- Neighbor cells: use a geohash library
-- Python: pip install python-geohash
-- Java:   com.github.davidmoten:geo (GitHub: davidmoten/geo)
```

### Redis GEOADD / GEORADIUS (Geohash Under the Hood)

```bash
# Redis stores coordinates using geohash internally (52-bit integer in sorted set)
# O(log N) for GEOADD, O(N+log M) for GEORADIUS

# Store driver location (Uber: 1M active drivers)
GEOADD drivers:active -73.985 40.748 "driver:42"
GEOADD drivers:active -73.991 40.752 "driver:99"

# Find drivers within 5km
GEORADIUS drivers:active -73.985 40.748 5 km
  WITHCOORD    # return coordinates
  WITHDIST     # return actual distance
  ASC          # sort by distance
  COUNT 10     # return max 10

# Output:
# 1) "driver:42" -> dist: 0.00km, coords: (-73.985, 40.748)
# 2) "driver:99" -> dist: 0.73km, coords: (-73.991, 40.752)

# Update driver location (every 3 seconds)
GEOADD drivers:active -73.990 40.749 "driver:42"  # overwrites previous

# Uber scale: 1M drivers x 1 update/3s = 333,333 GEOADD/sec
# Redis single-threaded: handles ~500K ops/sec on modern hardware
# Solution: Redis Cluster with multiple geo shards by city/region
```

### QuadTree In-Memory (Java Pseudocode)

```java
class QuadTreeNode {
    double minLat, maxLat, minLng, maxLng;
    List<Restaurant> restaurants;  // only populated in leaf nodes
    QuadTreeNode[] children;       // null for leaf nodes
    static final int MAX_CAPACITY = 50;

    void insert(Restaurant r) {
        if (children != null) {
            // Internal node: route to correct child
            getQuadrant(r).insert(r);
            return;
        }
        restaurants.add(r);
        if (restaurants.size() > MAX_CAPACITY) {
            split();  // become internal node, re-insert all restaurants
        }
    }

    List<Restaurant> searchRadius(double lat, double lng, double radiusKm) {
        if (!overlapsCircle(lat, lng, radiusKm)) return Collections.emptyList();
        if (children == null) {
            // Leaf: return all restaurants, caller filters by exact distance
            return restaurants;
        }
        List<Restaurant> result = new ArrayList<>();
        for (QuadTreeNode child : children) {
            result.addAll(child.searchRadius(lat, lng, radiusKm));
        }
        return result;
    }
}

// Build on startup (1M restaurants, ~5 seconds to build)
QuadTreeNode root = new QuadTreeNode(-90, 90, -180, 180);
restaurantRepository.findAll().forEach(root::insert);
```

### PostGIS R-Tree (Most Powerful, SQL-Native)

```sql
-- PostGIS uses GiST index which is effectively an R-Tree (QuadTree variant)
CREATE EXTENSION postgis;

ALTER TABLE restaurants
  ADD COLUMN location geography(POINT, 4326);

UPDATE restaurants
  SET location = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography;

-- GiST index = spatial tree index
CREATE INDEX idx_restaurants_location_gist
  ON restaurants USING GIST(location);

-- ST_DWithin: uses GiST index, O(log N + K)
SELECT id, name,
       ST_Distance(location, ST_Point(-73.985, 40.748)::geography) AS dist_m
FROM restaurants
WHERE ST_DWithin(
    location,
    ST_Point(-73.985, 40.748)::geography,
    5000   -- 5000 meters = 5km
)
ORDER BY dist_m
LIMIT 20;

-- EXPLAIN ANALYZE on this query shows: Index Scan using idx_restaurants_location_gist
-- 50M restaurants, ST_DWithin 5km: ~5ms (with GiST index)
-- Without index: sequential scan, 30+ seconds
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Design the 'Find drivers near me' feature for UBER. Drivers update their location every 3 seconds. Users need to see all drivers within 5km. How do you store and query driver locations?"

**You (architect answer):**

> "This is a write-heavy, read-heavy geo problem. Let me separate the two concerns.
>
> For writes: drivers push a location update every 3 seconds. With 1 million active drivers that's 333K writes per second. I would NOT go to PostgreSQL for this — it can't sustain that write rate on a single node. Instead, I'd use Redis GEOADD with the driver ID as the member and lat/lng as coordinates. Redis stores these internally as geohash integers in a sorted set, so each GEOADD is O(log N). With Redis Cluster sharded by city or geographic region, we handle this write volume easily.
>
> For reads: a user opens the app and requests drivers within 5km. This hits GEORADIUS on the same Redis cluster. It returns driver IDs and distances in O(N + log M) where N is the result count. That's sub-millisecond at our scale.
>
> The subtle issue here is stale data. Drivers who go offline may still appear in Redis. I'd set an expiry: each GEOADD also refreshes a key like `driver:42:last_seen` with TTL of 10 seconds. A background job removes drivers whose last_seen expired from the geo set.
>
> For the persistence layer, I'd use PostgreSQL with PostGIS and a GiST index as the source of truth — but only for historical queries, reporting, or cold-start loading. All real-time location data lives in Redis.
>
> If the interviewer pushes to 10 million drivers, I'd shard Redis by geohash prefix — all drivers in geohash cells starting with 'd' (eastern US) go to shard 1, 'e' (western Europe) to shard 2, etc. The application layer resolves which shard to query based on the user's geohash prefix."

---

## PART 5 — DECISION FRAMEWORK

### Geohash vs QuadTree vs PostGIS R-Tree

| Criteria | Geohash | QuadTree (in-memory) | PostGIS R-Tree (GiST) | Redis GEORADIUS |
|---|---|---|---|---|
| **Data location** | DB column (SQL) | Application memory | PostgreSQL | Redis (in-memory) |
| **Write throughput** | ~10K/s (indexed write) | RAM-only (instant) | ~5K/s (GiST maintenance) | ~500K/s |
| **Query latency** | 1-10ms (9 SQL queries) | <1ms (tree traverse) | 2-10ms (single query) | <1ms |
| **Data volume** | 100M+ rows fine | Fits in RAM (~5GB for 10M) | 100M+ rows fine | Up to ~100M members |
| **Density adaptivity** | No (fixed grid) | Yes (adaptive cells) | Yes (R-Tree adapts) | No (geohash fixed) |
| **Edge cases** | Must query 9 cells | Must handle overlapping cells | PostGIS handles natively | Must query 9 cells |
| **Operational complexity** | Low (just SQL index) | Medium (warm-up, invalidation) | Medium (PostGIS setup) | Low (Redis native) |
| **Best for** | Simple, any SQL DB | Proximity service in-memory cache | PostgreSQL-native spatial | Real-time location updates |

### Decision Tree

```
Is this real-time location (updates every few seconds)?
  YES --> Redis GEORADIUS (geohash under the hood)
         Shard by geographic region for >500K writes/sec
  NO  --> How many records?
           <10M AND fits in memory?
             YES --> In-memory QuadTree (sub-millisecond, adaptive)
             NO  --> Are you already using PostgreSQL?
                      YES --> PostGIS GiST index (ST_DWithin)
                      NO  --> Geohash column + B-tree index (simpler, any DB)

Do you need to shard the database itself by geography?
  YES --> Use geohash prefix as shard key
          All rows with geohash starting 'dr' go to shard NYC
          All rows with geohash starting 'u0' go to shard London
```

---

## QUICK REFERENCE CARD

```
GEOHASH PRECISION (use 6 chars for "nearby" queries):
  6 chars = 1.2km x 0.6km = neighborhood
  Always query 9 cells (center + 8 neighbors)

POSTGRESQL:
  CREATE INDEX ON restaurants(geohash);           -- B-tree on varchar
  ST_GeoHash(location::geometry, 6)               -- generate geohash
  ST_DWithin(a, b, meters)                        -- PostGIS spatial search

REDIS (Uber-style):
  GEOADD key lng lat member                       -- store/update location
  GEORADIUS key lng lat 5 km ASC COUNT 10         -- find nearby

IN-MEMORY QUADTREE:
  MAX_CAPACITY = 50 points per leaf
  Build on startup, reload on deploy
  ~5GB RAM for 10M points

SHARDING BY GEOHASH:
  shard = hash(geohash_prefix_4_chars) % num_shards
  Keeps geographic neighbors on same shard
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Every time an interview says "location," "nearby," "within X km," or "find closest" — you are being tested on spatial indexing, and the answer starts with geohash or QuadTree.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **06 — UBER** | Driver location storage is the core problem. Redis GEOADD (geohash internally) handles 1M drivers updating every 3s = 333K writes/sec. GEORADIUS for "find drivers within 5km." City-level Redis shards handle geographic isolation. |
| **08 — Food Delivery** | "Find restaurants within delivery radius." PostgreSQL PostGIS with GiST index on restaurant location column. User's delivery address converts to a geography point, ST_DWithin returns restaurants within 5km radius in a single indexed query. |
| **14 — Proximity Search** | The entire system is geospatial. Geohash used as the database sharding key (all restaurants with geohash prefix "dr5" go to shard 3 — geographically colocated data). QuadTree for in-memory index in the proximity service for sub-millisecond lookups before hitting the DB. |

**Architect's one-liner for the interview:**
*"B-tree indexes are 1D — they can't answer spatial queries; we collapse 2D coordinates into a geohash string so standard indexed prefix lookups give us geographic proximity search, or we use a QuadTree to adaptively partition dense areas like city centers into smaller cells than sparse areas like deserts."*

---
