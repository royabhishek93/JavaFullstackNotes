# Presence System
### How WhatsApp Shows "Online" / "Last Seen" — Heartbeat + Redis TTL

---

## PART 1 — THE STUDENT CONVERSATION

**Have you ever wondered how WhatsApp knows you're online, even though you never clicked "go online"?**

WhatsApp's app is designed to silently tell the server "I'm still here" every few seconds while it's open. The server records this with a timestamp. When you ask "is Alice online?", the server checks: "did Alice check in within the last 30 seconds?" If yes → Online. If no → show last seen timestamp.

This sounds simple, but at WhatsApp's scale — 2 billion users — managing presence status is a genuinely hard engineering problem. You have 500 million concurrent online users. Each sends a heartbeat every 30 seconds. That's 16 million heartbeat writes per second. Your presence store must handle this without breaking.

**The core mechanism: heartbeat + Redis TTL (time-to-live).**

---

## PART 2 — THE IMPLEMENTATION

### Heartbeat Flow

```
User opens WhatsApp:
────────────────────────────────────────────────────────────────────

  Mobile App                     WebSocket Server        Redis
  ──────────                     ────────────────        ─────

  App opens → connects to WS server

  Every 30 seconds while app is open:
  HEARTBEAT ─────────────────────►
                                   SET user:alice:online 1 EX 60
                                                           ↑  ↑
                                                           │  TTL = 60 seconds
                                                           └── key expires after 60s of no update

  App goes to background (iOS/Android kills network):
  No more heartbeats sent.

  t=0s:  Last heartbeat written. Key TTL = 60s.
  t=30s: Key TTL = 30s remaining. No heartbeat received.
  t=60s: Key EXPIRES automatically. Deleted from Redis.

  Alice is now "offline."
  Redis stores: nothing (key expired = offline)
  Also stored: user:alice:last_seen = "2026-08-31T14:30:22Z"
  (written every time a heartbeat updates the TTL)
```

### Reading Presence Status

```
Bob wants to see Alice's status:
────────────────────────────────────────────────────────────────────

  Bob's App → GET /presence/alice

  Presence Service:
  1. EXISTS user:alice:online  → returns 1 (exists) OR 0 (expired/absent)
     If 1: return "Online"
     If 0: GET user:alice:last_seen → return "Last seen 14 minutes ago"

  Redis commands:
    SETEX user:alice:online 60 "1"      ← write presence (heartbeat)
    EXISTS user:alice:online             ← check online status
    GET user:alice:last_seen             ← get timestamp

  Time complexity: O(1) per user. Even at 500M users.
```

---

## PART 3 — THE SCALE PROBLEM

```
WhatsApp scale math:
────────────────────────────────────────────────────────────────────

  500 million concurrent online users
  × 1 heartbeat per 30 seconds
  = 16.7 million heartbeat writes per second to Redis

  Redis single node: ~1M ops/sec max
  → 1 Redis node is not enough.

  Solution: Redis Cluster (hash-slot sharding)

  user:alice:online  → hash("alice") % 16384 = slot 1234 → Shard 3
  user:bob:online    → hash("bob")   % 16384 = slot 8765 → Shard 7
  user:carol:online  → hash("carol") % 16384 = slot 456  → Shard 1

  16 Redis shards × 1M ops/sec = 16M ops/sec ✓ (covers 16.7M with some margin)
  Add more shards for headroom.

  Memory:
  1 presence key = ~50 bytes (key + value + metadata)
  500M users × 50 bytes = 25 GB
  Spread across 16 shards = ~1.6 GB per shard ← very manageable
```

---

## PART 4 — PRIVACY CONTROLS ("LAST SEEN" SETTINGS)

```
WhatsApp privacy setting: "Who can see my Last Seen"
  Options: Everyone / My Contacts / Nobody

Implementation:
────────────────────────────────────────────────────────────────────

  UserPreference table (MySQL):
  { user_id: alice, last_seen_visibility: "contacts" }

  When Bob queries Alice's presence:
  1. Check Alice's visibility setting.
  2. Check if Bob is in Alice's contacts.
  3. If Bob is a contact AND Alice's setting is "contacts" → return last seen.
  4. If Alice's setting is "nobody" → return null (hide last seen entirely).
  5. If Bob is not Alice's contact AND setting is "contacts" → return null.

  WhatsApp reciprocity rule:
  If Alice hides her last seen from Bob,
  Alice also CANNOT see Bob's last seen.
  (prevents one-sided surveillance)

  Implementation: check BOTH users' settings before revealing either's last seen.
```

---

## PART 5 — "ONLINE" INDICATOR IN GROUP CHATS

