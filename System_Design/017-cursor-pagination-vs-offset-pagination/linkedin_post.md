# Cursor-Based Pagination vs Offset Pagination — LinkedIn Post

## Post Text (copy-paste ready)

100 concurrent users on page=50000 = 50 million wasted row scans for 1,000 useful rows.

- Offset pagination is O(offset + limit): `LIMIT 10 OFFSET 500000` scans and discards 500,000 rows just to return 10.
- It's also broken on live data — insert 5 new posts between page 1 and page 2, and OFFSET shifts everything down, so users see duplicates.
- Cursor pagination is O(log N + K): `WHERE (created_at, id) < (cursor_time, cursor_id)` is a direct B-tree seek — page 50,000 costs the same as page 1.
- It needs one composite index: `(created_at DESC, id DESC)` — skip it and cursor pagination silently becomes a full table scan.
- Offset isn't dead: admin dashboards that jump to "page 47" still need it — just cap it (e.g. page ≤ 100) to prevent abuse.
- Real numbers: an OTT catalog with 10M videos scans 200,000 index entries per page at OFFSET 200,000; cursor pagination touches ~10 rows, same as page 1.

Swipe → to see: offset vs cursor SQL, the duplicate-data bug walkthrough, and the required index.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
Offset pagination scans 500K rows to return 10. Cursor pagination doesn't. Here's why page 50,000 should cost the same as page 1.

### Variant B — Long (400–600 chars)
Most APIs paginate with `LIMIT 10 OFFSET 500000` — and MySQL scans all 500,010 rows just to throw away 500,000 of them. At 100 users hitting page=50000 at once, that's 50 million wasted row scans for 1,000 useful rows. Worse, offset pagination duplicates data when new rows are inserted mid-scroll. Cursor pagination fixes both: a `(created_at DESC, id DESC)` index turns "skip N rows" into a direct seek, so page 1 and page 50,000 cost exactly the same. Offset still wins for admin dashboards that need to jump to an exact page number — just cap the depth. Full breakdown in the carousel.

---

## Best Time to Post
Tuesday–Thursday, 8–10 AM local time (developer audiences check LinkedIn before standup) or 12–1 PM lunch scroll window.

## Engagement Hook
Ask in the comments: "What's the deepest page number your API has ever had to serve — and did it hurt?"
