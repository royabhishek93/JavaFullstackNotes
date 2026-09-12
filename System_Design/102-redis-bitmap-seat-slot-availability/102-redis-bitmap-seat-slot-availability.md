# Redis Bitmaps: Compact Boolean State for Seat/Slot Availability
### How to represent 10,000 seats as 1,250 bytes instead of a database table

---

## PART 1 — THE STUDENT CONVERSATION

Imagine a stadium with 10,000 seats. For every seat you need exactly one fact: booked or not booked. That's it — one bit of information per seat. Yet the instinct of most developers is to model this as 10,000 rows in a database table, or 10,000 keys in Redis (`seat:1`, `seat:2`, ... `seat:10000`), or a hash with 10,000 fields. Each of those approaches carries per-entry overhead — a row header, a key name string, pointer metadata — that dwarfs the actual 1 bit of information you're storing.

A Redis Bitmap solves this by exploiting a simple fact: a Redis String is just a sequence of bytes, and Redis lets you address and flip **individual bits** within that byte sequence directly, without you ever managing byte/bit math yourself. `SETBIT seats:section-A 4821 1` doesn't create a new key or a new field — it takes the *existing* string value stored at `seats:section-A`, and flips bit number 4821 to `1`. If the string isn't long enough yet, Redis silently grows it (zero-padded) to fit.

Think of it like a single very long string of light switches on a wall, one per seat, laid out in a row. "Is seat 4821 booked?" is just "is switch 4821 on?" — `GETBIT seats:section-A 4821`. You don't need a separate labeled switch-box (a database row) for each switch; they're all just positions along one wire.

Why does this matter? Because 10,000 bits is exactly 10,000/8 = 1,250 bytes — about the size of a single paragraph of text — to represent the *entire* seat map for a section. Compare that to 10,000 separate Redis keys, each of which costs Redis roughly 50-90 bytes of internal overhead (the key name, a `robj` header, dict entry pointers) even before you count the 1 bit of actual data — that's 500KB-900KB just in overhead, for the same information a bitmap stores in 1.25KB. It's not just "a bit more efficient" — it's often a 400-700x reduction.

The other superpower: Redis has native SIMD-optimized bitwise operations (`BITCOUNT`, `BITPOS`, `BITOP`) that operate on the *entire* bitmap in a single command, letting you answer aggregate questions ("how many seats are booked?", "what's the first free seat?", "which seats are both available AND wheelchair-accessible?") without looping over 10,000 individual reads in application code.

---

## PART 2 — THE BITMAP ARCHITECTURE DIAGRAMS

### Seat Map as a Bitmap: Booking and Querying

```
Theater Section A: 16 seats (simplified for diagram; real section = 2,500 seats)

Seat index:     0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15
Bit value:      0  0  1  0  1  1  0  0  0  1  0  0  0  0  1  0
                        ^     ^  ^        ^              ^
                     booked booked booked booked        booked
                     (seat2)(seat4)(seat5)(seat9)       (seat14)

Underlying Redis string "seats:section-A" (2 bytes for these 16 bits):
  Byte 0 (bits 0-7):   00101100   = 0x2C
  Byte 1 (bits 8-15):  01000010   = 0x42

Booking seat 4:
  SETBIT seats:section-A 4 1
  ─► flips bit 4 within byte 0, no new key created, no row inserted

Checking if seat 4 is booked:
  GETBIT seats:section-A 4
  ─► (integer) 1   (booked)

Checking if seat 6 is booked:
  GETBIT seats:section-A 6
  ─► (integer) 0   (available)

Counting total booked seats in the section:
  BITCOUNT seats:section-A
  ─► (integer) 5    (seats 2, 4, 5, 9, 14 are set)

Finding the FIRST available seat (bit = 0):
  BITPOS seats:section-A 0
  ─► (integer) 0    (seat 0 is the first free seat)

Finding the first available seat AFTER seat 5 (start byte offset):
  BITPOS seats:section-A 0 1        -- search starting at byte 1
  ─► (integer) 8    (seat 8 is free, first 0-bit in byte 1 range)
```

### Combining Bitmaps: Available AND Wheelchair-Accessible