```
Challenge: in a group of 500, who is currently online?
────────────────────────────────────────────────────────────────────

  Naïve approach: query presence for all 500 members when group opens.
  Cost: 500 EXISTS commands to Redis per user opening the group.
  If 1000 users open the group simultaneously: 500,000 Redis queries.
  In a large group of 1000 members: 1,000,000 Redis queries per open.

  Real WhatsApp approach:
  Only show "N members online" count, not individual online indicators.
  Less granular, but avoids the fan-out problem.

  For one-on-one chats:
  Show "Online" if peer's presence key exists in Redis.
  Show "Last seen X" if presence key expired.
  1 EXISTS query per message screen open. Manageable.

  Presence push (instead of pull):
  When Alice's status changes (online → offline or vice versa):
  Notification Service pushes presence update to all of Alice's active chats.
  Bob's app receives "Alice is now offline" without polling.
  Uses the existing WebSocket connection that Bob has open.
```

---

## PART 6 — THE INTERVIEW CONVERSATION

**Interviewer:** "Design the presence system for a chat app with 500M users."

**You (architect answer):**

> "The presence system has three components: heartbeat writing, presence reading, and last-seen storage.
>
> For heartbeats: every client sends a heartbeat to the WebSocket server every 30 seconds while active.
> The WS server writes to Redis: SETEX user:{id}:online 60 '1'. TTL is 60 seconds — twice the heartbeat
> interval, so one missed heartbeat doesn't incorrectly mark the user offline. If the client disconnects
> or the app goes to background, no more heartbeats arrive, and the key expires naturally after 60 seconds.
> At the same time, we write user:{id}:last_seen to a separate key with the current timestamp.
>
> For the scale: 500M concurrent users × 1 heartbeat/30 seconds = ~17M writes/second. A single Redis
> node handles ~1M ops/sec. I'd use Redis Cluster with 20+ shards, distributing users by hash slot.
> Each shard handles ~850K writes/sec with headroom.
>
> For presence reads: when Bob opens a chat with Alice, we do EXISTS user:alice:online. O(1) per query.
> For a group chat read receipts page, we'd batch EXISTS queries or use Redis MGET.
>
> Privacy: we gate on user preference. Alice can set her last seen to 'contacts only' or 'nobody.'
> This check is a MySQL lookup on UserPreference, cached in Redis for 5 minutes. If Alice hides
> her last seen, she forfeits seeing others' last seen too."

---

## QUICK REFERENCE CARD

```
Presence data model in Redis:
  Key: user:{id}:online      Value: "1"    TTL: 60s (refreshed every 30s by heartbeat)
  Key: user:{id}:last_seen   Value: timestamp  TTL: none (permanent, updated on heartbeat)

Heartbeat:
  Client sends every 30s while active (WebSocket ping or HTTP POST)
  Server: SETEX user:{id}:online 60 "1"
  Server: SET user:{id}:last_seen <timestamp>

Online check:
  EXISTS user:{id}:online → 1 = online, 0 = offline

Last seen:
  GET user:{id}:last_seen → timestamp string, format relative for display

Scale:
  500M users × (1/30) heartbeats/sec = 16.7M writes/sec
  Redis Cluster with 20 shards → ~800K writes/sec per shard ← manageable

Privacy:
  UserPreference.last_seen_visibility: EVERYONE | CONTACTS | NOBODY
  Check both users' settings before revealing either's last seen (reciprocity)

Disconnect detection:
  TTL expiry = soft disconnect (missed heartbeats)
  WS onDisconnect event = hard disconnect (more immediate, ~30s faster)
  Both should update last_seen and remove online key

Interview one-liner:
"Heartbeat + Redis TTL. Client sends SETEX with 60s TTL every 30 seconds.
If the app closes, no more heartbeats, key expires after 60s → offline.
At 500M scale: Redis Cluster distributes the 17M heartbeat writes/sec
across shards. Presence check is one EXISTS call per query."
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Presence is a subtle but common follow-up question in chat system interviews — knowing the heartbeat + TTL pattern immediately shows depth.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **04 — Chat (WhatsApp)** | This IS the WhatsApp "Online"/"Last seen" feature. Heartbeat every 30s → Redis SETEX user:{id}:online 60 "1". Key expires after 60s of no heartbeat = offline. At 500M users: Redis Cluster handles 17M heartbeat writes/sec. Privacy: UserPreference.last_seen_visibility controls who sees your last seen. |

**Architect's one-liner for the interview:**
*"Presence is just a Redis key with a 60-second TTL — the client keeps it alive with heartbeats, and silence means offline."*
