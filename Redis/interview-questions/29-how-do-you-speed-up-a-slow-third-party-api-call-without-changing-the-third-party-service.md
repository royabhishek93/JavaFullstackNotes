# How do you speed up a slow third-party API call without changing the third-party service?

**Type:** Scenario-Based
**Topic:** Redis Caching Patterns — Cache-Aside
**Level:** Mid–Senior Interview (5–10+ YOE)

## Direct Answer
Use the **cache-aside pattern**: before calling the slow API, check Redis for a cached response; if it's there, return it instantly; if not, call the slow API, store the result in Redis with an expiry, and return it. Every subsequent request within the expiry window is served from Redis in milliseconds instead of waiting seconds on the third-party call.

## Easy Explanation
Think of asking a friend a question that takes them 3 seconds to answer every time you ask, even if you ask the exact same question repeatedly. Instead, you write their answer on a sticky note the first time, and check the sticky note before bothering them again. If the note is still there (and not too old), you use it instantly; otherwise, you ask your friend again and update the note.

## Diagram
```
Request comes in for /products/42
        |
        v
   Check Redis: GET product:42
        |
   -----+----- 
  cached?     not cached?
    |              |
    v              v
 return       call slow third-party API (e.g. 1.5s)
 instantly          |
 (~5ms)             v
                SET product:42 <result> EX 300
                    |
                    v
                return result to caller

Next request for /products/42 within 5 minutes -> served from Redis, ~5ms instead of ~1.5s
```

## Production Example
```javascript
async function getProduct(id) {
  const cached = await redisClient.get(`product:${id}`);
  if (cached) return JSON.parse(cached);

  const response = await axios.get(`https://slow-partner-api.com/products/${id}`);
  await redisClient.set(`product:${id}`, JSON.stringify(response.data), { EX: 300 });
  return response.data;
}
```

In a real measurement, a request that took 1.7–4.7 seconds on a cold cache dropped to 6–15 milliseconds once the response was cached — a 100x+ speedup for every repeat request within the TTL window.

## Why Interviewers Ask This
It's the single most common practical Redis use case, and it checks whether the candidate can implement the full pattern correctly — check, fetch-on-miss, store-with-expiry — rather than just saying "cache it" without the mechanics.
