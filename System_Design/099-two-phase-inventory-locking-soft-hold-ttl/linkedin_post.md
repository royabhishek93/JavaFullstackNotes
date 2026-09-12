# Two-Phase Inventory Locking: Soft-Hold + TTL Pattern — LinkedIn Post

## Post Text (copy-paste ready)

A user sitting on checkout for 3 minutes shouldn't hold a database lock for 3 minutes. Here's the 2-phase fix.

- Phase 1 (soft hold): `SET seat:F12 userId:token NX EX 600` — one atomic Redis command, no DB touched, self-expires in 10 min if the user abandons checkout
- Phase 2 (confirm): only on payment success, open a real DB transaction and INSERT the permanent row — held for 2-8ms, not minutes
- The dangerous race: payment confirms right as the TTL expires, another user grabs the now-free seat, and a naive GET-then-DEL from app code silently destroys their legitimate hold — or worse, double-books the seat
- Fix: a single atomic Lua script that checks "does this hold still belong to me?" and only deletes if it matches — never a separate GET then DEL
- Monitor hold-to-confirm conversion rate — a healthy funnel converts 30-50%; below 10% usually means bot scalping mass-holding inventory

Swipe → to see the exact Redis + Lua flow and why `SELECT ... FOR UPDATE` for the whole checkout flow causes instant connection pool exhaustion.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
A user on checkout for 3 minutes shouldn't lock a DB row for 3 minutes. Here's the 2-phase Redis + DB pattern that fixes it 👇

### Variant B — Long (400–600 chars)
Holding a database row lock for the entire user checkout flow — browsing, payment entry, gateway callback — can take minutes and exhausts your connection pool under concurrent demand on a hot item. The fix: a cheap, self-expiring Redis soft-hold (`SET NX EX`) for the long "user is deciding" phase, and a real DB transaction only at the split-second moment payment actually succeeds. The trap: confirming a hold safely requires an atomic Lua check-and-delete, never a naive GET-then-DEL, or you risk destroying someone else's legitimate hold.

---

## Best Time to Post
Monday, 9:00–10:00 AM IST (practical production pattern content performs well opening the week)

## Engagement Hook
"Have you ever seen bot scalping mass-hold inventory in a flash sale? How did your team detect and mitigate it?"
