# Optimistic vs Pessimistic Locking — LinkedIn Post

## Post Text (copy-paste ready)

Two people click "Book" on the last airline seat at the same instant. Who wins?

- Pessimistic: SELECT FOR UPDATE locks the row on read — the second reader just blocks until you commit.
- Optimistic: add a version column; UPDATE...WHERE version=N fails with 0 rows affected if someone beat you to it.
- Deadlock rule: always lock rows in the same order across every transaction, or two transactions will wait on each other forever.
- High contention (seat booking, account debits)? Go pessimistic. Conflict rate under 10%? Go optimistic and retry.
- Real example: a Payment System uses SELECT FOR UPDATE on the account row so two concurrent debits can't both read balance=1000 and push it negative.

Swipe → to see the timelines, the SQL, and the decision framework.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
Two users, one seat, one lost-update bug. Here's how pessimistic vs optimistic locking stops the double-booking — and the deadlock rule to know.

### Variant B — Long (400–600 chars)
Two users see seat 14A as "available" at the same time. Both write "booked by me." Without locking, both win — and one passenger stands at the gate. That's a lost update, and it's a classic system design interview probe.

Pessimistic locking (SELECT FOR UPDATE) locks the row immediately so the second reader blocks — used for seat booking and payment debits where a conflict means real money or a real seat is at stake. Optimistic locking (a version column, UPDATE...WHERE version=N) skips locks entirely and just fails the write if the version moved — great for low-contention updates like profile edits.

The rule that saves you from deadlocks either way: always lock rows in the same order across every transaction.

---

## Best Time to Post
Tuesday–Thursday, 8–10 AM local time — when engineers are scrolling before standups and engagement on technical carousels peaks.

## Engagement Hook
Ask in the comments: "Would you use pessimistic or optimistic locking for a flash-sale checkout — and why?" Reply to the first few answers to boost early comment velocity.
