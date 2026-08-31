# How do you prevent race conditions in data fetching?

> **Interview priority:** MUST KNOW

## Question

How do you prevent race conditions in data fetching?

## Beginner Lens

Watch the timeline: user makes request A, then quickly makes request B. Request A is slow, request B is fast. Request B finishes first (correct data displayed), then request A finishes and overwrites it with stale data. The fix always involves either cancelling old requests or ignoring stale responses.

## Detailed Explanation

**HOW TO SAY IT (spoken to interviewer):**

> "Race conditions in data fetching are sneaky because they only happen under specific timing — fast user interactions combined with slow network. I've seen this cause real bugs in production search, autocomplete, and detail pages. The core issue is that HTTP requests don't finish in the order you send them. Let me show the exact failure scenario..."

```
REAL APP: E-Commerce Search — Race Condition Bug
─────────────────────────────────────────────────────────────────

USER TYPES: "lap" → "lapt" → "laptop"

NAIVE CODE (has race condition):
────────────────────────────────────────────────────────────────

function SearchResults() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);

  useEffect(() => {
    if (!query) return;
    
    fetch(`/api/search?q=${query}`)
      .then(r => r.json())
      .then(data => setResults(data));  // ← BUG HERE
  }, [query]);

  return (
    <div>
      <input 
        value={query} 
        onChange={e => setQuery(e.target.value)} 
      />
      <Results items={results} />
    </div>
  );
}

THE BUG — TIMELINE:
─────────────────────────────────────────────────────────────────

t=0ms:    User types "lap"
          ├─ setQuery("lap")
          └─ useEffect fires
             └─ fetch("/api/search?q=lap") sent → Request A
                Network latency: 300ms (slow server)

t=100ms:  User types "t" (now "lapt")
          ├─ setQuery("lapt")
          └─ useEffect fires
             └─ fetch("/api/search?q=lapt") sent → Request B
                Network latency: 50ms (cache hit, fast)

t=150ms:  Request B finishes FIRST (lapt results)
          └─ setResults([{id:1, name:"Laptop Stand"}, ...])
             UI shows "Laptop Stand" ✅ CORRECT

t=300ms:  Request A finishes LATER (lap results)
          └─ setResults([{id:99, name:"Lap Desk"}, ...])
             UI shows "Lap Desk" ❌ WRONG
             User searched for "lapt" but sees "lap" results

DIAGRAM:
─────────────────────────────────────────────────────────────────

User input timeline:
  "lap"    "lapt"   "laptop"
  ─┬────────┬────────┬────────────────────────► time
   │        │        │
   ▼        ▼        ▼
Request A  Request B Request C (sent in order)
   │        │        │
   │        │        │
   └────────┼────────┼──► Network (variable latency)
            │        │
            ▼        │
       Request B ────┘ finishes first (50ms)
       UI shows correct result ✅
            │
            ▼
       Request A finishes last (300ms)
       UI OVERWRITES with stale result ❌

The last setState wins, NOT the most recent request.
```

```
SOLUTION 1: CANCEL OLD REQUESTS (AbortController)
─────────────────────────────────────────────────────────────────

function SearchResults() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);

  useEffect(() => {
    if (!query) return;

    const controller = new AbortController();  // ← create controller

    fetch(`/api/search?q=${query}`, {
      signal: controller.signal  // ← link fetch to controller
    })
      .then(r => r.json())
      .then(data => setResults(data))
      .catch(err => {
        if (err.name === 'AbortError') {
          console.log('Request cancelled');  // expected
        } else {
          console.error('Fetch failed:', err);  // real error
        }
      });

    return () => {
      controller.abort();  // ← cancel on cleanup
    };
  }, [query]);

  return (
    <div>
      <input value={query} onChange={e => setQuery(e.target.value)} />
      <Results items={results} />
    </div>
  );
}

HOW IT WORKS:
─────────────────────────────────────────────────────────────────

t=0ms:    query = "lap"
          ├─ useEffect runs
          ├─ controller #1 created
          └─ fetch sent with signal #1

t=100ms:  query = "lapt" (query changed)
          ├─ CLEANUP RUNS FIRST
          │  └─ controller #1.abort() called
          │     └─ Request A cancelled ✅
          │        (browser stops waiting for response)
          ├─ NEW useEffect runs
          ├─ controller #2 created
          └─ fetch sent with signal #2

t=150ms:  Request B finishes
          └─ setResults([...]) ✅
             UI shows "lapt" results ✅

t=300ms:  Request A response arrives (even though cancelled)
          └─ Promise rejects with AbortError
          └─ catch block ignores it
          └─ setResults NEVER CALLED ✅

Result: UI always shows the LATEST query results ✅
```

