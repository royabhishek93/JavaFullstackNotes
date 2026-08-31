# BookMyShow - Design Comparison & Scoring Tables

## 📊 Technology Choices Comparison

```
┌───────────────────────┬───────────────────────────────────────┬──────────────────────────────────────┐
│       Component       │            Why This Choice            │        Alternative Considered        │
├───────────────────────┼───────────────────────────────────────┼──────────────────────────────────────┤
│ PostgreSQL for        │ ACID compliance, row-level locks (FOR │ MySQL (weaker locking)               │
│ Bookings              │  UPDATE)                              │                                      │
├───────────────────────┼───────────────────────────────────────┼──────────────────────────────────────┤
│ MySQL for Catalog     │ Read-heavy, mature replication, lower │ PostgreSQL (overkill for static      │
│                       │  cost                                 │ data)                                │
├───────────────────────┼───────────────────────────────────────┼──────────────────────────────────────┤
│ Elasticsearch for     │ Full-text search, geo-spatial,        │ PostgreSQL (too slow for fuzzy       │
│ Search                │ faceted filters                       │ search)                              │
├───────────────────────┼───────────────────────────────────────┼──────────────────────────────────────┤
│ Redis Cache           │ Sub-50ms latency, pub/sub for         │ Memcached (no pub/sub)               │
│                       │ real-time                             │                                      │
├───────────────────────┼───────────────────────────────────────┼──────────────────────────────────────┤
│ Kafka                 │ Durable message queue, replay         │ RabbitMQ (less throughput)           │
│                       │ capability                            │                                      │
├───────────────────────┼───────────────────────────────────────┼──────────────────────────────────────┤
│ FOR UPDATE Lock       │ Prevents double-booking race          │ Optimistic locking (too many retries │
│                       │ conditions                            │  at scale)                           │
└───────────────────────┴───────────────────────────────────────┴──────────────────────────────────────┘
```

---

## ✅ Must Have (Core - 70% of Score)

```
┌──────────────────────┬─────────────────────────────┬──────────────────────────────┐
│     Requirement      │         Your Design         │          Production          │
├──────────────────────┼─────────────────────────────┼──────────────────────────────┤
│ Show Entity          │ ❌ Missing                  │ ✅ Required                  │
├──────────────────────┼─────────────────────────────┼──────────────────────────────┤
│ Seat Entity          │ ❌ Missing                  │ ✅ Required                  │
├──────────────────────┼─────────────────────────────┼──────────────────────────────┤
│ SeatAvailability     │ ❌ Missing                  │ ✅ Required                  │
├──────────────────────┼─────────────────────────────┼──────────────────────────────┤
│ Payment Entity       │ ❌ Missing                  │ ✅ Required                  │
├──────────────────────┼─────────────────────────────┼──────────────────────────────┤
│ Concurrency Control  │ ❌ None                     │ ✅ FOR UPDATE locks          │
├──────────────────────┼─────────────────────────────┼──────────────────────────────┤
│ Booking Expiry       │ ❌ None                     │ ✅ 15-min hold               │
├──────────────────────┼─────────────────────────────┼──────────────────────────────┤
│ Proper Relationships │ ❌ Wrong (1:1 User-Booking) │ ✅ Correct (1:N)             │
├──────────────────────┼─────────────────────────────┼──────────────────────────────┤
│ Normalization        │ ❌ Movie has show_time      │ ✅ Separate Show entity      │
├──────────────────────┼─────────────────────────────┼──────────────────────────────┤
│ Indexes              │ ❌ None                     │ ✅ On all FKs, dates, status │
├──────────────────────┼─────────────────────────────┼──────────────────────────────┤
│ Audit Timestamps     │ ❌ Only "date" in User      │ ✅ created_at, updated_at    │
└──────────────────────┴─────────────────────────────┴──────────────────────────────┘
```

**Your Score: 1/10** (Only Review entity is acceptable)

---

## ✅ Should Have (Senior Level - 20% of Score)

```
┌───────────────────┬─────────────┬──────────────────────────────────────┐
│      Feature      │ Your Design │              Production              │
├───────────────────┼─────────────┼──────────────────────────────────────┤
│ Status Enums      │ ❌ None     │ ✅ booking_status, payment_status    │
├───────────────────┼─────────────┼──────────────────────────────────────┤
│ Soft Deletes      │ ❌ None     │ ✅ deleted_at (for audit)            │
├───────────────────┼─────────────┼──────────────────────────────────────┤
│ Idempotency       │ ❌ None     │ ✅ Unique booking_id, transaction_id │
├───────────────────┼─────────────┼──────────────────────────────────────┤
│ Sharding Strategy │ ❌ None     │ ✅ Shard by city_id                  │
├───────────────────┼─────────────┼──────────────────────────────────────┤
│ Read Replicas     │ ❌ None     │ ✅ For search queries                │
└───────────────────┴─────────────┴──────────────────────────────────────┘
```

---

## ✅ Good to Have (Staff/Principal Level - 10% of Score)

