# Q63: Cross-Region Latency - Minimize data transfer

**Difficulty:** ⭐⭐⭐⭐ (Staff)

```
LATENCY BREAKDOWN
═══════════════════════════════════════════════════════════
Same-AZ: 1-2ms
Same-Region (different AZ): 5-10ms
Cross-Region (US-East → US-West): 50-70ms
Cross-Region (US → Europe): 80-120ms
Cross-Region (US → Asia): 150-250ms


OPTIMIZATION STRATEGIES
═══════════════════════════════════════════════════════════

1. Regional CDN (CloudFront)
   - Static assets: 10-50ms → <10ms ✅
   - Cache hit ratio: 95%

2. Regional Caching (Redis)
   - Movie catalog: No cross-region calls
   - Show listings: Cached locally

3. Async Replication
   - User profiles: Eventually consistent
   - Booking data: Immediate (within region)

4. Data Locality
   - Bookings stay in home region
   - No cross-region reads for booking flow
```

---