```
SOLUTION 2: IGNORE STALE RESPONSES (boolean flag)
─────────────────────────────────────────────────────────────────

// Use this when you CAN'T cancel (e.g., library doesn't support abort)

function SearchResults() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);

  useEffect(() => {
    if (!query) return;

    let isCurrentRequest = true;  // ← flag for this specific render

    fetch(`/api/search?q=${query}`)
      .then(r => r.json())
      .then(data => {
        if (isCurrentRequest) {  // ← only update if still valid
          setResults(data);
        } else {
          console.log('Ignoring stale response for:', query);
        }
      });

    return () => {
      isCurrentRequest = false;  // ← mark this request as stale
    };
  }, [query]);

  return (
    <div>
      <input value={query} onChange={e => setQuery(e.target.value)} />
      <Results items={results} />
    </div>
  );
}

HOW IT WORKS:
─────────────────────────────────────────────────────────────────

t=0ms:    query = "lap"
          ├─ useEffect runs
          ├─ isCurrentRequest #1 = true
          └─ fetch sent

t=100ms:  query = "lapt"
          ├─ CLEANUP RUNS
          │  └─ isCurrentRequest #1 = false  ← marks old request stale
          ├─ NEW useEffect runs
          ├─ isCurrentRequest #2 = true
          └─ fetch sent

t=150ms:  Request B finishes (lapt)
          ├─ isCurrentRequest #2 === true ✅
          └─ setResults([...]) ✅

t=300ms:  Request A finishes (lap)
          ├─ isCurrentRequest #1 === false ❌
          └─ setResults NOT CALLED ✅
             Stale response ignored

Result: Only the latest response updates state ✅

Note: Request A still completes (wastes bandwidth) but we ignore it.
      AbortController is better — it actually cancels the network request.
```

```
SOLUTION 3: DEBOUNCE USER INPUT (delay triggering)
─────────────────────────────────────────────────────────────────

// Wait for user to stop typing before searching

import { useState, useEffect } from 'react';
import { useDebouncedValue } from './hooks';  // custom hook

function SearchResults() {
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebouncedValue(query, 300);  // 300ms delay
  const [results, setResults] = useState([]);

  useEffect(() => {
    if (!debouncedQuery) return;

    const controller = new AbortController();

    fetch(`/api/search?q=${debouncedQuery}`, {
      signal: controller.signal
    })
      .then(r => r.json())
      .then(data => setResults(data));

    return () => controller.abort();
  }, [debouncedQuery]);  // ← triggers only after user stops typing

  return (
    <div>
      <input value={query} onChange={e => setQuery(e.target.value)} />
      <Results items={results} />
    </div>
  );
}

// Custom debounce hook:
function useDebouncedValue(value, delay) {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(timer);  // ← cancel old timer
  }, [value, delay]);

  return debouncedValue;
}

HOW IT WORKS:
─────────────────────────────────────────────────────────────────

t=0ms:    User types "l"
          ├─ query = "l"
          └─ Timer started: fire in 300ms

t=50ms:   User types "a" (now "la")
          ├─ query = "la"
          ├─ CLEANUP runs → previous timer cancelled
          └─ New timer started: fire in 300ms

t=100ms:  User types "p" (now "lap")
          ├─ query = "lap"
          ├─ Previous timer cancelled
          └─ New timer started: fire in 300ms

t=400ms:  User STOPS typing (300ms elapsed)
          └─ Timer fires
             └─ debouncedQuery = "lap"
                └─ useEffect runs
                   └─ fetch sent ONCE ✅

Result: Only ONE request sent instead of three ✅
        Reduces server load and race condition opportunities
```

