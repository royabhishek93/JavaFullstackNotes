# How do you implement infinite scroll with cursor pagination correctly?

> **Interview priority:** SHOULD KNOW

## Question

How do you implement infinite scroll with cursor pagination correctly?

## Beginner Lens

Watch the scroll position: when user scrolls near the bottom, load the next page. The tricky parts are: (1) preventing duplicate requests, (2) handling race conditions when scrolling fast, (3) using cursor-based pagination instead of offset/limit to avoid showing duplicate posts when new items are added, and (4) caching pages so scrolling up doesn't refetch.

## Detailed Explanation

**HOW TO SAY IT (spoken to interviewer):**

> "Infinite scroll seems simple until you hit production with real users scrolling fast, network latency, and new posts being added while they browse. I've seen apps show duplicate posts, skip posts, or fire 50 requests at once. The key decisions are: scroll detection strategy, pagination approach (cursor vs offset), race condition handling, and cache management. Let me show the exact failure cases..."

```
REAL APP: Social Feed — Infinite Scroll with Bugs
─────────────────────────────────────────────────────────────────

NAIVE IMPLEMENTATION (has multiple bugs):
────────────────────────────────────────────────────────────────

function Feed() {
  const [posts, setPosts] = useState([]);
  const [page, setPage] = useState(1);

  useEffect(() => {
    fetch(`/api/posts?page=${page}&limit=20`)
      .then(r => r.json())
      .then(data => setPosts(prev => [...prev, ...data]));
  }, [page]);

  const handleScroll = () => {
    if (window.innerHeight + window.scrollY >= document.body.offsetHeight) {
      setPage(prev => prev + 1);  // ← BUG: fires multiple times
    }
  };

  useEffect(() => {
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div>
      {posts.map(post => <PostCard key={post.id} post={post} />)}
    </div>
  );
}

BUGS:
─────────────────────────────────────────────────────────────────

1. DUPLICATE REQUESTS
   User scrolls to bottom → handleScroll fires
   ├─ setPage(2) → fetch page 2 starts
   ├─ User still scrolling (page 2 not loaded yet)
   ├─ handleScroll fires AGAIN (still at bottom)
   ├─ setPage(3) → fetch page 3 starts
   └─ Result: pages 2 and 3 loading simultaneously ❌
      (page 3 might finish first → wrong order)

2. OFFSET PAGINATION DUPLICATES
   Timeline:
   t=0:   User loads page 1 (posts 1-20)
   t=10:  Someone posts new content (new post becomes #1)
          Now old post #1 is at position #2
   t=20:  User scrolls → loads page 2 (posts 21-40)
          BUT: server now returns old posts 20-39
          ├─ Post #20 appears TWICE (was in page 1, now in page 2)
          └─ Post #21 SKIPPED ❌

3. NO LOADING STATE
   User scrolls → new posts loading
   No spinner → user thinks nothing is happening
   User scrolls more → fires more requests ❌

4. NO END DETECTION
   User scrolls past all posts → keeps requesting page 999, 1000, 1001...
   Server returns [] but client keeps trying ❌
```

```
VISUAL DIAGRAM — OFFSET PAGINATION PROBLEM:
─────────────────────────────────────────────────────────────────

Database posts (ordered by creation time):

INITIAL STATE (t=0):
┌──────┬──────────────┬──────────────┐
│ ID   │ Content      │ Position     │
├──────┼──────────────┼──────────────┤
│ 100  │ Post 100     │ 1  ← page 1  │
│ 99   │ Post 99      │ 2            │
│ 98   │ Post 98      │ 3            │
│ ...  │ ...          │ ...          │
│ 81   │ Post 81      │ 20 ← page 1  │
│ 80   │ Post 80      │ 21 ← page 2  │
│ 79   │ Post 79      │ 22           │
│ ...  │ ...          │ ...          │
└──────┴──────────────┴──────────────┘

User loads page 1: GET /api/posts?page=1&limit=20
  → Returns posts 100-81 ✅

NEW POST ADDED (t=10):
┌──────┬──────────────┬──────────────┐
│ ID   │ Content      │ Position     │
├──────┼──────────────┼──────────────┤
│ 101  │ NEW POST     │ 1  ← new!    │
│ 100  │ Post 100     │ 2  ← shifted │
│ 99   │ Post 99      │ 3  ← shifted │
│ ...  │ ...          │ ...          │
│ 81   │ Post 81      │ 21 ← shifted │
│ 80   │ Post 80      │ 22 ← shifted │
└──────┴──────────────┴──────────────┘

User scrolls → loads page 2: GET /api/posts?page=2&limit=20
  → Returns posts at positions 21-40
  → NOW includes post 81 again (was #20, now #21) ❌

Result: User sees post 81 twice, never sees post 80 ❌
```

