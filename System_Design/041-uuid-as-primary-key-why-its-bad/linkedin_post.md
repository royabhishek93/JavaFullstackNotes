# UUID as Primary Key: Why It's Bad — LinkedIn Post

## Post Text (copy-paste ready)

Your UUID primary key is quietly wasting 40-50% of your table's disk space. Here's why.

- MySQL InnoDB stores rows physically sorted by primary key (clustered index) — random UUID inserts land at random positions, not the end of the table
- Every random insert into a full page triggers a page split — at 10K inserts/sec that's thousands of splits per second, each a random disk write
- After 6 months of UUID inserts, pages average ~48% full vs. 90-95% for AUTO_INCREMENT — meaning 2x the disk space and 2x the pages read on every table scan
- Fix for internal IDs: BIGINT AUTO_INCREMENT as the clustered PK, with a separate UUID `public_id` column for external/API exposure
- Need global uniqueness without the fragmentation? Use ULID or UUID v7 — both are time-ordered so inserts stay near the end of the index
- A Flipkart-style flash sale pushing 10K+ orders/sec keeps zero fragmentation with sequential BIGINT PKs — the same load with UUID PKs scatters writes across the entire B-tree

Swipe → to see the B-tree page-split diagram, the fragmentation comparison, and the exact decision tree for AUTO_INCREMENT vs ULID vs UUID v4.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
UUID primary keys can silently cost you 40-50% disk fragmentation. Here's the B-tree math every backend engineer should know 👇

### Variant B — Long (400–600 chars)
Ever wondered why your MySQL table with UUID primary keys feels bloated even though row counts look normal? It's not your imagination — InnoDB physically sorts rows by primary key, so random UUID inserts force constant B-tree page splits instead of clean appends. Over time, pages settle around 48% full instead of 90%+, doubling your disk footprint and table scan cost. The fix isn't "avoid UUIDs" — it's picking the right one: BIGINT AUTO_INCREMENT internally, ULID or UUID v7 when you need global, time-sortable uniqueness. Swipe through for the full breakdown, real fragmentation numbers, and the flash-sale example that makes this click.

---

## Best Time to Post
Tuesday or Wednesday, 8:30–9:30 AM IST (commute scroll time for Indian tech professionals) or 8:00–9:00 PM IST (post-dinner wind-down scroll)

## Engagement Hook
What's your rule of thumb — AUTO_INCREMENT, ULID, or UUID v4? Drop your primary key strategy below and let's compare notes.
