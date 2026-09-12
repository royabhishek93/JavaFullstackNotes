# Presence System — Online/Last Seen — LinkedIn Post

## Post Text (copy-paste ready)

500 million concurrent WhatsApp users. 16.7 million "I'm still here" heartbeats hitting the server every second. One Redis TTL value decides whether that whole system works or lies to you.

- The entire "online" indicator is one Redis key with a TTL: SETEX user:alice:online 60 "1" — heartbeat every 30s refreshes it, silence for 60s (2x the interval) and it expires = offline
- A single Redis node caps out around 1M ops/sec — 500M users × 1 heartbeat/30s forces you into a hash-sharded Redis Cluster (20+ shards) just to survive the write volume
- Privacy has a reciprocity trap: if you only check the viewer's settings, you've built one-sided surveillance — WhatsApp checks BOTH users' "Last Seen" visibility before revealing either one
- Naive group presence is a fan-out landmine: showing individual online dots for a 500-member group means 500 EXISTS calls per screen open — 1,000 people opening it = 500,000 Redis queries, just to render one screen
- TTL expiry alone gives you a 60-second-late "soft" disconnect — real systems also listen for the WebSocket's onDisconnect event as a faster "hard" disconnect path

Swipe to see: the heartbeat flow, the fan-out trap at scale, and the exact interview answer for "design presence for 500M users."

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
500M users, 16.7M heartbeats/sec — how WhatsApp's "online" dot actually works, and the group-chat trap that breaks it 👇

### Variant B — Long (400–600 chars)
WhatsApp's "online" status isn't magic — it's one Redis key with a 60-second TTL, refreshed by a heartbeat every 30 seconds. Silence for 60 seconds means the key expires and you're marked offline. At 500M concurrent users that's 16.7M writes/sec, which forces a hash-sharded Redis Cluster. The two traps that catch engineers: privacy reciprocity (you must check both users' Last Seen settings, not just the viewer's) and group-chat fan-out (500 individual EXISTS calls per group open doesn't scale — show an aggregate "N online" count instead).

---

## Best Time to Post
Wednesday, 10:00–11:00 AM IST (chat/messaging system design content peaks mid-week when engineers are prepping for weekend interview practice)

## Engagement Hook
"Have you ever built a 'who's online' feature that looked fine with 10 test users and fell over the moment it hit a real group chat? What broke first?"
