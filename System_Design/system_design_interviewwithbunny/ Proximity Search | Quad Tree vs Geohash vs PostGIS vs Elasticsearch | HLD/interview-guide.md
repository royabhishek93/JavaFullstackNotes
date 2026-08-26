# Proximity Search — Interview Guide
## (QuadTree vs Geohash vs PostGIS vs Elasticsearch vs Redis Geo)

---

## The One-Line Summary Interviewers Want

> "Spatial index the data (QuadTree / Geohash / GIST), apply a bounding-box pre-filter to eliminate 90% of rows, then compute exact Haversine distance only for the survivors."

---

## Problem Statement

**Goal:** Find all POIs (restaurants, drivers, hotels) within radius R of (lat, lng) in < 100 ms.

| Constraint | Value |
|---|---|
| Latency | < 100 ms |
| Dataset | Millions – Billions of points |
| Write pattern | Static (restaurants) vs Real-time (drivers) |

**Real use cases:** Uber (find drivers), Yelp (find restaurants), Airbnb (find hotels), Google Maps (nearby POIs)

---

## 5 Approaches at a Glance

| Approach | Latency | Accuracy | Scaling | Best For |
|---|---|---|---|---|
| QuadTree | < 1 ms | Exact | Vertical only | In-memory, < 1M pts |
| Geohash | 10–50 ms | Approx (box) | Easy (shard by prefix) | Distributed, any SQL DB |
| PostGIS | 50–100 ms | Exact (Vincenty) | Moderate (region shard) | ACID, complex shapes |
| Elasticsearch | 10–50 ms | Exact (Haversine) | Excellent (horizontal) | Billions of pts + text search |
| Redis Geo | < 10 ms | Exact (Haversine) | Good (shard by region) | Real-time moving objects |

---

## Approach 1 — QuadTree

### What the Diagram Shows
The image shows a tree where each internal node has **4 children (NW, NE, SW, SE)**. The map zooms in three steps: Search Parent Node → Find First Child Node → Finds Markers. Each level subdivides the bounding box into 4 quadrants — the circular search area at the leaf level finally finds the red markers.

### How It Works
```
Root (whole world)
├── NW quadrant
│   ├── NW-NW  ← prune if circle doesn't intersect
│   ├── NW-NE
│   ├── NW-SW
│   └── NW-SE  ← recurse deeper
└── NE, SW, SE quadrants ...
```
- Each leaf stores ≤ 100 points (configurable capacity)
- **Search:** Start at root, check if circle intersects bounding box → prune entire subtree if no → collect leaf candidates → Haversine filter
- **Time:** O(log N + K) where K = result count; pruning eliminates 75%+ of tree

### Insert / Update / Delete
| Operation | Action |
|---|---|
| Insert | Traverse to correct leaf by coords, add point; if over capacity → split into 4 children |
| Update (driver moved) | Remove old position + insert new position (2 ops) |
| Delete | Mark deleted; rebuild tree periodically |

### Pros / Cons
| Pros | Cons |
|---|---|
| < 1 ms for balanced tree | Single server — not distributable |
| Great for dynamic data (frequent inserts) | Lost on restart unless persisted |
| Efficient for sparse datasets | Tree rebalancing on splits |

**Use when:** Game engines, in-memory hot-region cache, < 1M points on one server.  
**Never use when:** Production distributed DB, billions of points.

---

## Approach 2 — Geohash

### What the Diagram Shows
The image shows **3 zoom levels** of a binary grid (Level 1 = 4 cells, Level 2 = 16 cells, Level 3 = 64 cells). The precision table lists exact lat/lng bit counts and error margins (reproduced below). The SQL query shows querying **multiple LIKE prefixes** for neighboring cells.

### Encoding Algorithm
```
lat = 37.7749  →  binary bits: 01011010...
lng = -122.419 →  binary bits: 10011101...
                   interleave   →  0110011101010...
                   to base32    →  '9q8yy9mz'  (San Francisco)
```

### Precision Table (from diagram)

