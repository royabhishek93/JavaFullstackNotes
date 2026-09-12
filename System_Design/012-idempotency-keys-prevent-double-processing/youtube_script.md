# Idempotency Keys — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE | Episode: 13 of 20

## HOOK (0:00–0:30)
"A user taps 'Pay $100.' The server charges the card, creates the order, and the response gets lost on the way back due to a network drop. The user sees a timeout, taps 'Pay' again. Same $100 gets charged a second time. This isn't a rare edge case — it's the default behavior of every retry-capable client on a flaky network, unless you build in exactly one header: Idempotency-Key. Today I'm showing you how it works, end to end."

[Screen cue: A phone showing "Payment failed, retry?" tapped twice, then a bank statement showing TWO $100 charges.]

## THE PROBLEM (0:30–2:00)
"Think about it this way — idempotency means calling an operation multiple times with the same input produces the exact same result as calling it once. `DELETE /users/42` is naturally idempotent — call it three times, the user is deleted either way, same end state. But `POST /payments` is NOT idempotent by default — call it three times, you get three separate charges, because each call is treated as a brand new operation. Networks are unreliable. Clients retry. That combination, without protection, means duplicate charges, duplicate orders, duplicate emails — anywhere a client can retry a state-changing request."

[Screen cue: Draw two columns — "GET/DELETE: naturally idempotent" with a green check, vs "POST: NOT idempotent by default" with a red X.]

## THE SOLUTION (2:00–5:00)
"Now watch how the fix actually works. Before the user even taps 'Pay,' the client generates a random UUID — this is the idempotency key — and stores it locally. Every attempt, including every retry, sends this SAME key in an Idempotency-Key header. On the server: first, look up this key in an idempotency_keys table. If it's already there, return the CACHED response immediately — no charging, no new order, nothing processed again. If it's not there, process the payment normally, then store the key alongside the response with a twenty-four-hour expiry, matching exactly what Stripe does in production. So on the very first attempt, the server debits the account, creates order number 1001, and caches that result under the key. The network drops before the client sees the response. The client retries with the identical key. The server finds the key already exists, and simply returns 'order 1001, charged $100' without touching the database again. The user is charged exactly once, and both attempts show the same successful result."

[Screen cue: Draw the timeline — first attempt (process + cache) → network drop → retry (cache hit, no processing) → same response returned.]

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)
"Here's the trap: a naive implementation checks 'does this key exist?' and THEN processes if it doesn't — but if two retries arrive at almost the exact same moment, both can pass the 'key doesn't exist' check before either one finishes writing, and you get a race condition producing two orders anyway. The fix is a database-level unique constraint on the key column itself, used as a lock: you INSERT the key with status PROCESSING using an ON DUPLICATE KEY clause that's a no-op if it already exists — whichever request's INSERT actually succeeds 'owns' the operation and proceeds, and the other request sees the duplicate-key failure and knows to return the cached result or wait. Second trap, and this one is subtle: engineers only cache SUCCESSFUL responses. If the first attempt fails with 'insufficient funds,' and you don't cache that failure, the retry re-runs the balance check from scratch — and if the user's balance happened to change in between, for example money arrived from another source, the retry might now succeed where the original correctly failed, silently changing the outcome of what the user believes was a single operation. The fix: cache BOTH success and failure responses under the same key, so a retry of a failed attempt returns that exact same failure, preserving the original decision. And a third trap: forgetting to scope the key to the user. If idempotency keys aren't tied to (key, user_id) together, one user could theoretically reuse or guess another user's key and get back THEIR cached response — a real security and privacy issue, not just a correctness one."

[Screen cue: Split diagram — two simultaneous requests both passing a naive check (race condition, red X), then the correct version using an INSERT-with-unique-constraint as a lock (green check).]

## REAL WORLD (8:00–9:30)
"Think about PhonePe or Paytm — a payment retry after a dropped connection is exactly the scenario idempotency keys were built for, and getting this wrong at UPI scale means real, reportable double-debits affecting real bank accounts. Think about Swiggy or Zomato order placement — a network timeout during checkout followed by an automatic client retry should never create two separate orders and two separate charges; the idempotency key guarantees the second request just returns the first order's ID. And think about a ticket-booking platform like BookMyShow during a high-demand release — a client retrying a seat reservation on a timeout must not be allowed to attempt reserving that seat twice; the idempotency key makes the second attempt simply return the first reservation instead of creating a conflicting duplicate booking attempt."

[Screen cue: Three logo-style cards — "PhonePe/Paytm: retry-safe UPI payments", "Swiggy/Zomato: no duplicate orders on timeout", "BookMyShow: no duplicate seat reservations".]

## OUTRO + NEXT EPISODE (9:30–10:00)
"So remember: the client generates the key once, before the first attempt, sends it on every retry, and the server caches the full result — success OR failure — keyed by that value, scoped to the user, protected by a database unique constraint against race conditions. Subscribe for Episode 14, where we cover content-addressable storage — including exactly how Dropbox and Git store a one-gigabyte file edit by uploading just four megabytes."

[Screen cue: "NEXT: Episode 14 — Content-Addressable Storage" title card with subscribe animation.]
