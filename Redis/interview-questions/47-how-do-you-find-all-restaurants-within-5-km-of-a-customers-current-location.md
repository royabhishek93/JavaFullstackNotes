# How do you find all restaurants within 5 km of a customer's current location?

**Type:** Scenario-Based
**Topic:** Redis Caching Patterns — Geospatial Queries
**Level:** Mid–Senior Interview (5–10+ YOE)

## Direct Answer
Store every restaurant's coordinates in Redis using `GEOADD`, then issue a single `GEOSEARCH` (or `GEORADIUS`) query from the customer's current coordinates with a 5 km radius. Redis handles the distance calculation internally and returns only the matching restaurants, optionally sorted by distance.

## Easy Explanation
Instead of pulling every restaurant's address into your backend and manually calculating "is this one within 5 km," you just ask Redis directly: "given this exact point, show me everything inside a 5 km circle." Redis already knows how to do that geometry for you — you just supply the center point and the radius.

## Diagram
```
GEOADD restaurants 77.5946 12.9716 "restaurant:101"
GEOADD restaurants 77.6100 12.9800 "restaurant:102"
GEOADD restaurants 78.9000 13.5000 "restaurant:999"   (far away)

Customer at: 77.5950, 12.9720

GEOSEARCH restaurants FROMLONLAT 77.5950 12.9720 BYRADIUS 5 km ASC WITHDIST

Result:
  restaurant:101 -> 0.05 km
  restaurant:102 -> 1.3 km
  (restaurant:999 excluded — well outside the 5km circle)
```

## Production Example
```javascript
await redisClient.geoAdd("restaurants", { longitude: 77.5946, latitude: 12.9716, member: "restaurant:101" });

const nearby = await redisClient.geoSearch("restaurants", {
  FROM: { longitude: 77.5950, latitude: 12.9720 },
  BY: { radius: 5, unit: "km" },
  SORT: "ASC",
});
```

This pattern powers "restaurants near you" style features in food-delivery apps, avoiding a common anti-pattern of loading every restaurant row from the database and calculating distance for each one in application code, which becomes slow as the restaurant table grows.

## Why Interviewers Ask This
It confirms the candidate knows Redis has a first-class, purpose-built feature for location queries rather than defaulting to reimplementing distance math or relying purely on a relational database's (often much slower) geo functions.
