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

## Functional Requirements

| # | Requirement |
|---|---|
| 1 | Users can search for nearby places (restaurants, hotels, POIs) within a radius |
| 2 | Users can filter results by category, rating, and open/closed status |
| 3 | Users can view full details of a specific place |
| 4 | Business owners can register and update their place listing |
| 5 | Users can submit and read reviews for a place |
| 6 | Users can report incorrect or outdated place information |
| 7 | Users can request directions from one location to another |

**Non-functional requirements:** < 100 ms search latency, 99.9% availability, eventual consistency on writes.

---

## API Design

### Search & Discovery

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/places/search` | Search nearby places |
| GET | `/api/v1/places/{place_id}` | Get full details of a place |
| GET | `/api/v1/directions` | Get directions between two points |

### Place Management (Business Owner)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/places` | Register a new place |
| PATCH | `/api/v1/places/{place_id}` | Update place details |

### Reviews

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/places/{place_id}/reviews` | Get all reviews for a place |
| POST | `/api/v1/places/{place_id}/reviews` | Submit a new review |

### Moderation

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/places/{place_id}/report` | Report incorrect or closed place |

---

### API Details

#### GET /api/v1/places/search

```
Query params:
  lat      (required) – user latitude
  lng      (required) – user longitude
  radius   (required) – search radius in km (default: 5, max: 50)
  category (optional) – e.g. restaurant, hotel, gas_station
  rating   (optional) – minimum rating (e.g. 4.0)
  limit    (optional) – max results (default: 20, max: 100)
  cursor   (optional) – pagination cursor for next page

Response 200:
{
  "places": [
    {
      "place_id": "abc123",
      "name": "Taco Bell",
      "category": "restaurant",
      "lat": 12.9716,
      "lng": 77.5946,
      "distance_km": 0.8,
      "rating": 4.2,
      "is_open": true
    }
  ],
  "next_cursor": "eyJsYXQ..."
}
```

#### GET /api/v1/places/{place_id}

```
Response 200:
{
  "place_id": "abc123",
  "name": "Taco Bell",
  "address": "MG Road, Bangalore",
  "lat": 12.9716,
  "lng": 77.5946,
  "category": "restaurant",
  "rating": 4.2,
  "review_count": 312,
  "phone": "+91-80-1234567",
  "hours": { "mon": "09:00-22:00", ... },
  "photos": ["https://cdn.example.com/abc123/1.jpg"]
}
```

#### POST /api/v1/places

```
Request body:
{
  "name": "New Cafe",
  "address": "100 Main St",
  "lat": 12.9800,
  "lng": 77.6000,
  "category": "cafe",
  "phone": "+91-80-9999999",
  "hours": { "mon": "08:00-21:00", ... }
}

Response 201: { "place_id": "xyz789", "status": "pending_review" }
```

#### PATCH /api/v1/places/{place_id}

```
Request body (only fields to update):
{
  "phone": "+91-80-1111111",
  "hours": { "sun": "10:00-20:00" },
  "is_permanently_closed": false
}

Response 200: { "place_id": "abc123", "updated": true }
```

#### GET /api/v1/places/{place_id}/reviews

```
Query params:
  limit  (optional) – default 20
  cursor (optional) – pagination

Response 200:
{
  "reviews": [
    {
      "review_id": "r001",
      "user_id": "u42",
      "rating": 5,
      "text": "Great tacos!",
      "created_at": "2024-03-15T12:00:00Z"
    }
  ],
  "next_cursor": "eyJyZXY..."
}
```

#### POST /api/v1/places/{place_id}/reviews

```
Request body:
{
  "rating": 4,
  "text": "Good but slow service."
}

Response 201: { "review_id": "r002", "status": "published" }
```

#### GET /api/v1/directions

```
Query params:
  from_lat, from_lng  – origin coordinates
  to_lat, to_lng      – destination coordinates
  mode                – driving | walking | cycling (default: driving)

Response 200:
{
  "distance_km": 3.2,
  "duration_min": 12,
  "polyline": "encoded_polyline_string",
  "steps": [ { "instruction": "Turn left onto MG Road", "distance_m": 400 } ]
}
```

#### POST /api/v1/places/{place_id}/report

```
Request body:
{
  "reason": "permanently_closed" | "wrong_location" | "duplicate" | "spam",
  "notes": "This place closed in January 2024."
}

Response 202: { "report_id": "rep001", "status": "under_review" }
```

> **WHY GET /api/v1/places/search?** This is the core read path — every proximity query flows through here. The `cursor` param enables efficient keyset pagination without OFFSET (OFFSET re-scans from row 1; a cursor picks up from the last seen distance value). The `radius` cap (50 km) prevents runaway scatter-gather across too many geo shards.

