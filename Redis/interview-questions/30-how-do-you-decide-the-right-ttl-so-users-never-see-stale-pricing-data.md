# How do you decide the right TTL so users never see stale pricing data?

**Type:** Advanced Scenario-Based
**Topic:** Redis Caching Patterns — Cache Invalidation & TTL Strategy
**Level:** Staff Interview (10–15+ YOE)

## Direct Answer
Base the TTL on how *quickly the underlying data actually changes* and how costly a stale read would be to the business — not on a guess. For rarely-changing catalog data, minutes-to-hours is fine; for pricing that can change due to promotions or currency shifts, use a short TTL *combined with* active invalidation (explicitly deleting/updating the cache key the moment a price changes), so you're not solely relying on time-based expiry to catch every update.

## Easy Explanation
A TTL is like saying "trust this sticky note for 5 minutes, then throw it away and ask again." That's fine for something that rarely changes, like a product's description. But for something that can change suddenly — like a flash-sale price — a 5-minute-old note could actively mislead a customer. The safer approach is: whenever the *real* price changes, immediately update or delete the sticky note yourself, instead of waiting for it to expire on its own.

## Diagram
```
Passive invalidation only (TTL alone):
  SET price:sku-42 "499" EX 300
  ... price changes to "399" in the database at t=60s ...
  ... cache still serves "499" until t=300s ...   <- up to 4 minutes of WRONG price shown

Active invalidation (TTL + explicit update on change):
  SET price:sku-42 "499" EX 300
  price changes in the database
        |
        v
  admin/service ALSO runs: SET price:sku-42 "399" EX 300   (or DEL price:sku-42)
        |
        v
  next request immediately sees the correct "399"   <- no stale window at all
```

## Production Example
```javascript
// Whenever a price changes anywhere in the system, this is called
async function updatePrice(skuId, newPrice) {
  await db.updatePrice(skuId, newPrice);
  await redisClient.set(`price:${skuId}`, newPrice, { EX: 300 }); // refresh cache immediately
}
```

An e-commerce platform sets a 5-minute TTL as a safety net (in case an invalidation call is ever missed), but actively pushes updated prices into Redis the instant they change in the pricing service — so customers never see stale prices unless both the invalidation call *and* the TTL somehow both failed.

## Why Interviewers Ask This
It distinguishes engineers who treat TTL as the *only* invalidation strategy from those who understand TTL should be a safety net, while active invalidation on write is the primary mechanism for data that has real business impact if stale.
