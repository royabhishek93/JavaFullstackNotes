Proximity Search Algorithm (Find Nearby Restaurants/Drivers)

"QuadTree/Geohash spatial indexing → PostgreSQL PostGIS (GIST) → Elasticsearch geo_distance → Redis GEORADIUS → Haversine distance"

1. Problem Statement

Goal: Find all points of interest (restaurants, drivers, hotels) within radius R of user location (lat, lng)
Example: User at (37.7749, -122.4194) searches 5km radius → return all restaurants within 5km sorted by distance
Requirements: <100ms query latency, support millions of locations, accurate distance calculations
Use cases: Uber (find drivers), Yelp (find restaurants), Airbnb (find hotels), Google Maps (nearby POIs)
2. Five Main Approaches

Approach 1: QuadTree - Recursive grid subdivision into 4 quadrants, in-memory spatial index
Approach 2: Geohash - Encode lat/lng as base32 string, prefix matching with SQL LIKE queries
Approach 3: PostgreSQL with PostGIS - GEOGRAPHY type, ST_DWithin for radius, GIST spatial index
Approach 4: Elasticsearch - Distributed search with geo_point mapping and geo_distance filter
Approach 5: Redis Geospatial - In-memory GEORADIUS command for real-time moving objects
3. Approach 1: QuadTree

QuadTree Structure
Concept: Recursively divide 2D space into 4 quadrants (NW, NE, SW, SE) until each cell contains ≤ max_capacity points (e.g., 100 points per leaf node)
Tree structure: Each internal node has 4 children, leaf nodes store actual location points
Example: World map → divide into 4 quadrants → each quadrant divides into 4 → continues until depth limit (e.g., 20 levels) or capacity reached
Bounding box: Each node stores min/max lat/lng defining its geographic bounds
Search Algorithm
Input: Query point (lat, lng) and radius R
Step 1: Start at root node, check if search circle intersects node's bounding box
Step 2: If yes, recursively search all 4 children; if no, prune entire subtree (skip)
Step 3: At leaf nodes, collect all points and calculate exact distance using Haversine formula
Step 4: Filter points where distance ≤ R, sort by distance, return top N results
Time complexity: O(log N + K) where K is number of results, pruning eliminates 75%+ of tree
Insertion & Updates
Insert: Find appropriate leaf node by traversing tree based on coordinates, add point to leaf
Split: If leaf exceeds capacity (100 points), split into 4 children, redistribute points
Update: For moving objects (drivers), remove old location, insert new location (2 operations)
Delete: Mark point as deleted, periodically rebuild tree to reclaim space
Pros & Cons
Pros: (1) Fast queries O(log N) for balanced tree, (2) Efficient for sparse data, (3) Easy to implement in-memory, (4) Good for dynamic data (frequent inserts/deletes)
Cons: (1) Not suitable for distributed systems (tree on single server), (2) Memory overhead for internal nodes, (3) Tree rebalancing on splits, (4) Lost on server restart unless persisted
Best for: Game engines, in-memory caches for hot regions, <1M points on single server
Not for: Production databases (use PostGIS), billions of points (use Elasticsearch), distributed systems
4. Approach 2: Geohash

Geohash Encoding Algorithm
Step 1: Interleave latitude and longitude bits - lat=37.7749 (binary: 01011010...), lng=-122.4194 (binary: 10011101...) → interleave → 0110011101010...
Step 2: Convert binary to base32 (0-9, a-z excluding a, i, l, o) → '9q8yy' for San Francisco
Example: SF (37.7749, -122.4194) → geohash='9q8yy9mz' (8 characters)
Precision: Length 1 = ±2500km, 3 = ±78km, 5 = ±2.4km, 7 = ±76m, 9 = ±2m (see table in image)
Proximity Property
Key property: Nearby locations share common prefix
Example: '9q8yy9mz' (SF downtown), '9q8yy9mt' (1 block away) → share prefix '9q8yy9m'
Hierarchical: Zoom levels on maps - zoom out → use shorter prefix (9q8 = SF area), zoom in → longer prefix (9q8yy9m = street level)
This enables efficient SQL queries with LIKE operator on indexed geohash column
Database Schema & Query
Schema: CREATE TABLE restaurants (id SERIAL, name VARCHAR, lat DECIMAL, lng DECIMAL, geohash VARCHAR(12))
Index: CREATE INDEX idx_geohash ON restaurants (geohash)
Query: SELECT * FROM restaurants WHERE geohash LIKE '9q8yy%' (returns all in ~2.4km box)
Radius to precision: 500m → use 6 chars (±610m), 2km → 5 chars (±2.4km), 5km → 4 chars (±20km)
Edge Case: Neighbor Cells
Problem: Two points 50m apart on geohash boundary have different prefixes → query misses one
Example: Point A: '9q8yyzzz', Point B: '9q8z0000' (different 5th character, but only 50m apart)
Solution: Calculate 8 neighboring geohash cells (N, NE, E, SE, S, SW, W, NW) using geohash library
Query expansion: WHERE geohash IN ('9q8yy', '9q8yz', '9q8yx', '9q8yw', '9q8yv', '9q8yt', '9q8ys', '9q8yq', '9q8yu') (9 cells total)
Post-filter: Calculate exact Haversine distance for all results, filter to points actually within circular radius
Pros & Cons
Pros: (1) Simple SQL with B-tree index (no special extensions), (2) Works with any database (MySQL, PostgreSQL, MongoDB), (3) Human-readable (can share geohash in URLs), (4) Hierarchical for zoom levels
Cons: (1) Returns square area not circle (must post-filter), (2) Edge case requires 9 cell queries, (3) Approximate (not exact distance), (4) Geohash cell size varies by latitude
Best for: Simple databases without spatial extensions, distributed systems (easy to shard), approximate searches
Example query: SELECT * FROM restaurants WHERE geohash LIKE '9q8yy%' → 500 candidates → Haversine filter → 200 within exact 5km radius
5. Approach 3: PostgreSQL with PostGIS