```
SOLUTION 1: CURSOR-BASED PAGINATION (prevents duplicates)
─────────────────────────────────────────────────────────────────

// Backend returns cursor (pointer to last item)
// Frontend uses cursor to get next batch

function Feed() {
  const [posts, setPosts] = useState([]);
  const [cursor, setCursor] = useState(null);  // ID of last post
  const [hasMore, setHasMore] = useState(true);
  const [isLoading, setIsLoading] = useState(false);

  const loadMore = async () => {
    if (isLoading || !hasMore) return;  // ← prevent duplicate requests

    setIsLoading(true);
    
    const url = cursor 
      ? `/api/posts?cursor=${cursor}&limit=20`
      : `/api/posts?limit=20`;
    
    const response = await fetch(url);
    const data = await response.json();
    
    setPosts(prev => [...prev, ...data.posts]);
    setCursor(data.nextCursor);  // ID of last post in this batch
    setHasMore(data.hasMore);    // false if no more posts
    setIsLoading(false);
  };

  useEffect(() => {
    loadMore();  // initial load
  }, []);

  const handleScroll = () => {
    const { scrollTop, scrollHeight, clientHeight } = document.documentElement;
    if (scrollTop + clientHeight >= scrollHeight - 100) {  // 100px threshold
      loadMore();
    }
  };

  useEffect(() => {
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, [isLoading, hasMore]);  // ← re-create listener when deps change

  return (
    <div>
      {posts.map(post => <PostCard key={post.id} post={post} />)}
      {isLoading && <Spinner />}
      {!hasMore && <div>No more posts</div>}
    </div>
  );
}

BACKEND (cursor pagination):
────────────────────────────────────────────────────────────────

// Express.js example
app.get('/api/posts', async (req, res) => {
  const { cursor, limit = 20 } = req.query;
  
  const query = cursor
    ? { createdAt: { $lt: cursor } }  // posts older than cursor
    : {};
  
  const posts = await Post.find(query)
    .sort({ createdAt: -1 })
    .limit(limit + 1);  // fetch one extra to check if more exist
  
  const hasMore = posts.length > limit;
  const postsToReturn = hasMore ? posts.slice(0, limit) : posts;
  const nextCursor = postsToReturn.length > 0 
    ? postsToReturn[postsToReturn.length - 1].createdAt 
    : null;
  
  res.json({
    posts: postsToReturn,
    nextCursor,
    hasMore
  });
});

HOW CURSOR PREVENTS DUPLICATES:
─────────────────────────────────────────────────────────────────

Request 1: GET /api/posts?limit=20
  Returns: posts with createdAt > (none)
  Result: 20 newest posts, cursor = createdAt of post #20

NEW POST ADDED (ID 101, createdAt = "2024-01-15T10:30:00Z")

Request 2: GET /api/posts?cursor=2024-01-15T10:00:00Z&limit=20
  Returns: posts with createdAt < "2024-01-15T10:00:00Z"
  Result: next 20 posts OLDER than previous batch ✅
          New post 101 NOT included (it's NEWER) ✅
          No duplicates, no skips ✅
```