> **WHY GET /api/v1/places/{place_id}?** Search results return lightweight cards (name, distance, rating). A detail page fetches full metadata — photos, hours, phone — only when the user taps a card. This splits high-volume search traffic (millions/day) from lower-volume detail fetches, letting you cache detail responses aggressively with a longer TTL.

> **WHY POST /api/v1/places?** Without a write API, the dataset never grows. Business owners self-register via this endpoint; the `status: pending_review` response signals async moderation before the listing goes live, preventing spam from polluting search results.

> **WHY PATCH /api/v1/places/{place_id}?** Places change — hours shift, phone numbers change, businesses reopen. PATCH (not PUT) lets owners send only the changed fields, reducing payload size and avoiding accidental overwrites of fields they didn't intend to touch.

> **WHY GET /api/v1/places/{place_id}/reviews?** Reviews are high-read, low-write data that benefits from cursor-based pagination. Fetching them separately from place details avoids bloating the detail response when a place has thousands of reviews.

> **WHY POST /api/v1/places/{place_id}/reviews?** User-generated ratings drive ranking signals (average rating affects search ordering). Without a submit endpoint there is no feedback loop between user experience and search quality.

> **WHY GET /api/v1/directions?** Direction routing ties directly to the proximity use case — after finding a nearby place, the user needs to get there. In interviews, mentioning this shows you understand the full user journey (discover → select → navigate), not just the search algorithm.

> **WHY POST /api/v1/places/{place_id}/report?** Data quality degrades over time (businesses close, move, change category). The report endpoint creates a moderation queue that keeps the dataset accurate without requiring manual admin oversight of every listing. In interviews this signals you're thinking about data lifecycle, not just the happy path.

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

WHY NAIVE SQL ("WHERE lat BETWEEN x AND y") IS BAD? (Beginner Explanation)
  Imagine you want all restaurants within 5 km of you. The obvious SQL move is:
  WHERE lat BETWEEN 12.92 AND 13.02 AND lng BETWEEN 77.54 AND 77.64
  This looks fine but it scans EVERY ROW in the table — like checking every house on Earth
  to find your neighbors. With 10 million restaurants, that's 10 million comparisons per query.
  What problem it solves: You need a way to jump straight to the "right neighborhood" without
  reading all the other data first. That's exactly what spatial indexes (QuadTree, Geohash, GIST)
  do — they organize data by location so you only touch the rows that could possibly be nearby.
  Why the alternative is worse: No spatial index = O(N) full table scan on every query.
  With 10M rows at 100K QPS that's 1 trillion comparisons per second. The database melts.

---

## Approach 1 — QuadTree

WHY QUADTREE EXISTS? (Beginner Explanation)
  Imagine you're playing a game of "hot or cold" on a map. Instead of checking every spot,
  you cut the map in half: "Is the target in the left half or right half?" Then cut that half
  again: "Top or bottom?" You zoom in with only 4 choices at each step until you're right on it.
  A QuadTree does exactly this — it divides any area into 4 quadrants (NW, NE, SW, SE),
  then divides each quadrant into 4 more, recursively, until each box holds ≤ 100 points.
  What problem it solves: Finding nearby points without checking all points.
  Searching a QuadTree is like zooming into Google Maps — you skip entire continents
  in milliseconds and land right where the data is.
  Why the alternative is worse: A flat list of 1M points means 1M comparisons.
  The QuadTree prunes 75%+ of the map at every level — finding points in O(log N) instead.

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

WHY GEOHASH EXISTS? (Beginner Explanation)
  Think of a Geohash as a ZIP code for GPS coordinates. "94102" tells you "San Francisco downtown"
  without knowing the exact street address. Similarly, Geohash '9q8yy' tells you "this point is
  in SF" and '9q8yy9mz' tells you "this specific building in SF."
  The magic trick: nearby places share the same prefix. All restaurants in downtown SF start
  with '9q8yy...'. So instead of doing trigonometry on millions of lat/lng pairs, you just do
  a string prefix match — something any database index can do instantly.
  What problem it solves: Converts 2D coordinates (lat, lng) into a 1D string that a regular
  B-tree index can sort and search. No special spatial extension needed.
  Why the alternative is worse: Raw lat/lng requires math on every row (Haversine formula).
  Geohash turns spatial proximity into string comparison — trivially indexable in any SQL DB.

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