PostGIS Setup
Install extension: CREATE EXTENSION postgis;
Data type: GEOGRAPHY(POINT, 4326) for lat/lng on sphere (accurate distances in meters) or GEOMETRY for planar coordinates (faster but less accurate)
SRID 4326: WGS 84 coordinate system (standard GPS coordinates)
Example: CREATE TABLE restaurants (id SERIAL, name VARCHAR, location GEOGRAPHY(POINT, 4326))
Spatial Index: GIST
Create index: CREATE INDEX idx_location ON restaurants USING GIST (location)
GIST: Generalized Search Tree, creates R-tree structure, groups nearby points into bounding boxes hierarchically
Index structure: Root node → bounding box covering all points → children cover subregions → leaves contain individual points
Query optimization: Index scan O(log N) instead of sequential scan O(N)
Radius Query with ST_DWithin
Insert data: INSERT INTO restaurants (name, location) VALUES ('Taco Bell', ST_GeomFromText('POINT(77.5946 12.9716)', 4326))
Query: SELECT name, ST_Distance(location, ST_GeogFromText('SRID=4326;POINT(77.6080 12.9700)')) AS distance FROM restaurants WHERE ST_DWithin(location, ST_GeogFromText('SRID=4326;POINT(77.6080 12.9700)'), 5000) ORDER BY distance LIMIT 20
ST_DWithin: Pre-filter using bounding box (fast), then exact distance check (slower but accurate)
ST_Distance: Returns distance in meters for GEOGRAPHY type, uses Vincenty formula (accurate to ±0.5mm)
Performance: ~50-100ms for 10M points with GIST index
Polygon & Complex Shapes
Polygon search: SELECT * FROM restaurants WHERE ST_Contains(ST_GeomFromGeoJSON('{polygon}'), location)
Use case: Find restaurants in specific neighborhood, delivery zones with irregular boundaries
GeoJSON polygon: { 'type': 'Polygon', 'coordinates': [[[lng1, lat1], [lng2, lat2], [lng3, lat3], [lng1, lat1]]] }
ST_Intersects: Check if point intersects with line/polygon
ST_Buffer: Create buffer zone around point/line (e.g., 100m buffer around road)
Pros & Cons
Pros: (1) Exact distance calculations (Vincenty formula), (2) ACID guarantees, (3) Complex spatial queries (polygons, buffers, intersections), (4) Mature ecosystem, well-documented
Cons: (1) PostgreSQL-specific (not portable), (2) Single server bottleneck (harder to shard), (3) Slower than Redis for real-time, (4) Requires extension install
Best for: Source of truth for location data, static locations (restaurants, hotels), complex spatial operations
Scaling: Shard by region (US-West DB, US-East DB), read replicas for queries
6. Approach 4: Elasticsearch Geo Queries