| Length | Lat Error | Lng Error | Height | Width | Use Case |
|---|---|---|---|---|---|
| 1 | ±23° | ±23° | 4992.6 km | 5009.4 km | Country |
| 2 | ±2.8° | ±5.6° | 624.1 km | 1252.3 km | Large region |
| 3 | ±0.70° | ±0.70° | 156 km | 156.5 km | City |
| 4 | ±0.087° | ±0.18° | 19.5 km | 39.1 km | District |
| 5 | ±0.022° | ±0.022° | 4.9 km | 4.9 km | Neighborhood |
| 6 | ±0.0027° | ±0.0055° | 609.4 m | 1.2 km | Street |
| 7 | ±0.00068° | ±0.00068° | 152.5 m | 152.9 m | Building |
| 8 | ±0.00086° | ±0.000172° | 19 m | 38.2 m | Precise |
| 9 | ±0.000021° | ±0.000021° | 4.8 m | 4.8 m | Sub-building |

### Radius → Precision Mapping
| Radius | Use Length | Reasoning |
|---|---|---|
| 100 m | 7 | ±76m cell, 9-cell query needed |
| 500 m | 6 | ±610m cell |
| 2 km | 5 | ±2.4km cell |
| 5 km | 4 | ±20km cell, larger box but fewer DB queries |

### Database Schema & Query
```sql
-- Schema
CREATE TABLE restaurants (
  id      SERIAL,
  name    VARCHAR,
  lat     DECIMAL,
  lng     DECIMAL,
  geohash VARCHAR(12)
);
CREATE INDEX idx_geohash ON restaurants (geohash);

-- Query (from diagram — query 9 cells: center + 8 neighbors)
SELECT * FROM restaurants
WHERE geohash LIKE 'sgkztus%'
   OR geohash LIKE 'sgkztur%'
   OR geohash LIKE 'sgkztuq%'
   -- ... 6 more neighbor cells
```

### The Critical Edge Case (Interviewers Always Ask This)
```
Point A: '9q8yyzzz'  (inside cell)
Point B: '9q8z0000'  (different 5th char but only 50m away!)
```
**Fix:** Always query 8 neighboring cells (9 total). Post-filter with Haversine to get exact circle.

### Pros / Cons
| Pros | Cons |
|---|---|
| Works with any SQL DB (no extensions) | Returns square box, not circle → must post-filter |
| Easy to shard (by geohash prefix) | Edge case requires 9-cell queries |
| Human-readable, shareable in URLs | Cell size varies by latitude |

---

## Approach 3 — PostgreSQL + PostGIS

### What the Diagram Shows
The image shows the exact INSERT and SELECT syntax. INSERT uses `ST_GeogFromText('SRID=4326;POINT(lng lat)')`. SELECT uses `ST_DWithin(location, user_point, 5000)` where 5000 is radius in meters.

### Setup
```sql
CREATE EXTENSION postgis;

CREATE TABLE restaurants (
  id       SERIAL PRIMARY KEY,
  name     VARCHAR(255),
  location GEOGRAPHY(POINT, 4326),  -- WGS84, accurate on sphere
  category VARCHAR(100),
  rating   DECIMAL(2,1)
);

-- GIST index: R-tree structure, O(log N) spatial lookup
CREATE INDEX idx_location_gist ON restaurants USING GIST (location);
```

### Insert & Query (from diagram)
```sql
-- Insert
INSERT INTO restaurants (name, location)
VALUES ('Taco Bell', ST_GeogFromText('SRID=4326;POINT(77.5946 12.9716)'));

-- Radius query
SELECT name,
       ST_Distance(location,
         ST_GeogFromText('SRID=4326;POINT(77.6080 12.9700)')) AS distance_m
FROM restaurants
WHERE ST_DWithin(
        location,
        ST_GeogFromText('SRID=4326;POINT(77.6080 12.9700)'),
        5000        -- 5km radius in meters
      )
  AND category = 'Fast Food'
  AND rating >= 4.0
ORDER BY distance_m
LIMIT 20;
```

### How ST_DWithin Works
1. Bounding box check via GIST index (fast, O(log N))
2. Exact distance check using **Vincenty formula** (±0.5mm accuracy)

### Complex Spatial Queries (PostGIS Unique)
```sql
-- Polygon containment (delivery zone, neighborhood search)
SELECT * FROM restaurants
WHERE ST_Contains(ST_GeomFromGeoJSON('{...polygon GeoJSON...}'), location);

-- Buffer zone (100m around a road)
SELECT * FROM restaurants
WHERE ST_DWithin(location, ST_Buffer(road_geom, 100), 0);
```

