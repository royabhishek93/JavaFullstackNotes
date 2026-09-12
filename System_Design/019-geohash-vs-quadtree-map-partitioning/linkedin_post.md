# Geohash vs QuadTree — Map Partitioning — LinkedIn Post

## Post Text (copy-paste ready)

50M restaurants, 5km radius search: 30+ seconds with a plain lat/lng query — or 5ms with the right index.

- A B-tree index is 1D — it sorts numbers on a line, it can't answer "what's near this point" in 2D space
- Geohash collapses lat/lng into a short string where nearby places share a common prefix (e.g. "dr5re" and "dr5rf" are neighboring cells)
- The 9-neighbor rule: always query the center cell + all 8 surrounding cells — a restaurant 10m away can land in a neighboring cell, not yours
- QuadTree adapts to density instead of using a fixed grid: a Sahara Desert cell can be 500km wide (empty), while a Manhattan cell is 100m wide (packed, split 12+ levels deep)
- Uber's driver-location problem: 1M active drivers updating every 3 seconds = 333,333 writes/sec — Redis GEOADD/GEORADIUS (geohash under the hood) handles this; PostgreSQL alone can't

Swipe → to see: the 9-neighbor grid diagram, the QuadTree adaptive split, and the decision framework for Geohash vs QuadTree vs PostGIS R-Tree.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
B-tree indexes can't do "nearby" — they're 1D. Geohash + the 9-neighbor rule (and Uber's 333K writes/sec) explain why. Save for your next interview.

### Variant B — Long (400–600 chars)
"Find restaurants near me" sounds simple until you realize a B-tree index only understands one dimension — it can't answer 2D proximity queries. Geohash fixes this by turning lat/lng into a string where nearby places share a prefix, but you must always query the center cell plus all 8 neighbors, never just one. QuadTree takes a different approach — adaptive cells, so a Manhattan block splits 12+ levels deep while the Sahara stays one giant cell. Uber uses this at scale: 1M drivers updating every 3 seconds is 333,333 writes/sec, handled by Redis GEOADD/GEORADIUS — geohash under the hood. Full breakdown, diagrams, and decision framework in the carousel.

---

## Best Time to Post
Tuesday–Thursday, 8:00–10:00 AM (local time zone of your primary audience) — peak LinkedIn engagement window for technical/career content before the workday starts.

## Engagement Hook
Ask in the comments: "Have you ever queried just the center geohash cell and missed nearby results? What broke?" — invites war-story replies and boosts comment-driven reach.
