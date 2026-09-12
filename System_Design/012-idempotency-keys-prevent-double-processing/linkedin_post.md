# Idempotency Keys — LinkedIn Post

## Post Text (copy-paste ready)

A network drop + a retry button = your customer charged twice. One header fixes it.

- POST /payments is NOT idempotent by default — call it 3 times, you get 3 charges, because each call is treated as brand new
- Fix: client generates a UUID before the first attempt, sends it as Idempotency-Key on every retry — server caches the result and returns it on duplicate keys instead of processing again
- The race condition trap: 2 retries arriving simultaneously can both pass a naive "does this key exist?" check before either finishes — fix with a DB-level unique constraint used as a lock
- Cache BOTH success AND failure responses — if you only cache success, a retried "insufficient funds" failure might silently succeed the second time if the balance changed in between
- Scope keys to (key + user_id) — otherwise one user could reuse or guess another user's key and get their cached response back

Swipe → to see the exact server-side flow (lookup → INSERT-as-lock → process → cache) and the header names Stripe, PayPal, and Twilio each use.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
A dropped network connection + a retry = double-charged customer. Here's the exact header that prevents it 👇

### Variant B — Long (400–600 chars)
POST requests aren't idempotent by default — retry one 3 times and you get 3 charges, 3 orders, 3 emails. The fix: the client generates a UUID before the first attempt and sends it as an Idempotency-Key header on every retry. The server caches the result under that key and returns it on duplicate requests instead of reprocessing. The trap most implementations miss: caching only success responses, and not protecting against simultaneous retries with a database-level unique constraint.

---

## Best Time to Post
Wednesday, 9:00–10:00 AM IST (practical payment/reliability content performs consistently mid-week)

## Engagement Hook
"Has a missing idempotency key ever caused a double-charge or duplicate-order bug on your team?"