Index Mapping Setup
Create index: PUT /restaurants { 'mappings': { 'properties': { 'location': { 'type': 'geo_point' }, 'name': { 'type': 'text' }, 'category': { 'type': 'keyword' }, 'rating': { 'type': 'float' } } } }
geo_point: Stores lat/lng, automatically creates spatial index (BKD tree internally)
Index document: POST /restaurants/_doc { 'name': 'Taco Bell', 'location': { 'lat': 12.9716, 'lon': 77.5946 }, 'category': 'Fast Food', 'rating': 4.2 }
Geo Distance Query
Basic query: GET /restaurants/_search { 'query': { 'geo_distance': { 'distance': '5km', 'location': { 'lat': 12.97, 'lon': 77.59 } } } }
Sort by distance: 'sort': [ { '_geo_distance': { 'location': { 'lat': 12.97, 'lon': 77.59 }, 'order': 'asc', 'unit': 'km' } } ]
Response includes: { '_source': { 'name': 'Taco Bell' }, 'sort': [ 0.5 ] } (0.5 km distance)
Distance units: km, mi, m (meters), ft (feet)
Combined Filters (Proximity + Text + Facets)
Complex query: { 'query': { 'bool': { 'must': [ { 'match': { 'name': 'pizza' } } ], 'filter': [ { 'geo_distance': { 'distance': '5km', 'location': {...} } }, { 'term': { 'category': 'Italian' } }, { 'range': { 'rating': { 'gte': 4.0 } } } ] } } }
Query execution: (1) Full-text search on 'pizza' → 10K candidates, (2) Filter by category → 2K, (3) Filter by rating → 1K, (4) geo_distance → 50 results
Aggregations: 'aggs': { 'distance_buckets': { 'geo_distance': { 'field': 'location', 'origin': {...}, 'ranges': [ {'to': 1}, {'from': 1, 'to': 3}, {'from': 3, 'to': 5} ] } } } → returns count per distance bucket
Use case: 'Pizza restaurants within 5km, rating ≥4.0, categorized by distance ranges'
Geo Bounding Box (Faster for Large Results)
Query: { 'query': { 'geo_bounding_box': { 'location': { 'top_left': { 'lat': 13.0, 'lon': 77.5 }, 'bottom_right': { 'lat': 12.9, 'lon': 77.7 } } } } }
Faster than geo_distance for rectangular areas (no distance calculation)
Use case: Find all restaurants on map viewport (when user scrolls map)
Optimization: Use geo_bounding_box to get candidates, then geo_distance for exact circular radius
Pros & Cons
Pros: (1) Horizontally scalable (shard across nodes), (2) Combine proximity + full-text search, (3) Fast aggregations/facets, (4) ~10-50ms latency for 100M documents
Cons: (1) Eventual consistency (~1s refresh interval), (2) More expensive (memory intensive), (3) Complex setup, (4) No ACID guarantees
Best for: Search engines (Yelp, Google Maps), complex filtering, billions of documents, read-heavy workloads
Scaling: Auto-shards based on document count, can scale to petabytes of data
7. Approach 5: Redis Geospatial

Redis Geo Commands
Add location: GEOADD drivers 77.5946 12.9716 'driver_1' 77.6000 12.9800 'driver_2' → stores in sorted set with geohash as score
Search radius: GEORADIUS drivers 77.5900 12.9700 5 km WITHDIST ASC COUNT 10 → returns [('driver_1', '0.5 km'), ('driver_2', '1.2 km')]
Search by member: GEORADIUSBYMEMBER drivers 'driver_1' 2 km → find all drivers within 2km of driver_1
Get position: GEOPOS drivers 'driver_1' → returns [(77.5946, 12.9716)]
Distance between: GEODIST drivers 'driver_1' 'driver_2' km → returns 1.2 (km)
Update & Delete
Update location: Just GEOADD again with new coordinates (upsert operation)
Example: Driver moves → GEOADD drivers 77.6100 12.9850 'driver_1' → updates existing entry
Delete: ZREM drivers 'driver_1' (geospatial data stored as sorted set internally)
Expire: Set TTL on key → EXPIRE drivers:online 3600 (auto-delete after 1 hour if no updates)
Performance & Scaling
Time complexity: O(log N + M) where N = total points, M = results returned
Latency: ~1ms for 10K points, ~5ms for 100K points, ~10ms for 1M points (all in-memory)
Memory: ~50 bytes per point (lat, lng, member name, geohash) → 1M points ≈ 50MB
Sharding: Use multiple Redis instances, shard by region or geohash prefix (drivers:sf, drivers:nyc)
Persistence: Use RDB snapshots or AOF for durability, but typically used for ephemeral hot data
Pros & Cons
Pros: (1) Fastest queries <10ms, (2) Real-time updates (drivers moving), (3) Simple API, (4) Perfect for hot/ephemeral data
Cons: (1) In-memory only (expensive for millions of points), (2) No complex filtering, (3) Data lost on restart (unless persisted), (4) Limited query capabilities
Best for: Real-time moving objects (Uber drivers, delivery agents), active sessions, frequently accessed locations
Hybrid approach: Redis for hot data (active drivers) + PostgreSQL for cold data (all drivers) + sync every 60s
8. Haversine Distance Formula