### Pros / Cons
| Pros | Cons |
|---|---|
| Exact Vincenty distance | PostgreSQL-only (not portable) |
| ACID guarantees | Single server bottleneck |
| Complex shapes (polygons, buffers) | Requires extension install |
| Mature ecosystem | ~100ms latency vs Redis's ~5ms |

**Scaling:** Shard by region (US-West DB, US-East DB) + read replicas per region.

---

## Approach 4 — Elasticsearch Geo Queries

### Index Mapping
```json
PUT /restaurants
{
  "mappings": {
    "properties": {
      "name":     { "type": "text" },
      "category": { "type": "keyword" },
      "location": { "type": "geo_point" },
      "rating":   { "type": "float" },
      "is_open":  { "type": "boolean" }
    }
  }
}
```
`geo_point` internally uses a **BKD tree** (block k-d tree) for spatial indexing.

### Proximity + Text + Filters Combined
```json
POST /restaurants/_search
{
  "query": {
    "bool": {
      "must":   [{ "match": { "name": "pizza" } }],
      "filter": [
        { "geo_distance": { "distance": "5km", "location": { "lat": 12.97, "lon": 77.59 } } },
        { "range":        { "rating": { "gte": 4.0 } } },
        { "term":         { "is_open": true } }
      ]
    }
  },
  "sort": [{ "_geo_distance": { "location": {"lat": 12.97, "lon": 77.59}, "order": "asc", "unit": "km" } }],
  "size": 20
}
```
**Execution order:** Full-text → 10K candidates → category filter → 2K → rating filter → 1K → geo_distance → 50 results.

### Geo Bounding Box (Faster for Viewport Queries)
```json
{ "query": { "geo_bounding_box": {
  "location": {
    "top_left":     { "lat": 13.0, "lon": 77.5 },
    "bottom_right": { "lat": 12.9, "lon": 77.7 }
  }
}}}
```
Use this when user scrolls a map — no expensive circle calculation.

### Distance Bucket Aggregations
```json
"aggs": {
  "distance_buckets": {
    "geo_distance": {
      "field": "location",
      "origin": { "lat": 12.97, "lon": 77.59 },
      "ranges": [{"to": 1}, {"from": 1, "to": 3}, {"from": 3, "to": 5}]
    }
  }
}
```

### Pros / Cons
| Pros | Cons |
|---|---|
| Horizontal scaling (billions of docs) | Eventual consistency (~1s refresh) |
| Combines proximity + full-text search | More expensive (memory intensive) |
| ~10–50ms at 100M documents | No ACID guarantees |
| Rich aggregations / facets | Complex cluster setup |

---

## Approach 5 — Redis Geospatial

### Commands
```bash
# Add / update (upsert)
GEOADD drivers 77.5946 12.9716 "driver_1"
GEOADD drivers 77.6100 12.9850 "driver_1"   # update = just GEOADD again

# Search circle: return 10 nearest drivers, sorted by distance
GEORADIUS drivers 77.5900 12.9700 5 km WITHDIST ASC COUNT 10
# → [("driver_1", "0.5 km"), ("driver_2", "1.2 km")]

# Neighbors of an existing member
GEORADIUSBYMEMBER drivers "driver_1" 2 km

# Distance between two members
GEODIST drivers "driver_1" "driver_2" km

# Delete / expire
ZREM drivers "driver_1"
EXPIRE drivers:online 3600   # auto-expire inactive set after 1 hour
```

### How GEORADIUS Works Internally
1. Encode center point to 52-bit geohash integer
2. Determine geohash prefix range that covers the radius
3. `ZRANGEBYLEX` on sorted set to get candidates in O(log N)
4. Haversine distance for each candidate → filter to those within radius → sort

Data is stored as a **ZSET** (sorted set) where score = geohash integer.

### Performance Numbers
| Points | Latency |
|---|---|
| 10K | ~1 ms |
| 100K | ~5 ms |
| 1M | ~10 ms |

**Memory:** ~50 bytes per point → 1M points ≈ 50 MB

