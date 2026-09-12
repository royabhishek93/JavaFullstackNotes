# The N+1 Query Problem — LinkedIn Post

## Post Text (copy-paste ready)

100 orders = 101 database queries = 202ms instead of 5ms with a JOIN.

Your ORM is doing this to you right now and you don't know it:

- LAZY loading + a for-loop = 1 query for the list, then N more queries — one per row — instead of 1.
- Fix 1: JOIN FETCH (JPQL) — pulls parent + children in a single query.
- Fix 2: @EntityGraph — same result, cleaner Spring Data syntax, Hibernate auto-generates the LEFT JOIN.
- Fix 3: @BatchSize(25) — turns 100 queries into 4 batched IN-clause queries.
- Fix 4: DTO Projection — flattens everything into 1 query, best perf for read-only endpoints.
- Diagnostic rule: if response time grows linearly with result size, it's N+1. Flat = fine.
- Watch out: JOIN FETCH can create a cartesian product (100 orders × 10 items = 1000 rows) — fix with DISTINCT.

Real numbers: a social media feed at 1M concurrent users turns 1M queries/sec into 21M queries/sec from one unguarded @OneToMany. An e-commerce search page for 40 products fires 81 queries fetching seller + rating info separately.

Swipe → to see the waiter analogy (11 trips vs 2), the SQL log proof, and all 4 fixes side-by-side.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
100 orders → 101 queries → 202ms. One @OneToMany, one for-loop, and your DB is on fire. Here's how to spot and fix N+1. Save this.

### Variant B — Long (400–600 chars)
Your `/orders` endpoint takes 500ms for 100 orders and 1000ms for 200. That linear growth is the tell: N+1 queries. One query fetches the list, then your ORM lazily fires one more query per row — 100 orders becomes 101 round trips instead of 1 JOIN. At 1M concurrent users, a single unguarded feed relationship turns 1M queries/sec into 21M. The fix isn't one trick — it's four: JOIN FETCH, @EntityGraph, @BatchSize batching, or DTO projection, depending on your access pattern. Swipe through the breakdown, including the cartesian product trap JOIN FETCH can create. Save this for your next system design interview.

---

## Best Time to Post
Tuesday–Thursday, 8–10 AM local time — highest engagement window for technical/career content on LinkedIn as professionals check feeds before starting work.

## Engagement Hook
Ask in the comments: "What's the highest queries-per-request you've seen in production?" — invites developers to share war stories and boosts comment-driven reach.