Formula & Implementation
Haversine formula: Calculates great-circle distance between two points on sphere (Earth)
Formula: a = sin²(Δlat/2) + cos(lat1) × cos(lat2) × sin²(Δlng/2), c = 2 × atan2(√a, √(1−a)), distance = R × c
R = Earth's radius: 6371 km (or 3959 miles)
Example: SF (37.7749, -122.4194) to LA (34.0522, -118.2437) → Haversine → 559 km
Accuracy: ±0.5% error (assumes perfect sphere, Earth is actually oblate spheroid)
Optimization: Bounding Box Pre-filter
Problem: Computing Haversine for 1M points takes ~1 second CPU time
Solution: Pre-filter with bounding box → eliminate 90% of points → Haversine only for 10%
Bounding box: WHERE lat BETWEEN (user_lat - delta) AND (user_lat + delta) AND lng BETWEEN (user_lng - delta) AND (user_lng + delta)
Delta calculation: delta ≈ radius_km / 111 (rough conversion: 1 degree ≈ 111 km)
Example: 5km radius → delta = 5/111 ≈ 0.045 degrees → bounding box filters from 1M to 10K → Haversine for 10K → <10ms
Alternatives
Vincenty formula: More accurate (accounts for ellipsoid), ±0.5mm error, but 10x slower computation
Euclidean distance: sqrt((x2-x1)² + (y2-y1)²), only for small areas on flat projection, very fast but inaccurate for large distances
Manhattan distance: |x2-x1| + |y2-y1|, rough approximation, useful for quick filtering before exact calculation
Database functions: PostGIS ST_Distance (uses Vincenty for GEOGRAPHY), Elasticsearch (uses Haversine), Redis GEODIST (Haversine)
9. Approach Comparison

Decision Matrix
QuadTree — When: In-memory single server, <1M points, game engines | Latency: <1ms | Accuracy: Exact | Complexity: High | Scaling: Vertical only
Geohash — When: Simple SQL database, distributed system, approximate OK | Latency: 10-50ms | Accuracy: Approximate (box) | Complexity: Low | Scaling: Easy (shard by prefix)
PostGIS — When: Static data, ACID needed, complex queries | Latency: 50-100ms | Accuracy: Exact (Vincenty) | Complexity: Medium | Scaling: Moderate (shard by region)
Elasticsearch — When: Billions of points, text+proximity search | Latency: 10-50ms | Accuracy: Exact (Haversine) | Complexity: Medium | Scaling: Excellent (horizontal)
Redis Geo — When: Real-time moving objects, hot data | Latency: <10ms | Accuracy: Exact (Haversine) | Complexity: Low | Scaling: Good (shard by region)
10. Production Hybrid Architecture

Tier 1 - Redis (Hot Cache): Top 1000 active/popular locations per city, TTL=10 min, serves 80% of queries in <5ms, GEORADIUS for real-time
Tier 2 - Elasticsearch (Search Layer): 100M+ documents, complex filters (category, rating, text search), ~50ms latency, handles cache misses with complex requirements
Tier 3 - PostgreSQL PostGIS (Source of Truth): All locations, detailed metadata, ~100ms latency, handles writes and rare queries, ACID guarantees
Write flow: Client updates location → PostgreSQL (primary) → async indexer → Elasticsearch → hot locations cached in Redis
Query flow: Check Redis cache → if miss, query Elasticsearch with filters → if still miss or need exact metadata, query PostGIS → cache hot results in Redis
Real-time updates: Moving objects (drivers) update Redis every 5s, batch sync to PostgreSQL every 60s
Invalidation: On restaurant update → invalidate Redis keys, reindex in Elasticsearch via Kafka event stream
11. Common Interview Questions

Q
Explain geohash and how to handle edge cases at cell boundaries.
A
Geohash encoding:

(1) Interleave lat/lng bits → binary string → convert to base32 → 'sgkztus' (7 chars ≈ ±76m),

(2) Precision table: length 5 = ±2.4km, length 7 = ±76m, length 9 = ±2m. Proximity property: Nearby locations share common prefix ('sgkztus', 'sgkztur' both in SF area). Edge case problem: Two points 50m apart on cell boundary have different hashes ('sgkztzzz' vs 'sgku000' - different 5th char). Solution:

(1) Calculate 8 neighbor geohash cells using library (N, NE, E, SE, S, SW, W, NW),

(2) Query all 9 cells (center + 8 neighbors): WHERE geohash IN ('sgkzt', 'sgkzu', 'sgkzs', ...) - 9 total,

(3) Post-filter with Haversine to get exact circular radius. Optimization: Use larger geohash precision (fewer chars) to get bigger box that definitely contains circle, then filter. Example: 5km radius → use precision 5 (±2.4km cell) → single query → Haversine filter → exact results.

Q
Compare QuadTree vs Geohash vs PostGIS - when to use each?
A
QuadTree:

(1) Structure: Recursive 4-way partitioning, each node has NW/NE/SW/SE children,

(2) Search: O(log n) traversal, prune subtrees that don't intersect search circle,

(3) Use: In-memory single server (<1M points), game engines, dynamic data,

(4) Pros: Fast (<1ms), easy updates,

(5) Cons: Not distributable, lost on restart, complex implementation. Geohash:

(1) Encoding: Lat/lng → base32 string, prefix matching,

(2) Search: SQL LIKE 'prefix%' with B-tree index, query 9 cells (center + 8 neighbors),