```
┌───────────────────┬─────────────┬──────────────────────────────┐
│      Feature      │ Your Design │          Production          │
├───────────────────┼─────────────┼──────────────────────────────┤
│ Saga Pattern      │ ❌ None     │ ✅ Reserve → Pay → Confirm   │
├───────────────────┼─────────────┼──────────────────────────────┤
│ Event Sourcing    │ ❌ None     │ ✅ Kafka events              │
├───────────────────┼─────────────┼──────────────────────────────┤
│ Cache Strategy    │ ❌ None     │ ✅ Redis for seat status     │
├───────────────────┼─────────────┼──────────────────────────────┤
│ Real-time Updates │ ❌ None     │ ✅ WebSocket + Redis Pub/Sub │
├───────────────────┼─────────────┼──────────────────────────────┤
│ Rate Limiting     │ ❌ None     │ ✅ Token bucket per user     │
└───────────────────┴─────────────┴──────────────────────────────┘
```

---

## 🔧 To Make This Production-Ready

You need **at minimum**:

1. **Add 6 missing entities**: Show, Seat, SeatAvailability, Payment, Theater, BookingSeat
2. **Fix User → Booking relationship**: Move booking_id from User to Booking (user_id)
3. **Normalize Movie**: Remove show_time, city, pin_code (belongs to Show/Theater)
4. **Add concurrency control**: `FOR UPDATE` locks in SeatAvailability
5. **Add booking lifecycle**: PENDING → CONFIRMED/EXPIRED
6. **Add indexes**: On all foreign keys, status fields, dates
7. **Add audit fields**: created_at, updated_at on all tables
8. **Add payment flow**: 3-phase commit (Reserve → Charge → Confirm)

---

## 🎯 Interview Walkthrough Comparison

### ❌ Your Current Design's Answer:

```
1. User clicks seat 5
2. Insert into Booking table
3. Done

Issues interviewer will catch:
- "What if two users click simultaneously?" → Double booking
- "Where's the Show entity?" → Can't track showtime
- "What about payment?" → No payment table
- "How do you know which seat?" → No Seat/BookingSeat entities
- "User has booking_id FK, so only 1 booking ever?" → Relationship error
```

**Interview Outcome**: ❌ Fail (wouldn't progress to architecture/scaling questions)

---

### ✅ Production Design's Answer:

```
1. User clicks Seat 5 for Show 123

2. BEGIN TRANSACTION (SERIALIZABLE)

3. Lock the seat row:
   SELECT * FROM seat_availability
   WHERE show_id=123 AND seat_id=5
   FOR UPDATE;

4. Check if AVAILABLE:
   IF status != 'AVAILABLE':
       ROLLBACK; return "Seat taken"

5. Reserve seat:
   - INSERT INTO booking (user_id, show_id, status='PENDING', expires_at=NOW()+15mins)
   - INSERT INTO booking_seat (booking_id, seat_id)
   - UPDATE seat_availability SET status='RESERVED', reserved_until=NOW()+15mins

6. COMMIT

7. Return: "Seat reserved for 15 minutes, please complete payment"

8. User pays:
   - Call payment gateway (Stripe)
   - IF success: UPDATE booking SET status='CONFIRMED', payment_id='stripe_xyz'
   - IF fail: Release seat (status='AVAILABLE')

9. Async: Send confirmation email, publish Kafka event
```

**Interview Outcome**: ✅ Pass (proceeds to scaling, caching, distributed systems)

---

## 📊 Red Flags Summary

| Red Flag | What Interviewer Thinks |
|----------|------------------------|
| Missing Show entity | "Doesn't understand movie booking domain" |
| booking_id in User | "Weak database fundamentals (1:N relationships)" |
| show_time in Movie | "Doesn't understand normalization" |
| No concurrency control | "Wouldn't survive production (race conditions)" |
| No Payment entity | "Hasn't built financial systems" |
| No indexes | "Doesn't think about performance" |
| No timestamps | "Hasn't debugged production issues" |

**Overall Assessment**: "Junior-level candidate, needs mentoring"

---

## 🎯 Interview Level Assessment

```
┌───────────────┬─────────────────────────────────────┬─────────────────────┐
│ Design Quality│              Level                  │ Your Current Design │
├───────────────┼─────────────────────────────────────┼─────────────────────┤
│ Intern/Junior │ Basic CRUD, simple relationships    │ ❌ Below this       │
│               │                                     │ (fundamental errors)│
├───────────────┼─────────────────────────────────────┼─────────────────────┤
│ Mid-Level     │ Normalized schema, proper           │ ❌ Missing          │
│               │ relationships                       │                     │
├───────────────┼─────────────────────────────────────┼─────────────────────┤
│ Senior        │ Concurrency control, payment flow,  │ ❌ Missing          │
│               │ indexes                             │                     │
├───────────────┼─────────────────────────────────────┼─────────────────────┤
│ Staff/        │ Sharding, caching, distributed      │ ❌ Missing          │
│ Principal     │ systems                             │                     │
└───────────────┴─────────────────────────────────────┴─────────────────────┘
```

**Verdict**: This design would **not pass a mid-level interview**, let alone senior/staff.

---

## 💡 Key Takeaway

For a **production-ready interview**, you need to demonstrate:

1. ✅ **Domain understanding** (Show, Seat, Booking lifecycle)
2. ✅ **Database fundamentals** (relationships, normalization, indexes)
3. ✅ **Concurrency** (locking, race conditions)
4. ✅ **Scale thinking** (sharding, caching, replicas)
5. ✅ **Operational maturity** (audit, monitoring, soft deletes)

Your current design shows **0/5** of these. Start with fixing the fundamental schema first!
