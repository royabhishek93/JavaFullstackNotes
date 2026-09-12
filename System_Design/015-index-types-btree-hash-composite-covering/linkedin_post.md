# Index Types — B-Tree vs Hash vs Composite vs Covering Index — LinkedIn Post

## Post Text (copy-paste ready)

A hash index gives O(1) lookups. Your B-tree gives O(log N). Are you picking the right one?

- B-Tree is the default — handles =, >, <, BETWEEN, and ORDER BY. Use it 95% of the time.
- Hash index is equality-only — no ranges, no sorting, but O(1) instead of O(log N).
- Composite index follows the left-prefix rule — skip the leftmost column in your WHERE clause and MySQL can't use the index at all.
- Covering index stores every column your query needs — EXPLAIN shows "Using index" instead of "Using index; Using where," meaning zero table heap reads.
- Column order in a composite index matters: equality columns first, range columns last.

Swipe → to see: how Tiny URL uses a hash index on short_code to serve 100K QPS at O(1), and how a covering index eliminates table reads for an e-commerce product query.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
Hash = O(1). B-tree = O(log N). Composite = left-prefix rule. Covering = no table reads. Pick the right index, not just any index.

### Variant B — Long (400–600 chars)
Every system design interview has a database, and every database question eventually leads to "how do you make that query fast?" The answer is almost never "add an index" — it's "add the right index." Tiny URL needs a hash index on short_code for O(1) equality lookups at 100K QPS. Instagram needs a composite index on (user_id, created_at) to serve timelines without a second index. E-commerce needs a covering index so EXPLAIN shows "Using index" with zero table heap fetches. Know the shape of your query before you pick the index type.

---

## Best Time to Post
Tuesday, 8:30 AM IST

## Engagement Hook
What's the worst "just add an index" advice you've seen backfire in production?