(3) Use: Simple SQL databases, distributed systems, approximate OK,

(4) Pros: Works with any DB, easy to shard, human-readable,

(5) Cons: Returns box not circle, edge cases. PostGIS:

(1) Extension: GEOGRAPHY type, ST_DWithin for radius, GIST spatial index,

(2) Search: O(log n) with R-tree, exact Vincenty distance,

(3) Use: Static data, ACID needed, complex shapes (polygons),

(4) Pros: Exact distance, mature, complex queries,

(5) Cons: PostgreSQL-only, harder to shard, ~100ms latency. Decision: QuadTree for single-server in-memory, Geohash for distributed approximate, PostGIS for ACID + exact distance. Production: Hybrid - Redis Geo (hot data) + Elasticsearch (search) + PostGIS (source of truth).

Q
How do you optimize proximity search for millions of locations?
A
Multi-layer optimization:

(1) Spatial indexing: Use GIST index (PostGIS), B-tree on geohash, or Redis GEORADIUS - reduces from O

(n) scan to O(log n) lookup,

(2) Bounding box pre-filter: Calculate lat/lng bounds, WHERE lat BETWEEN (lat-delta) AND (lat+delta) AND lng BETWEEN (lng-delta) AND (lng+delta), eliminates 90% before expensive distance calc, delta = radius_km / 111,

(3) Caching: Redis cache for hot locations (top 1000 per city), TTL=10 min, serves 80% queries in <5ms,

(4) Geographic sharding: Partition by region (US-West, US-East, EU) or geohash prefix, reduces per-shard dataset by 5-10x,

(5) Materialized views: Pre-compute popular queries (restaurants by city + 5km radius), refresh hourly,

(6) Read replicas: PostgreSQL replicas in each region for geo queries, route to nearest replica,

(7) Lazy distance calc: Return top N by bounding box first, calculate exact distance only for displayed results,

(8) Result limit: LIMIT 20 instead of returning all matches (user only sees first page anyway). Example: 10M restaurants → geohash prefix filter → 10K candidates → bounding box → 1K candidates → Haversine → 200 within exact radius → sort → return top 20 → total latency 50ms vs 5000ms without optimization.

Q
Implement proximity search with PostgreSQL PostGIS - show schema and query.
A
Setup:

(1) Install: CREATE EXTENSION postgis;,

(2) Schema: CREATE TABLE restaurants (id SERIAL PRIMARY KEY, name VARCHAR

(255), location GEOGRAPHY(POINT, 4326), category VARCHAR

(100), rating DECIMAL(2,1)),

(3) Index: CREATE INDEX idx_location_gist ON restaurants USING GIST (location),

(4) Insert: INSERT INTO restaurants (name, location, category, rating) VALUES ('Taco Bell', ST_GeomFromText('POINT(77.5946 12.9716)', 4326), 'Fast Food', 4.2). Query: SELECT id, name, category, rating, ST_Distance(location, ST_GeogFromText('SRID=4326;POINT(77.6080 12.9700)')) AS distance_meters FROM restaurants WHERE ST_DWithin(location, ST_GeogFromText('SRID=4326;POINT(77.6080 12.9700)'), 5000) AND category = 'Fast Food' AND rating >= 4.0 ORDER BY distance_meters LIMIT 20; Explanation:

(1) ST_GeogFromText: Creates geography point from user location (77.6080, 12.9700),

(2) ST_DWithin: Pre-filters using bounding box, then exact distance check ≤ 5000 meters,

(3) ST_Distance: Calculates exact distance in meters using Vincenty formula,

(4) GIST index: Enables O(log n) spatial lookup,

(5) Additional filters: category and rating for combined search,

(6) Performance: ~50-100ms for 10M rows. Alternative using geometry (faster but less accurate): Change GEOGRAPHY to GEOMETRY, use ST_MakePoint(lng, lat) instead of ST_GeomFromText, distance in degrees not meters.

Q
How does Redis GEORADIUS work internally and when should you use it?
A
Internal implementation:

(1) Data structure: Redis stores geospatial data as sorted set (ZSET), score = geohash of location, member = location ID,

(2) Geohash encoding: Internally encodes lat/lng to 52-bit geohash integer,

(3) GEORADIUS algorithm:

(a) Calculate geohash of center point,

(b) Determine geohash prefix range for radius,

(c) ZRANGEBYLEX to get all members in geohash range (O(log n)),

(d) Calculate exact Haversine distance for each candidate,

(e) Filter to points within radius, sort by distance,

(4) Time complexity: O(log n + m) where m = results. Commands:

(1) GEOADD key lng lat member: Add/update location,

(2) GEORADIUS key lng lat radius km WITHDIST ASC COUNT 10: Search circle, return distance sorted,

(3) GEORADIUSBYMEMBER key member radius km: Find neighbors of existing member,

(4) GEODIST key member1 member2 km: Distance between two members. When to use:

(1) Real-time moving objects (drivers, delivery agents update every 5s),

(2) Hot/ephemeral data (active sessions, current locations),

(3) <10ms latency requirement,

(4) <10M points (memory constraint),

(5) High read frequency (100K queries/sec). Don't use for:

(1) Billions of points (too expensive in RAM),

(2) Complex filtering (category, rating) - use Elasticsearch,

(3) ACID persistence - use PostGIS. Hybrid pattern: Redis for active drivers (10K online) + PostgreSQL for all drivers (1M total), sync every 60s.

Q
How do you calculate Haversine distance and why use bounding box pre-filter?
A
Haversine formula:

(1) Purpose: Calculate great-circle distance between two points on sphere (Earth),

(2) Inputs: Point A (lat1, lng1), Point B (lat2, lng2), Earth radius R = 6371 km,

(3) Formula: a = sin²((lat2-lat1)/2) + cos(lat1)·cos(lat2)·sin²((lng2-lng1)/2), c = 2·atan2(√a, √(1-a)), distance = R·c,

(4) Implementation: Convert degrees to radians (multiply by π/180), apply trig functions, result in km,

(5) Example: SF (37.7749, -122.4194) to LA (34.0522, -118.2437): Δlat = -3.7227 rad, Δlng = 4.1757 rad → a = 0.0382 → c = 0.391 → distance = 6371 × 0.391 = 559 km. Accuracy: ±0.5% error (assumes sphere, Earth is ellipsoid). Bounding box optimization:

(1) Problem: Computing Haversine for 1M points = 1M trig calculations = ~1 second CPU time,

(2) Solution: Pre-filter with simple lat/lng range check: WHERE lat BETWEEN (user_lat - delta) AND (user_lat + delta) AND lng BETWEEN (user_lng - delta) AND (user_lng + delta),

(3) Delta: delta = radius_km / 111 (rough: 1 degree ≈ 111 km), for 5km radius → delta = 0.045 degrees,

(4) Effect: Eliminates 90-95% of points using index scan (fast),

(5) Final step: Haversine only for remaining 5-10% → total time <10ms. Example: 1M points, 5km radius → bounding box reduces to 10K candidates → Haversine for 10K → <10ms vs 1000ms without optimization.

Q
Design Elasticsearch mapping and query for 'pizza restaurants within 5km, rating ≥4'.
A
Index mapping: PUT /restaurants { 'mappings': { 'properties': { 'name': { 'type': 'text', 'analyzer': 'standard' }, 'category': { 'type': 'keyword' }, 'location': { 'type': 'geo_point' }, 'rating': { 'type': 'float' }, 'price_range': { 'type': 'keyword' }, 'is_open': { 'type': 'boolean' } } } }. Index document: POST /restaurants/_doc { 'name': 'Taco Bell', 'category': 'Fast Food', 'location': { 'lat': 12.9716, 'lon': 77.5946 }, 'rating': 4.2, 'price_range': '$', 'is_open': true }. Search query: POST /restaurants/_search { 'query': { 'bool': { 'must': [ { 'match': { 'name': 'pizza' } } ], 'filter': [ { 'geo_distance': { 'distance': '5km', 'location': { 'lat': 12.97, 'lon': 77.59 } } }, { 'range': { 'rating': { 'gte': 4.0 } } }, { 'term': { 'is_open': true } } ] } }, 'sort': [ { '_geo_distance': { 'location': { 'lat': 12.97, 'lon': 77.59 }, 'order': 'asc', 'unit': 'km' } } ], 'size': 20 }. Result: { 'hits': { 'hits': [ { '_source': { 'name': 'Pizza Hut', 'rating': 4.5 }, 'sort': [ 0.8 ] } ] } } (0.8 km distance). Aggregations for facets: 'aggs': { 'price_facets': { 'terms': { 'field': 'price_range' } }, 'distance_buckets': { 'geo_distance': { 'field': 'location', 'origin': { 'lat': 12.97, 'lon': 77.59 }, 'ranges': [ {'to': 1}, {'from': 1, 'to': 3}, {'from': 3, 'to': 5} ] } } }. Performance: ~20-50ms for 100M documents, scales horizontally.

Q
How do you shard geospatial data for horizontal scaling?
A
Sharding strategies:

(1) Geographic sharding: Divide by region (US-West, US-East, EU-West, EU-East, Asia-Pacific), each region = separate database/cluster, route queries based on location bounds, Pros: Simple routing, isolated failures, Cons: Unbalanced load (NYC has more restaurants than Montana), cross-region queries complex.

(2) Geohash prefix sharding: Shard by first N characters of geohash (e.g., first 2 chars = 1024 possible prefixes → 16 shards), use consistent hashing to map geohash prefix to shard, Pros: Even distribution, Cons: Radius queries may span multiple shards.