```
Two independent bitmaps for the same 16-seat section:

seats:section-A:booked        (1 = booked, 0 = available)
  0  0  1  0  1  1  0  0  0  1  0  0  0  0  1  0

seats:section-A:wheelchair    (1 = wheelchair-accessible seat)
  0  1  1  0  0  0  0  1  0  0  0  1  0  0  0  0

Step 1: Invert "booked" conceptually — we want AVAILABLE seats,
        so we need a NOT operation. Redis has no native BITNOT
        combining two keys in one step for "available", so the
        common pattern is to maintain an "available" bitmap
        directly (flip to 0 the moment a seat is booked) rather
        than inverting "booked" on every query:

seats:section-A:available     (1 = available, kept in sync with booked)
  1  1  0  1  0  0  1  1  1  0  1  1  1  1  0  1

Step 2: BITOP AND to find seats that are BOTH available AND wheelchair-accessible:
  BITOP AND result:section-A:avail-and-wheelchair \
        seats:section-A:available \
        seats:section-A:wheelchair

  available:     1  1  0  1  0  0  1  1  1  0  1  1  1  1  0  1
  wheelchair:    0  1  1  0  0  0  0  1  0  0  0  1  0  0  0  0
  AND result:    0  1  0  0  0  0  0  1  0  0  0  1  0  0  0  0
                    ^                 ^        ^
                 seat1             seat7    seat11
                 (available AND wheelchair-accessible)

  BITCOUNT result:section-A:avail-and-wheelchair
  ─► (integer) 3

  BITPOS result:section-A:avail-and-wheelchair 1
  ─► (integer) 1    (seat 1 is the first matching seat to offer the user)
```

### Failure Mode: Bitmaps Are Wrong for Sparse/Unbounded ID Spaces

```
BAD USE CASE: "Track which of our 50 million registered user IDs
               have logged in today" using user_id as the bit offset.

  SETBIT logged_in_today 48213907 1
  SETBIT logged_in_today 2 1
  SETBIT logged_in_today 49999999 1

  Problem: Redis allocates a CONTIGUOUS string covering bit 0
  through the highest bit offset used. Setting bit 49999999
  forces Redis to allocate a string of ceil(50,000,000/8) bytes
  = ~6.25 MB — for a SINGLE key — even if only 3 users ever log in.

  If user IDs are sparse (most of the 50M ID space is never
  actually used, or IDs are non-sequential UUIDs/snowflake IDs),
  the bitmap wastes enormous memory representing gaps nobody
  cares about, and you can't even use non-integer IDs as bit
  offsets at all.

  Bitmaps are only a good fit when:
    - The ID space is DENSE (seat 0..9999, all seats exist)
    - The ID space is BOUNDED and known in advance (fixed hall capacity)
    - IDs map naturally to small non-negative integers

  For "has any of billions of arbitrary/sparse IDs been seen" —
  e.g. unique visitor tracking across a huge, growing, non-sequential
  ID space — a Bloom filter is the right structure instead: it
  trades a small, tunable false-positive rate for handling
  effectively unbounded, sparse ID spaces in a fixed memory budget.
  See 027-bloom-filter-hyperloglog-approximate-data-structures.md
  for that tradeoff in depth. HyperLogLog is the analogous choice
  when you only need a *cardinality estimate* (e.g. "how many
  unique visitors today") rather than per-ID membership.
```

---

## PART 3 — INTERNALS, IMPLEMENTATION, AND REAL NUMBERS

### Memory Comparison: Bitmap vs Separate Keys vs Hash

```bash
# Approach 1: Bitmap (this file's recommendation)
# 10,000 seats = 10,000 bits = 1,250 bytes, ONE key.
SETBIT seats:section-A 9999 1
MEMORY USAGE seats:section-A
# -> (integer) 1344   (1,250 bytes payload + ~94 bytes Redis object overhead)

# Approach 2: Separate key per seat (naive)
# SET seat:section-A:0 0 / SET seat:section-A:1 0 / ... x10,000
# Each key: ~56 bytes overhead (key name + robj header + dict entry)
#           + ~48 bytes for a tiny integer-encoded string value
# Total: ~10,000 * ~90 bytes ≈ 900 KB
# -> ~670x more memory than the bitmap for identical information

# Approach 3: Hash with 10,000 fields
# HSET seats:section-A 0 0
# HSET seats:section-A 1 0  ... x10,000
# Redis hash-field-overhead (ziplist/listpack encoding helps small hashes,
# but past hash-max-listpack-entries=128 it converts to a full hash table)
# Realistic overhead once converted: ~70-90 bytes/field
# Total: ~10,000 * 80 bytes ≈ 800 KB
# -> Still ~600x more memory than the bitmap

echo "Bitmap wins because there is zero per-entry key/field overhead —
      only the raw bits themselves are stored."
```

### Realistic Command Set for a Booking Service