WHY GEOHASH PRECISION LEVELS MATTER? (Beginner Explanation)
  A short Geohash is like a country-level ZIP code — '9' means "somewhere in North America."
  A long Geohash is like a full postal address — '9q8yy9mz' means "this specific building."
  Length 3 = city-sized box (156 km). Length 6 = street-sized box (609 m). Length 9 = your desk.
  For a 5 km search radius, you pick length 5 (4.9 km cells) — the cell is roughly as big as
  your search area. Too short and you pull in half the country. Too long and your circle spills
  across so many tiny cells that you need hundreds of DB queries to cover it.
  What problem it solves: Balancing query coverage vs. over-fetching. You want the fewest
  cells that still contain all possible results within your radius.
  Why the alternative is worse: Using length-9 precision for a 5 km search means ~1000 tiny
  cells to query. Using length-2 for a 500 m search means fetching an entire region.

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

WHY YOU MUST CHECK NEIGHBORING GEOHASH CELLS? (Beginner Explanation)
  Picture a city divided into square blocks. You live on the corner of two blocks.
  Your nearest neighbor lives across the street — technically in a different block.
  If you only look inside your own block, you miss them entirely.
  Geohash cells have the same problem: two points can be 50 meters apart but have completely
  different hash strings because they sit on opposite sides of a cell boundary.
  '9q8yyzzz' and '9q8z0000' look nothing alike as strings, but are only steps apart on the map.
  What problem it solves: A single-cell query silently misses points at the edges.
  Querying all 9 cells (your cell + 8 surrounding ones) guarantees no nearby point is missed.
  Why the alternative is worse: Single-cell queries produce mysterious missing results —
  the kind of bug that's nearly impossible to debug without knowing this gotcha.

### Pros / Cons
| Pros | Cons |
|---|---|
| Works with any SQL DB (no extensions) | Returns square box, not circle → must post-filter |
| Easy to shard (by geohash prefix) | Edge case requires 9-cell queries |
| Human-readable, shareable in URLs | Cell size varies by latitude |

---

## Approach 3 — PostgreSQL + PostGIS