```
SOLUTION 4: USE REACT QUERY (library handles it)
─────────────────────────────────────────────────────────────────

import { useQuery } from '@tanstack/react-query';

function SearchResults() {
  const [query, setQuery] = useState('');

  const { data: results, isLoading } = useQuery({
    queryKey: ['search', query],  // ← cache key
    queryFn: () => fetch(`/api/search?q=${query}`).then(r => r.json()),
    enabled: query.length > 0,
    // React Query automatically:
    // - Cancels previous request when query changes
    // - Deduplicates simultaneous requests
    // - Caches results
    // - Handles loading/error states
  });

  return (
    <div>
      <input value={query} onChange={e => setQuery(e.target.value)} />
      {isLoading && <Spinner />}
      {results && <Results items={results} />}
    </div>
  );
}

WHY REACT QUERY SOLVES IT:
─────────────────────────────────────────────────────────────────

1. Automatic cancellation: Each new query cancels the previous one
2. Deduplication: If you search "laptop" twice quickly, only one request
3. Cache: Searching "laptop" again shows cached result instantly
4. Race-safe: queryKey change = previous query result ignored
5. Less code: No manual useEffect, cleanup, or state management
```

```
COMPARISON TABLE:
─────────────────────────────────────────────────────────────────

Method              Pros                        Cons
──────────────────  ──────────────────────────  ─────────────────
AbortController     Actually cancels network    Browser support
                    Saves bandwidth             (IE11 no support)
                    Clean solution

Boolean flag        Works with any library      Wastes bandwidth
                    Good browser support        (request completes)
                    Simple to understand

Debounce            Reduces server load         Adds input delay
                    Fewer race conditions       UX feels sluggish
                    Good for autocomplete       (300ms lag)

React Query         Handles everything          Dependency added
                    + caching, dedup, errors    Learning curve
                    Production-ready            Overkill for simple
                                               cases

RECOMMENDATION: AbortController + debounce for autocomplete
                React Query for complex data fetching
```

```
REAL PRODUCTION BUG — USER DETAIL PAGE:
─────────────────────────────────────────────────────────────────

function UserProfile({ userId }) {
  const [user, setUser] = useState(null);

  useEffect(() => {
    fetch(`/api/users/${userId}`)
      .then(r => r.json())
      .then(data => setUser(data));
  }, [userId]);

  return <div>{user?.name}</div>;
}

BUG: User clicks through users quickly
     1. Click user 101 → fetch starts (200ms)
     2. Click user 102 → fetch starts (50ms)
     3. User 102 loads (shows correct name) ✅
     4. User 101 loads LATE (overwrites with wrong user) ❌
     
     URL shows /users/102 but page shows user 101's data!

FIX: Add AbortController cleanup ✅
```

```
DEBUGGING CHECKLIST — "My data is wrong after fast clicks"
─────────────────────────────────────────────────────────────────

✅ Does the component fetch based on a prop/param?
   (userId, searchQuery, filter, etc.)
   → YES? Race condition likely.

✅ Can the user change that prop quickly?
   (click through list, type fast, toggle filters)
   → YES? You MUST handle cancellation.

✅ Do you have cleanup in your useEffect?
   return () => controller.abort();
   → NO? Add it.

✅ Are you using React Query or SWR?
   → They handle this automatically.

✅ Is your API slow or variable latency?
   → Race conditions more likely, debounce helps.
```

> "The mental model: HTTP requests are fire-and-forget. You send 3 requests, they can finish in ANY order. If you don't cancel or ignore stale responses, the last one to finish wins — not the most recent one you wanted. AbortController is your friend."

**INTERVIEW FOLLOW-UP QUESTIONS:**

**Q: "What if I need the results of multiple requests?"**

> "Use Promise.all() and a single AbortController. When cleanup runs, abort all pending requests together. Or use React Query which has built-in parallel query support."

**Q: "Does AbortController work with axios?"**

> "Yes, but with axios-specific syntax: axios.get(url, { signal: controller.signal }). Native fetch and axios both support it, but old libraries might not."

**Q: "What about WebSockets — can you abort those?"**

> "WebSocket.close() in cleanup. Same pattern — cleanup function closes the connection before opening a new one."