(3) Hybrid: Regions + geohash - shard by region first (US-East), then by geohash prefix within region, Example: US-East shard 1: geohashes starting with '9q', '9r', US-East shard 2: '9w', '9x'. Query routing:

(1) Extract location from query,

(2) Determine geohash or region,

(3) Route to appropriate shard

(s),

(4) If query spans multiple shards (large radius near boundary), fan out to all relevant shards, merge results. Example: User at NYC (40.7128, -74.0060) searches 10km → all results in US-East shard, User at Philadelphia (border of US-East/US-Mid) searches 50km → query both shards, merge by distance. Cross-shard complexity:

(1) Small radius (<10km): Usually hits 1-2 shards,

(2) Large radius (>50km): May hit 3-5 shards, scatter-gather pattern. Performance: Per-shard dataset reduced 10x (10M → 1M), query latency improved 5x (500ms → 100ms). Elasticsearch: Auto-shards by document ID, manual routing by geohash possible using custom routing key.

Q
What's your caching strategy for proximity searches?
A
Multi-layer caching:

(1) Result cache: Cache entire query results in Redis, key = hash(lat, lng, radius, filters), value = [location_ids], TTL=5 min, handles identical repeated queries, Example: search: {lat: 37.77, lng: -122.42, radius: 5km, category: Italian} → cache key: hash(37.77:-122.42:5000:Italian) → value: [id1, id2, id3, ...],

(2) Location cache: Cache popular/active locations in Redis GEOSPATIAL, GEOADD restaurants:hot:{city_id}, TTL=10 min, serves 80% queries via GEORADIUS in <5ms, Eviction: LRU (Least Recently Used), keep top 1000 per city.

(3) Application cache: In-memory cache (Caffeine, Guava) in API servers for very frequent queries, 100-element LRU cache, serves in <1ms without network hop.

(4) CDN cache: For static location data (restaurant metadata, images), cache at edge locations globally. Cache warming:

(1) Background job analyzes query logs,

(2) Identifies top 100 queries per city by frequency,

(3) Pre-populates Redis cache before peak hours. Invalidation:

(1) On location update: Invalidate all cache keys containing that location, Use Redis Pub/Sub or Kafka to broadcast invalidation event,

(2) Pattern matching: Use Redis SCAN to find keys matching location_id, DEL all matching keys,

(3) Time-based: Regardless of updates, expire cache entries after TTL to prevent indefinite staleness. Example cache hit flow: User searches → check Redis result cache → hit (identical query 2 min ago) → return cached results → <5ms latency. Cache miss flow: → query Elasticsearch → 50ms → cache result → return to user.

Q
How do you handle polygon-based searches (e.g., restaurants in a neighborhood)?
A
Polygon search implementation:

(1) PostGIS: SELECT * FROM restaurants WHERE ST_Contains(ST_GeomFromGeoJSON('{polygon}'), location), polygon format: GeoJSON {'type': 'Polygon', 'coordinates': [[[lng1, lat1], [lng2, lat2], [lng3, lat3], [lng1, lat1]]]}, must close loop (first point = last point), GIST index supports containment queries O(log n).

(2) Elasticsearch: { 'query': { 'geo_polygon': { 'location': { 'points': [ {'lat': 12.97, 'lon': 77.59}, {'lat': 12.98, 'lon': 77.60}, {'lat': 12.97, 'lon': 77.61} ] } } } }, supports up to 1000 vertices, automatically closes polygon. Optimization:

(1) Bounding box pre-filter: Calculate min/max lat/lng of polygon (bounding rectangle), pre-filter with WHERE lat BETWEEN min_lat AND max_lat AND lng BETWEEN min_lng AND max_lng (fast), then exact containment check ST_Contains (slower), reduces candidates by 90%,

(2) Polygon simplification: For complex polygons (1000+ vertices), use Douglas-Peucker algorithm to reduce to 100-200 vertices while maintaining shape, 5-10x faster queries.

(3) Pre-computation: For static zones (delivery areas, neighborhoods), assign zone_id to each location, query becomes WHERE zone_id = {id} (instant via index). Use cases:

(1) Delivery zones: Restaurant serves specific polygonal area,

(2) Geofencing: Driver dispatch only within polygon boundary,

(3) Neighborhood search: Find restaurants in 'Greenwich Village' (irregular shape). Performance: Simple polygon (10 vertices) with 10M points → ~50ms with GIST index, Complex polygon (100 vertices) → ~200ms. Example: Uber Eats delivery zone → restaurant draws polygon on map → frontend converts to GeoJSON → backend stores in zones table → orders only accepted from customers within ST_Contains(delivery_zone, customer_location).

12. Geohash Precision Reference

