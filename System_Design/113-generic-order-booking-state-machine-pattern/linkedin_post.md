# The Generic Order/Booking State Machine Pattern — LinkedIn Post

## Post Text (copy-paste ready)

A cancelled order got shipped. `is_cancelled=true` AND `is_shipped=true` — same row, same time.

Here's why it happened, and the pattern that makes it structurally impossible:

- 5 boolean flags (`is_paid`, `is_shipped`, `is_cancelled`, `is_refunded`, `is_delivered`) give you 2^5 = 32 possible combinations — but maybe 8 are actually legal. Nothing enforces the difference.
- The fix: one `status` enum column + an explicit transition table — `Map<(CurrentState, Event), NextState>`. Anything not in the table is rejected before it touches the DB, not silently allowed.
- Once an order ships, cancellation can't be a backward transition — it needs its own return/refund flow. `(SHIPPED, CustomerCancelled)` simply isn't in the table.
- Every transition writes to `status` AND an append-only `status_history` table in the SAME transaction — that's your audit trail when a customer disputes a charge.
- Duplicate webhooks and out-of-order queue events aren't edge cases, they're guaranteed: on a platform doing ~400K orders/day, illegal-transition rejections run 0.3–0.8% of attempts — mostly retries the transition table safely no-ops instead of double-processing.

Swipe → to see the state machine diagram, the persistence pattern, and the comparison against boolean flags, workflow engines, and event sourcing.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
Booleans let "cancelled AND shipped" both be true. State machines make it impossible. Full breakdown 👇

### Variant B — Long (400-600 chars)
Every "add a status flag" PR is a future data-integrity bug waiting to happen. `is_paid`, `is_shipped`, `is_cancelled` — five independent booleans give you 32 combinations when only ~8 are legal business states, and nothing stops the other 24. The fix used across payments, food delivery, ticket booking, and job schedulers is the same: one status enum, one transition table (`(state, event) → nextState`), reject anything not listed, and log every transition to an append-only history table in the same transaction as the status update. On a 400K-order/day platform, that guard alone catches 0.3–0.8% of transition attempts as illegal — mostly duplicate webhooks and out-of-order queue events — before they become silent corruption. Full pattern breakdown, code, and comparison table in the carousel.

---

## Best Time to Post
Tuesday or Wednesday, 8:00–9:30 AM IST (before the Indian tech workday starts, catches commute + pre-standup scrolling)

## Engagement Hook
Have you ever debugged a "impossible" state in production caused by boolean flags disagreeing with each other? Drop the flag names below 👇