### Pros / Cons
| Pros | Cons |
|---|---|
| Fastest queries (< 10 ms) | In-memory only (expensive at scale) |
| Real-time updates (upsert on every driver ping) | No complex filtering (category, rating) |
| Simple API | Data lost on restart (without AOF/RDB) |

**Hybrid pattern:** Redis for active drivers (10K online now) + PostgreSQL for all drivers (1M total), batch sync every 60s.

---

## Haversine Formula (Always Mention This)

```
a = sin²((lat2-lat1)/2) + cos(lat1) × cos(lat2) × sin²((lng2-lng1)/2)
c = 2 × atan2(√a, √(1−a))
distance = R × c        (R = 6371 km)
```

**Accuracy:** ±0.5% (assumes perfect sphere)  
**Vincenty:** ±0.5mm (accounts for ellipsoid) but 10× slower — used by PostGIS ST_Distance

### Bounding Box Pre-filter (The Key Optimization)
```sql
-- Step 1: cheap index scan eliminates 90% of rows
WHERE lat BETWEEN (user_lat - delta) AND (user_lat + delta)
  AND lng BETWEEN (user_lng - delta) AND (user_lng + delta)

-- delta = radius_km / 111   (1 degree ≈ 111 km)
-- 5km radius → delta = 0.045 degrees

-- Step 2: Haversine only for the survivors (~10% of data)
```
**Result:** 1M points → bounding box → 10K candidates → Haversine → < 10 ms total vs 1000 ms without.

---

## Production Hybrid Architecture

```
Write flow:
  Client → PostgreSQL (primary, ACID) → async indexer → Elasticsearch
                                      → hot locations cached → Redis

Query flow:
  Request → Redis GEORADIUS (< 5ms, 80% hits)
          → cache miss → Elasticsearch geo_distance (50ms, 95% hits)
          → miss or needs exact metadata → PostGIS ST_DWithin (100ms, 5%)
          → cache hot results back to Redis
```

| Tier | Store | Data | TTL | Latency |
|---|---|---|---|---|
| Hot cache | Redis Geo | Top 1000 active per city | 10 min | < 5 ms |
| Search layer | Elasticsearch | 100M+ docs with filters | — | ~50 ms |
| Source of truth | PostgreSQL PostGIS | All locations + metadata | — | ~100 ms |

**Real-time objects (drivers):** Update Redis every 5s, batch sync to PostgreSQL every 60s.  
**Invalidation on restaurant update:** Invalidate Redis keys + reindex Elasticsearch via Kafka event.

---

## Geographic Sharding

```
Strategy 1 — Geographic regions:
  US-West DB | US-East DB | EU DB | Asia DB
  Pros: Simple routing, isolated failures
  Cons: Unbalanced load (NYC >> Montana), cross-region queries

Strategy 2 — Geohash prefix sharding:
  Shard by first 2 geohash chars → 1024 prefixes → 16 shards
  Pros: Even distribution
  Cons: Radius query may span multiple shards

Strategy 3 — Hybrid (recommended):
  Shard by region first, then geohash prefix within region
```

**Query routing:**
- Small radius (< 10 km): hits 1–2 shards → fast
- Large radius (> 50 km): scatter-gather to 3–5 shards → merge by distance
- **Buffer zones:** Add 10 km overlap between shard boundaries to avoid cross-shard edge cases

---

## Key Numbers to Remember

| Metric | Value |
|---|---|
| Earth radius | 6371 km |
| 1° latitude | ≈ 111 km (constant) |
| 1° longitude | ≈ 111 km × cos(lat) (0 at poles) |
| Redis memory | ~50 bytes/point → 1M pts ≈ 50 MB |
| PostGIS GIST index | ~10–20% of table size |
| Elasticsearch geo_point | ~16 bytes/point |
| Redis capacity | ~10M points/instance |
| PostGIS capacity | 10M–100M per DB with GIST |
| Elasticsearch | Billions across cluster |

---

## Interview Questions & Model Answers

### Q1: Explain geohash and how to handle edge cases at cell boundaries.