Precision Table (from image)
Length 1 — ±2500 km (5009.4 km width × 4992.6 km height) - Country level
Length 2 — ±630 km (1252.3 km × 624.1 km) - Large region
Length 3 — ±78 km (156.5 km × 156 km) - City level
Length 4 — ±20 km (39.1 km × 19.5 km) - District
Length 5 — ±2.4 km (4.9 km × 4.9 km) - Neighborhood
Length 6 — ±0.61 km (1.2 km × 609.4 m) - Street
Length 7 — ±76 m (152.9 m × 152.4 m) - Building
Length 8 — ±19 m (38.2 m × 19 m) - Precise
Length 9 — ±2.4 m (4.8 m × 4.8 m) - Sub-building
Precision Selection Guide
500m radius — Use length 6 (±610m cell size) - ensures all points in radius are in queried cells
2km radius — Use length 5 (±2.4km cell) - single cell query possible
5km radius — Use length 4 (±20km cell) - larger cell, more candidates but fewer DB queries
100m radius — Use length 7 (±76m cell) - precise, need 9 cell query (center + 8 neighbors)
13. Key Numbers to Remember

Performance Benchmarks
Redis GEORADIUS — ~1ms for 10K points, ~5ms for 100K, ~10ms for 1M points
PostgreSQL PostGIS — ~50-100ms for 10M points with GIST index
Elasticsearch — ~10-50ms for 100M documents with geo queries
Geohash LIKE — ~10-50ms with B-tree index on geohash column
QuadTree in-memory — <1ms for balanced tree with 1M points
Haversine calculation — ~0.001ms per calculation (1M in 1 second)
Distance Formulas
Earth Radius — 6371 km (3959 miles) for Haversine formula
1 degree latitude — ≈111 km (constant everywhere on Earth)
1 degree longitude — ≈111 km × cos(latitude) - varies by latitude, 0 at poles
Haversine accuracy — ±0.5% error (assumes perfect sphere)
Vincenty accuracy — ±0.5mm error (accounts for ellipsoid), 10x slower
Memory & Storage
Redis memory — ~50 bytes per location → 1M points ≈ 50MB
PostGIS GIST index — ~10-20% of table size for spatial index
Elasticsearch geo_point — ~16 bytes per location (stored + indexed)
QuadTree overhead — ~100-200 bytes per node (internal nodes + pointers)
Scaling Limits
Redis capacity — ~10M points per instance (memory constraint)
PostgreSQL — 10M-100M points per database with proper indexing
Elasticsearch — Billions of points across cluster (horizontal scaling)
QuadTree — Efficient for <1M points in-memory, single server
Key Interview Tips

⚠️
NEVER use simple lat/lng BETWEEN without spatial indexing for large datasets. Scanning millions of rows is O(n). Use GIST index (PostGIS), B-tree on geohash, or Redis GEORADIUS for O(log n).

⭐
Interviewers ALWAYS ask: 'Geohash vs QuadTree vs PostGIS?'. Answer: Geohash for distributed systems (standard indexes), QuadTree for in-memory single-server, PostGIS for ACID + complex queries. Production uses hybrid: Redis (hot) + Elasticsearch (search) + PostGIS (source of truth).

💡
Key optimization: Bounding box pre-filter before Haversine. WHERE lat BETWEEN (user_lat - delta) AND (user_lat + delta) eliminates 90% of points, then Haversine only for remaining 10%. Delta ≈ radius_km / 111.

⭐
Must mention: Geohash edge case. Points on cell boundary have different prefixes despite being close. Solution: query 8 neighboring cells (9 total). Precision based on radius: 500m → length 6, 5km → length 4.

⚠️
NEVER assume 1 degree latitude = 1 degree longitude in distance. Latitude is constant (111km), longitude varies by latitude (111km at equator, 0km at poles). Always use Haversine or PostGIS ST_Distance.

💡
Hybrid caching: Redis GEORADIUS for hot data (~5ms), Elasticsearch for complex queries (~50ms), PostgreSQL PostGIS for source of truth (~100ms). Serves 80% from Redis, 95% from Elasticsearch, 5% from PostgreSQL.

⭐
Interviewers love: 'Why Elasticsearch over PostgreSQL?'. Answer: Elasticsearch: horizontally scalable (billions of points), fast filtering (category + rating + distance), ~50ms p95. PostgreSQL: single server bottleneck, ~100ms, ACID guarantees. Use both: ES for reads, PG for writes.

⚠️
NEVER compute Haversine for every point. Pre-filter with bounding box or geohash (index-based), then Haversine only for candidates. Haversine cheap per calc but expensive at scale (1M calculations = 1 second CPU).

💡
Geographic sharding: Shard by region (US-West, US-East, EU, Asia). 60% queries hit single shard, 30% hit 2 shards (border), reduces per-shard dataset 5x, latency 50ms vs 200ms. Use overlapping zones (10km buffer).

⭐
Must explain: SQL query with geohash. SELECT * FROM restaurants WHERE geohash LIKE 'sgkzt%' OR geohash LIKE 'sgkzu%' ... (9 cells) → 500 candidates → Haversine filter → 200 within exact 5km. Show understanding of neighbor calculation.