WHY POSTGIS EXISTS? (Beginner Explanation)
  PostgreSQL is a filing cabinet. It's great at storing and querying rows of data.
  But it has no idea what a "circle on a map" means — it only knows numbers and strings.
  PostGIS is a spatial superpower bolt-on to PostgreSQL. It teaches PostgreSQL to understand
  shapes: points, lines, polygons, circles. It adds functions like ST_DWithin ("is this point
  within 5 km of that point?") and ST_Contains ("is this restaurant inside this delivery zone?").
  Under the hood it adds a GIST index — a special R-tree structure that groups nearby shapes
  together so queries skip irrelevant regions, same idea as a QuadTree but for disk-based data.
  What problem it solves: You want ACID-safe, exact-distance, polygon-capable geo queries
  in the same database that holds the rest of your relational data.
  Why the alternative is worse: Plain SQL can't do "find all points inside a polygon."
  You'd have to pull millions of rows into application code and filter there — catastrophic.

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

WHY ELASTICSEARCH GEO_POINT EXISTS? (Beginner Explanation)
  Elasticsearch is the search engine that powers "find pizza restaurants nearby, sorted by rating,
  open right now." It already knows how to do blazing-fast full-text search across billions of docs.
  geo_point is a special field type that tells Elasticsearch: "this field holds a GPS coordinate."
  Internally it uses a BKD tree (block k-d tree) — a disk-friendly spatial index that narrows down
  candidates by location in O(log N), similar to a QuadTree but optimized for SSDs at massive scale.
  The killer feature: you can combine geo_distance ("within 5 km") with text search ("pizza")
  and filters (rating >= 4, is_open = true) in a SINGLE query. PostgreSQL + PostGIS can't do
  full-text search. Redis can't do rating filters. Elasticsearch does all of it together.
  What problem it solves: "Find the nearest open pizza place with rating >= 4" as one fast query.
  Why the alternative is worse: Two separate systems (one for text, one for geo) means
  joining results in application code — slow, complex, and hard to sort by distance + relevance.

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

WHY REDIS GEORADIUS EXISTS? (Beginner Explanation)
  Redis is a sticky note on the fridge — everything is in RAM, so reads are nearly instant.
  PostgreSQL is the filing cabinet in the basement — reliable and thorough, but you have to
  walk downstairs and dig through folders. For a moving Uber driver pinging their location
  every 5 seconds, you can't afford a basement trip on every update and every query.
  Redis stores all driver positions as a sorted set in memory — a geohash integer as the score.
  GEORADIUS asks: "who is within 5 km of this point?" and gets the answer in ~1 ms because
  it never touches disk. Updates are just GEOADD calls — upsert in O(log N) with no locking.
  What problem it solves: Real-time, high-frequency location updates and queries where
  even 50 ms latency is too slow (Uber showing you the nearest driver in < 1 second).
  Why the alternative is worse: PostgreSQL at 100 ms × 100K driver pings/sec = database meltdown.
  Redis at 1 ms × 100K pings/sec = comfortable. The tradeoff is memory cost and no complex filters.

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

WHY BOUNDING BOX VS RADIUS SEARCH MATTERS? (Beginner Explanation)
  A radius search is a circle: "find everything within exactly 5 km of me." Mathematically clean,
  but computing exact circle membership requires the Haversine formula on every candidate row.
  A bounding box search is a square: "find everything inside this lat/lng rectangle." Much cheaper —
  just four comparisons (lat >= min AND lat <= max AND lng >= min AND lng <= max). Any B-tree index
  handles this instantly. The catch: the square's corners are farther than the radius, so you get
  extra false positives (points in the corners of the box but outside the circle).
  The standard pattern: bounding box first (fast, gets ~10% of data), then Haversine only on
  those survivors (exact, but on a tiny subset). You get circle accuracy at bounding-box speed.
  What problem it solves: Computing Haversine on 10M rows is slow. Computing it on 10K is fast.
  Why the alternative is worse: Haversine-only = 1000ms. Bounding box only = fast but imprecise.
  Two-step = < 10ms and exact. Always use both.

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

---

## KEY PATTERNS REFERENCED IN THIS DESIGN

> **For the 2-year developer:** These are the hidden concepts behind design decisions in this system. Each has a dedicated deep-dive file.

### Index Types
**Why it matters here:** Spatial index (R-Tree in MySQL, GiST in PostgreSQL) for "find restaurants within 5km" — standard B-tree can't handle 2D coordinates. Without spatial index: full table scan of all restaurants in the city. With GiST index: O(log N + K) bounding-box intersection query.
**Deep dive:** `../../Index_Types_BTree_Hash_Composite_Covering.md`

### CAP Theorem
**Why it matters here:** Proximity search is AP — showing a restaurant that's technically 5.1km away instead of 5km due to slightly stale location data is acceptable. Availability of search results is paramount; a 1-second stale driver position is invisible to users.
**Deep dive:** `../../CAP_Theorem_Applied_What_Actually_Breaks.md`

### Cursor Pagination
**Why it matters here:** "Show restaurants near me, page 3." At high restaurant density (NYC), thousands of results. Offset pagination scans all preceding results. Cursor on (distance, restaurant_id) enables direct index seek to the next page position.
**Deep dive:** `../../Cursor_Pagination_vs_Offset_Pagination.md`

### [Geohash vs QuadTree Map Partitioning](../../Geohash_vs_QuadTree_Map_Partitioning.md)
**Why this system uses it:** The entire system is built around spatial queries. PostgreSQL PostGIS with GiST index for persistent storage: `ST_DWithin(business.location, $user_location, $radius_meters)` returns all businesses within radius. For in-memory proximity service: Redis GEOADD/GEORADIUS for sub-millisecond driver/business lookups. Database sharding by geohash prefix: all businesses with geohash prefix "dr5" (NYC area) go to the same DB shard — range queries within a city hit one shard.

### [Inverted Index — How Elasticsearch Works](../../Inverted_Index_How_Elasticsearch_Works.md)
**Why this system uses it:** Combined search: "find Italian restaurants near me with good reviews" requires full-text search on business name/cuisine + geo-proximity filter. Elasticsearch `geo_point` field type + BM25 scoring on name/category. Query: `bool filter [geo_distance: 5km] must [match: "italian restaurant"]` — ES evaluates geo filter first (fast), then scores matching documents by text relevance. 50M businesses indexed in ES; query returns top 10 in <50ms.

### [BM25 vs Vector Search](../../BM25_vs_Vector_Search_Semantic_Similarity.md)
**Why this system uses it:** Combined search: "find vegan restaurants near me with good ambiance." BM25 matches "vegan" and "restaurants" in business names/categories. Vector search matches "good ambiance" to businesses with reviews mentioning "cozy," "romantic," "great atmosphere." Hybrid Elasticsearch query: `geo_distance` filter (proximity) + `match` on business name/category (BM25) + `knn` on review embeddings (vector). The geo filter runs first (fast), reducing the candidate set; BM25 + vector rank the filtered results.

### [Elasticsearch vs PostgreSQL Full-Text](../../Elasticsearch_vs_PostgreSQL_Full_Text_Search.md)
**Why this system uses it:** The proximity search system combines spatial queries (PostGIS) with full-text search (business name, category, reviews). Elasticsearch handles both: `geo_distance` filter + `match` query in one request. PostgreSQL + PostGIS handles spatial queries extremely well but adding full-text search on top (pg_tsvector) requires joining two separate index scans — slower than ES's native combined query. For a system where search IS the core feature, Elasticsearch as the query layer (with PostgreSQL as the write source via CDC) is the right choice.
