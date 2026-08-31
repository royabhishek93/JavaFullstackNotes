# How do you find restaurants within 5 km of a customer without writing distance math yourself?

**Type:** Advanced Scenario-Based
**Topic:** Redis Architecture — Geospatial Indexes
**Level:** Senior Interview (8–12+ YOE)

## Direct Answer
Use Redis's **Geospatial** commands. Store each restaurant's coordinates with `GEOADD`, then ask Redis directly for everything within a radius using `GEOSEARCH` (or the older `GEORADIUS`) — Redis computes the distance calculations internally, so you never have to implement haversine/great-circle math in your application.

## Easy Explanation
Instead of pulling every restaurant's coordinates into your application and manually calculating "how far is this one from the customer" for each of them, you hand Redis the customer's coordinates and a radius, and it hands back exactly the restaurants that qualify — sorted by distance if you want. It's like asking a smart map "show me only the pins inside this circle," instead of measuring the distance to every single pin yourself.

## Diagram
```
GEOADD restaurants  77.5946 12.9716  "restaurant:pizza-place"
GEOADD restaurants  77.6100 12.9800  "restaurant:sushi-bar"
GEOADD restaurants  77.9000 13.2000  "restaurant:far-away-diner"

Customer's current coordinates: 77.5950, 12.9720

GEOSEARCH restaurants FROMLONLAT 77.5950 12.9720 BYRADIUS 5 km ASC WITHCOORD WITHDIST

Result:
  "restaurant:pizza-place"   -> 0.05 km away
  "restaurant:sushi-bar"     -> 1.2 km away
  ("restaurant:far-away-diner" excluded — it's ~40km away, outside the 5km radius)
```

## Production Example
```bash
GEOADD nearby-stores 77.5946 12.9716 "store:101"
GEOSEARCH nearby-stores FROMLONLAT 77.5950 12.9720 BYRADIUS 5 km ASC COUNT 10 WITHDIST
```

A food-delivery app uses exactly this pattern to power "restaurants near you" — storing every restaurant's location once via `GEOADD`, then issuing a single `GEOSEARCH` per customer request instead of looping through the entire restaurant table computing distances in application code.

## Why Interviewers Ask This
It checks whether a candidate knows Redis has first-class support for location-based queries, avoiding a very common anti-pattern: pulling a whole table into memory and hand-rolling distance math, which doesn't scale and duplicates logic Redis already provides.