```bash
# Book seat 4821 in section A (atomic single-bit flip)
SETBIT seats:section-A 4821 1

# Release seat 4821 (e.g. booking cancelled)
SETBIT seats:section-A 4821 0

# Is seat 4821 currently booked?
GETBIT seats:section-A 4821

# Total booked count in the section (for "X/10000 seats sold" UI)
BITCOUNT seats:section-A

# BITCOUNT scoped to a byte range (seats 800-1599, i.e. bytes 100-199)
BITCOUNT seats:section-A 100 199

# Find the very first available seat (bit=0) for "auto-assign best seat"
BITPOS seats:section-A 0

# Atomicity for a "book if available" check-then-set — use a Lua script
# to avoid a race between two users booking the same seat concurrently:
EVAL "
  local current = redis.call('GETBIT', KEYS[1], ARGV[1])
  if current == 0 then
    redis.call('SETBIT', KEYS[1], ARGV[1], 1)
    return 1  -- booking succeeded
  else
    return 0  -- already booked, race lost
  end
" 1 seats:section-A 4821
```

### Combining Multiple Constraint Bitmaps (Java / Spring)

```java
@Service
public class SeatAvailabilityService {

    @Autowired
    private StringRedisTemplate redis;

    // Find seats that are available AND wheelchair-accessible AND aisle
    public List<Integer> findMatchingSeats(String section, int maxResults) {
        String availableKey    = "seats:" + section + ":available";
        String wheelchairKey   = "seats:" + section + ":wheelchair";
        String aisleKey        = "seats:" + section + ":aisle";
        String resultKey       = "seats:" + section + ":query-result:" + UUID.randomUUID();

        // BITOP AND across three bitmaps in one Redis round trip
        redis.execute((RedisCallback<Object>) connection -> {
            connection.bitOp(RedisStringCommands.BitOperation.AND,
                resultKey.getBytes(), availableKey.getBytes(),
                wheelchairKey.getBytes(), aisleKey.getBytes());
            return null;
        });

        List<Integer> matches = new ArrayList<>();
        long nextOffset = 0;
        while (matches.size() < maxResults) {
            Long pos = redis.execute((RedisCallback<Long>) connection ->
                connection.bitPos(resultKey.getBytes(), true,
                    org.springframework.data.domain.Range.of(
                        org.springframework.data.domain.Range.Bound.inclusive(nextOffset),
                        org.springframework.data.domain.Range.Bound.unbounded())));
            if (pos == null || pos < 0) break;
            matches.add(pos.intValue());
            nextOffset = pos + 1;
        }
        redis.delete(resultKey); // scratch key, clean up after query
        return matches;
    }
}
```

### Real Numbers

