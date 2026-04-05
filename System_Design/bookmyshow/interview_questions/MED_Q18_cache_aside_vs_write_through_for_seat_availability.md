# Q18: Cache-Aside vs Write-Through for seat availability

### Comparison:
```
CACHE-ASIDE (Lazy Loading) ✅ Recommended
═══════════════════════════════════════════════════════════
Read:
1. Check cache
2. If miss, read from DB
3. Write to cache
4. Return data

Write:
1. Update DB
2. Invalidate cache
3. Next read will refresh

Pros: ✓ Only cache what's needed
Cons: ✗ Cache miss latency

WRITE-THROUGH
═══════════════════════════════════════════════════════════
Read:
1. Check cache
2. If miss, read from DB + cache
3. Return data

Write:
1. Update cache
2. Update DB
3. Return success

Pros: ✓ Cache always fresh
Cons: ✗ Write latency higher
```

**For BookMyShow: Use Cache-Aside**
- Seats change frequently (bookings)
- Cache invalidation simpler
- Read-heavy workload
- Acceptable cache miss latency

---