```
SOLUTION 2: DEBOUNCE + LOADING FLAG (prevent spam)
─────────────────────────────────────────────────────────────────

import { useEffect, useState, useCallback } from 'react';
import { debounce } from 'lodash';

function Feed() {
  const [posts, setPosts] = useState([]);
  const [cursor, setCursor] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const loadMore = async () => {
    if (isLoading) return;  // ← already loading, skip
    
    setIsLoading(true);
    // ... fetch logic
    setIsLoading(false);
  };

  const handleScroll = useCallback(
    debounce(() => {
      const bottom = window.innerHeight + window.scrollY >= 
                     document.body.offsetHeight - 100;
      if (bottom) loadMore();
    }, 200),  // ← wait 200ms after last scroll event
    [isLoading, cursor]
  );

  useEffect(() => {
    window.addEventListener('scroll', handleScroll);
    return () => handleScroll.cancel();  // cancel pending debounce
  }, [handleScroll]);

  return <div>{/* ... */}</div>;
}

HOW DEBOUNCE HELPS:
─────────────────────────────────────────────────────────────────

User scrolls quickly:
  scroll event at 0ms   ← debounce timer starts
  scroll event at 10ms  ← timer reset
  scroll event at 20ms  ← timer reset
  scroll event at 30ms  ← timer reset
  (user stops scrolling)
  200ms later → handleScroll fires ONCE ✅

Without debounce:
  - 4 scroll events → 4 loadMore() calls
  - 4 simultaneous fetch requests ❌

With debounce:
  - 4 scroll events → 1 loadMore() call ✅
```

```
SOLUTION 3: INTERSECTION OBSERVER (better scroll detection)
─────────────────────────────────────────────────────────────────

// More performant than scroll event listener

import { useEffect, useRef, useState } from 'react';

function Feed() {
  const [posts, setPosts] = useState([]);
  const [cursor, setCursor] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const loaderRef = useRef(null);  // ref to "sentinel" element

  const loadMore = async () => {
    if (isLoading) return;
    setIsLoading(true);
    // ... fetch logic
    setIsLoading(false);
  };

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {  // sentinel visible
          loadMore();
        }
      },
      { threshold: 1.0 }  // trigger when fully visible
    );

    if (loaderRef.current) {
      observer.observe(loaderRef.current);
    }

    return () => observer.disconnect();
  }, [isLoading, cursor]);

  return (
    <div>
      {posts.map(post => <PostCard key={post.id} post={post} />)}
      <div ref={loaderRef}>  {/* ← sentinel element */}
        {isLoading && <Spinner />}
      </div>
    </div>
  );
}

WHY INTERSECTION OBSERVER IS BETTER:
─────────────────────────────────────────────────────────────────

Scroll event:
  - Fires 100+ times per second while scrolling
  - Need debouncing
  - Main thread work

IntersectionObserver:
  - Only fires when sentinel enters/leaves viewport
  - No debouncing needed
  - Off main thread (better performance) ✅
  - Recommended by React team
```

```
SOLUTION 4: REACT QUERY (handles everything)
─────────────────────────────────────────────────────────────────

import { useInfiniteQuery } from '@tanstack/react-query';

function Feed() {
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage
  } = useInfiniteQuery({
    queryKey: ['posts'],
    queryFn: async ({ pageParam = null }) => {
      const url = pageParam
        ? `/api/posts?cursor=${pageParam}`
        : `/api/posts`;
      const res = await fetch(url);
      return res.json();
    },
    getNextPageParam: (lastPage) => lastPage.nextCursor,
    // React Query automatically:
    // - Prevents duplicate requests
    // - Caches all pages
    // - Deduplicates simultaneous calls
    // - Handles loading states
  });

  const loaderRef = useRef();

  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage) {
        fetchNextPage();
      }
    });

    if (loaderRef.current) observer.observe(loaderRef.current);
    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  const posts = data?.pages.flatMap(page => page.posts) ?? [];

  return (
    <div>
      {posts.map(post => <PostCard key={post.id} post={post} />)}
      <div ref={loaderRef}>
        {isFetchingNextPage && <Spinner />}
        {!hasNextPage && <div>No more posts</div>}
      </div>
    </div>
  );
}

REACT QUERY BENEFITS:
─────────────────────────────────────────────────────────────────

1. AUTOMATIC CACHING
   - User scrolls down → loads pages 1, 2, 3
   - User scrolls up → pages 1, 2, 3 served from cache ✅
   - No refetch needed

2. STALE-WHILE-REVALIDATE
   - Shows cached data immediately
   - Refetches in background
   - Updates when new data arrives

3. DEDUPLICATION
   - Multiple fetchNextPage() calls at once
   - React Query deduplicates to 1 request ✅

4. ERROR HANDLING
   - Automatic retry on failure
   - Loading and error states built-in

5. FRESH DATA ON FOCUS
   - User switches tabs, comes back
   - React Query refetches page 1 (new posts)
   - Old pages stay cached
```