```
10,000-seat stadium section, single bitmap key:
  Storage:            1,250 bytes (10,000 bits / 8)
  vs 10,000 separate keys:  ~900 KB   (720x larger)
  vs 10,000-field hash:     ~800 KB   (640x larger)

BITCOUNT latency:     O(N) internally but SIMD/popcount-optimized in C;
                      for a 1.25 KB bitmap this completes in low
                      microseconds — sub-millisecond even under load.

BITPOS latency:       Similar O(N) worst case, but Redis skips
                      whole all-zero/all-one bytes fast, so typical
                      "find first free seat" queries resolve in
                      microseconds for stadium-scale (10K-100K seat)
                      bitmaps.

Daily habit tracker:  365 days/year = 365 bits = ~46 bytes per user
                      per year. Even 100 million users tracked for
                      a full year: 100M * 46 bytes ≈ 4.3 GB total —
                      manageable on a single well-provisioned Redis
                      instance, versus a naive per-day-row schema
                      that would run into billions of rows.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "You're building the seat-availability service for a stadium ticketing platform — a section has 10,000 seats and needs to support 'find me an available wheelchair-accessible aisle seat' queries under heavy concurrent load during a ticket drop. How would you model this in Redis, and why not just use a database table with a `booked` boolean column?"

**You (architect answer):**

> "A database table with a boolean column per seat works functionally, but it's the wrong tool for two reasons: it doesn't compress a fixed, dense, small state space efficiently, and combining multiple boolean attributes — available, wheelchair-accessible, aisle — requires either a multi-column WHERE clause with a full or partial table scan, or a set of separate indexes that still cost real query time.
>
> I'd model each attribute as a Redis Bitmap: one bit per seat, where the bit offset is the seat's fixed index within the section. `seats:section-A:available`, `seats:section-A:wheelchair`, `seats:section-A:aisle` — each is a single Redis string. For 10,000 seats that's exactly 1,250 bytes per bitmap, versus roughly 900KB if I modeled it as 10,000 separate keys, because a bitmap has zero per-entry overhead — it's just the raw bits.
>
> To answer 'find me an available, wheelchair-accessible, aisle seat,' I run `BITOP AND` across the three bitmaps into a scratch result key, then `BITPOS result 1` to get the first matching seat — both operations run in microseconds even under load because Redis's bit operations are implemented with hardware-optimized popcount instructions in C, not application-level loops.
>
> For the actual booking action, I need atomicity — two users can't both win the same seat in a race. I use a small Lua script that does a `GETBIT` check and conditional `SETBIT` in one atomic Redis operation, so there's no window between check and set where a second request can slip in.
>
> The operational concern I'd flag is that bitmaps only make sense because this ID space is dense and bounded — every seat from 0 to 9,999 genuinely exists. If someone later asked me to track something like 'has this arbitrary user ID engaged with today's promotion' across a sparse, unbounded 50-million-ID space, I would NOT reuse this pattern — a bitmap keyed by raw user ID would force Redis to allocate a huge contiguous string to cover the highest ID ever seen, wasting memory on gaps. For that kind of sparse membership tracking I'd reach for a Bloom filter instead, which is built for unbounded ID spaces at the cost of a small, tunable false-positive rate."

---

## PART 5 — DECISION FRAMEWORK

### Bitmap vs Alternatives for Boolean State Spaces

| Approach | How It Works | Tradeoff | Memory (10K items) | Complexity | When It Fails |
|---|---|---|---|---|---|
| **Redis Bitmap** | 1 bit per item, offset = item's fixed integer index | Requires dense, bounded, integer-indexable ID space | ~1.25 KB | Low | Sparse/unbounded IDs waste massive memory (must allocate up to highest offset) |
| **Separate key per item** | `SET item:{id} 0/1` | Simple mental model, but huge per-key overhead | ~900 KB | Low | Doesn't scale past a few thousand items before memory dominates |
| **Redis Hash** | `HSET items {id} {0/1}` | Better than separate keys, still per-field overhead | ~800 KB | Low | Same overhead problem at larger field counts; hash converts to full hashtable past `hash-max-listpack-entries` |
| **Relational DB boolean column** | `SELECT ... WHERE booked=false` | Durable, transactional, but slow for bulk bitwise combos (AND/OR across attributes) | Row-based, larger, plus index overhead | Medium | Multi-attribute "find first matching" queries need composite indexes and don't parallelize as cheaply as `BITOP` |
| **Bloom Filter** | Probabilistic hashed-bit membership test | Trades exactness for handling unbounded/sparse sets in fixed memory | Tunable (fixed regardless of ID sparsity) | Medium | Not applicable here — no false positives allowed when booking a specific seat |

### When bitmaps are right

```
✓ The state space is DENSE and BOUNDED (all N seats/slots genuinely exist)
✓ IDs map naturally to small non-negative integers (seat index, day-of-year)
✓ You need fast aggregate ops: COUNT, FIRST-AVAILABLE, AND/OR/XOR combos
✓ Memory efficiency matters at scale (stadiums, daily/yearly trackers)
✓ Exact correctness is required (unlike Bloom filters, zero false positives)
```

### Skip bitmaps when

```
✗ IDs are sparse or effectively unbounded (arbitrary user IDs, UUIDs)
  -> use a Bloom filter (see 027-bloom-filter-hyperloglog-approximate-data-structures.md)
✗ You only need a cardinality estimate, not per-ID membership
  -> use HyperLogLog (same file above covers this)
✗ You need rich per-entity metadata beyond a single boolean
  -> use a Hash or a relational row (a bit can't carry a price, a name, etc.)
✗ Durability/transactional guarantees across multiple systems matter more
  than raw speed -> a relational DB with proper indexing may be safer
```

---

## QUICK REFERENCE CARD

```
BASIC BIT OPS:
  SETBIT key offset 0|1        -> set/clear a single bit
  GETBIT key offset            -> read a single bit

AGGREGATE OPS:
  BITCOUNT key [start end]     -> count set bits (optionally byte range)
  BITPOS key 0|1 [start end]   -> find first bit matching value

COMBINING BITMAPS:
  BITOP AND destKey key1 key2 [key3 ...]   -> intersection
  BITOP OR  destKey key1 key2 [key3 ...]   -> union
  BITOP XOR destKey key1 key2              -> difference/toggle
  BITOP NOT destKey key1                   -> invert

ATOMIC CHECK-THEN-SET (Lua):
  local cur = redis.call('GETBIT', KEYS[1], ARGV[1])
  if cur == 0 then redis.call('SETBIT', KEYS[1], ARGV[1], 1); return 1 end
  return 0

MEMORY RULE OF THUMB:
  N bits ≈ N/8 bytes, ONE key, near-zero per-entry overhead

WHEN TO USE INSTEAD:
  Sparse/unbounded IDs      -> Bloom filter
  Cardinality estimate only -> HyperLogLog
  Rich per-entity metadata  -> Hash or relational row
```

---