**Answer:**
1. Interleave lat/lng bits → binary string → base32 → `'9q8yy9mz'` (SF, 8 chars ≈ ±19m)
2. **Proximity property:** Nearby locations share common prefix (key insight)
3. **Edge case:** Two points 50m apart on cell boundary: `'9q8yyzzz'` vs `'9q8z0000'` — different 5th char, completely different LIKE prefix
4. **Fix:** Always query 9 cells (center + 8 neighbors using geohash library)
5. **Post-filter:** Haversine on all 9-cell results to get exact circle

---

### Q2: QuadTree vs Geohash vs PostGIS — when to use each?

| | QuadTree | Geohash | PostGIS |
|---|---|---|---|
| Structure | 4-way recursive partition | Base32 prefix string | GEOGRAPHY type + GIST |
| Search | O(log N), prune subtrees | SQL LIKE + 9 cells | ST_DWithin + R-tree |
| Use case | In-memory, < 1M pts | Distributed, any SQL DB | ACID + complex shapes |
| Key pro | < 1ms | Works anywhere | Exact Vincenty |
| Key con | Not distributable | Returns box not circle | PG-only, harder to shard |

**Production:** Hybrid — Redis (hot) + Elasticsearch (search) + PostGIS (source of truth).

---

### Q3: Why Elasticsearch over PostgreSQL for proximity search?

**Elasticsearch:**
- Horizontally scalable — billions of points across cluster
- Combines proximity + full-text + facets in a single query
- ~10–50ms p95, auto-sharding

**PostgreSQL:**
- Single server bottleneck (~100ms)
- ACID guarantees — use as write source of truth
- Best for complex spatial operations (polygons, buffers)

**Answer:** Use both. ES for reads, PG for writes. Sync via async indexer.

---

### Q4: How do you optimize proximity search for 10M+ locations?

1. **Spatial index:** GIST (PostGIS), B-tree on geohash, Redis GEORADIUS — O(log N) vs O(N)
2. **Bounding box pre-filter:** `WHERE lat BETWEEN (lat-delta) AND (lat+delta)` eliminates 90% before Haversine
3. **Caching:** Redis GEORADIUS for hot locations (TTL=10min, serves 80% in < 5ms)
4. **Geographic sharding:** Partition by region, 5–10× per-shard reduction
5. **Result limit:** LIMIT 20 — user sees first page only, no point computing all 10K matches
6. **Read replicas:** Route geo queries to nearest regional replica

**Example:** 10M restaurants → geohash prefix filter → 10K → bounding box → 1K → Haversine → 200 in exact radius → top 20 → **50ms total** vs 5000ms unoptimized.

---

### Q5: How does Redis GEORADIUS work internally?

1. Stores data as **sorted set (ZSET)**, score = 52-bit geohash integer
2. `GEORADIUS`: compute geohash range for center+radius → `ZRANGEBYLEX` O(log N) → Haversine filter → sort
3. Updates are simple upserts (just `GEOADD` again)
4. **When to use:** Real-time moving objects, < 10ms latency, < 10M points, high read frequency (100K QPS)
5. **Don't use when:** Billions of points, complex filters, ACID persistence

---

### Q6: Design polygon-based search (restaurant delivery zone).

**PostGIS:**
```sql
SELECT * FROM restaurants
WHERE ST_Contains(ST_GeomFromGeoJSON('{"type":"Polygon","coordinates":[[...]]}'), location);
```

**Optimization:**
1. Bounding box of polygon first (WHERE lat BETWEEN min_lat AND max_lat) — eliminates 90%
2. Then exact `ST_Contains` — only for candidates
3. For static zones: pre-assign `zone_id` to each location → query becomes `WHERE zone_id = ?` (instant)
4. For complex polygons (1000+ vertices): use Douglas-Peucker to simplify to 100–200 vertices, 5–10× faster

---

## Common Traps to Avoid in Interviews

- **NEVER** use bare `lat/lng BETWEEN` without a spatial index — it's O(N), scans every row
- **NEVER** assume 1° lat = 1° lng in distance. Latitude = 111 km (constant); longitude = 111 km × cos(lat), varies by latitude
- **NEVER** compute Haversine for every row — always pre-filter with bounding box or geohash first
- **Always mention** geohash neighbor cells — 1 cell query silently misses points on boundaries
- **Always mention** the 3-tier hybrid: Redis (hot, fast) → Elasticsearch (search) → PostGIS (truth)