```
HANDLING NEW POSTS (prepend to feed):
─────────────────────────────────────────────────────────────────

// WebSocket receives new post notification

function Feed() {
  const [posts, setPosts] = useState([]);
  const [newPostsCount, setNewPostsCount] = useState(0);

  useEffect(() => {
    const socket = new WebSocket('ws://api.example.com');
    
    socket.onmessage = (event) => {
      const newPost = JSON.parse(event.data);
      setNewPostsCount(prev => prev + 1);
      // Don't auto-insert (jarring UX while user reads)
    };

    return () => socket.close();
  }, []);

  const loadNewPosts = async () => {
    const res = await fetch('/api/posts?limit=' + newPostsCount);
    const data = await res.json();
    setPosts(prev => [...data.posts, ...prev]);  // prepend
    setNewPostsCount(0);
  };

  return (
    <div>
      {newPostsCount > 0 && (
        <button onClick={loadNewPosts}>
          Load {newPostsCount} new post{newPostsCount > 1 ? 's' : ''}
        </button>
      )}
      {posts.map(post => <PostCard key={post.id} post={post} />)}
    </div>
  );
}

UX: User sees "Load 3 new posts" button → clicks → new posts appear ✅
    (Better than auto-inserting while user is reading) ✅
```

```
DEBUGGING CHECKLIST — "Infinite scroll shows duplicates/skips posts"
─────────────────────────────────────────────────────────────────

✅ Check pagination type
   - Using offset/limit? → Switch to cursor
   - Cursor based on ID or timestamp? → Timestamp safer

✅ Check for duplicate requests
   - Add isLoading guard
   - Debounce scroll handler
   - Or use IntersectionObserver

✅ Check race conditions
   - Fast scrolling → multiple pages in flight
   - Last request to finish wins (wrong order) ❌
   → Add request cancellation (AbortController)

✅ Check cache behavior
   - Scrolling up refetches? → Use React Query
   - Stale data shown? → Configure staleTime

✅ Check new posts handling
   - Auto-inserting while user reads? → Annoying UX
   - Use "Load N new posts" button instead

✅ Network tab (DevTools)
   - Multiple /api/posts requests firing?
   - Responses returning same data? → Duplicates
```

> "The mental model: offset pagination is like saying 'give me items 21-40' — but if items shift (new post added), you get the wrong slice. Cursor pagination says 'give me 20 items AFTER this specific post' — the anchor is stable, so you always get the right next batch. For scroll, IntersectionObserver is like placing a tripwire near the bottom; when it's visible, load more."

**INTERVIEW FOLLOW-UP QUESTIONS:**

**Q: "What if the user jumps to a specific page number?"**

> "Cursor pagination makes jumping hard because you need cursors for all intermediate pages. Options: (1) hybrid approach — use offset for jumps, cursor for infinite scroll; (2) show infinite scroll only, no page numbers (modern UX); (3) precompute cursors for every Nth page."

**Q: "How do you handle deleted posts in the feed?"**

> "WebSocket sends delete event → remove from local state. Or on next page load, backend skips deleted posts. Cursor stays valid (it's a timestamp), just fewer results in that range."

**Q: "What about bidirectional infinite scroll?"**

> "Track two cursors: `olderThan` and `newerThan`. Scroll down → fetch with `olderThan` cursor, scroll up → fetch with `newerThan` cursor. Chat apps use this. React Query supports it with `hasPreviousPage` and `fetchPreviousPage`."
