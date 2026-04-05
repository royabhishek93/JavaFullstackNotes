# Q19: Redis vs Memcached for BookMyShow

```
┌─────────────────────┬──────────────┬──────────────┐
│     Feature         │    Redis     │  Memcached   │
├─────────────────────┼──────────────┼──────────────┤
│ Data structures     │ 5+ types     │ Key-value    │
│ Pub/Sub             │ Yes ✅       │ No ❌        │
│ Persistence         │ Yes ✅       │ No ❌        │
│ Replication         │ Yes ✅       │ No ❌        │
│ Atomic operations   │ Yes ✅       │ Limited      │
│ Lua scripting       │ Yes ✅       │ No ❌        │
│ Memory efficiency   │ Lower        │ Higher ✅    │
└─────────────────────┴──────────────┴──────────────┘

Choose Redis for BookMyShow:
✅ Pub/Sub needed (real-time updates)
✅ Sorted sets (leaderboards, autocomplete)
✅ Atomic operations (counters, locks)
✅ TTL per key (seat expiry)
```

---
