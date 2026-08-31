# How do you prevent duplicate subscriptions and memory leaks in useEffect?

> **Interview priority:** MUST KNOW

## Question

How do you prevent duplicate subscriptions and memory leaks in useEffect?

## Beginner Lens

Before memorizing the interview answer, notice the timeline: when the effect runs, what external connection it creates, when React cleans up, and what happens if cleanup is forgotten. The bug always appears after navigation or re-renders, not on the first mount.

## Detailed Explanation

**HOW TO SAY IT (spoken to interviewer):**

> "This is probably the most common React bug I've seen in production — components creating duplicate WebSocket connections, timers that keep firing after unmount, or event listeners piling up. The root cause is always the same: forgetting that effects run on EVERY render by default, not just mount. Let me show you with a real dashboard example..."

```
REAL APP: Stock Trading Dashboard — WebSocket Bug in Production
─────────────────────────────────────────────────────────────────

SCENARIO: User views Tesla stock (TSLA) → switches to Apple (AAPL) → back to Tesla

WITHOUT CLEANUP (buggy code):
────────────────────────────────────────────────────────────────

function StockPrice({ symbol }) {
  const [price, setPrice] = useState(null);

  useEffect(() => {
    const ws = new WebSocket(`wss://api.stocks.com/live/${symbol}`);
    ws.onmessage = (event) => {
      setPrice(event.data.price);
    };
  }, [symbol]);  // ← RUNS EVERY TIME symbol CHANGES

  return <div>{symbol}: ${price}</div>;
}

WHAT ACTUALLY HAPPENS:
─────────────────────────────────────────────────────────────────

t=0s:  User opens dashboard, symbol = "TSLA"
       ├─ Component mounts
       ├─ useEffect runs
       └─ WebSocket #1 created → connects to TSLA stream
          WS #1 → receives prices → updates UI ✅

t=5s:  User clicks Apple stock, symbol = "AAPL"
       ├─ Component re-renders (symbol changed)
       ├─ useEffect runs AGAIN (deps changed)
       └─ WebSocket #2 created → connects to AAPL stream
          WS #1 → STILL ALIVE, still receiving TSLA prices ❌
          WS #2 → receives AAPL prices → updates UI
          Result: UI shows AAPL, but WS #1 keeps calling setPrice
                  with stale TSLA data → race condition

t=10s: User clicks Tesla again, symbol = "TSLA"
       ├─ Component re-renders
       ├─ useEffect runs THIRD TIME
       └─ WebSocket #3 created → connects to TSLA stream
          WS #1 → still alive (TSLA) ❌
          WS #2 → still alive (AAPL) ❌
          WS #3 → alive (TSLA) ✅
          Result: THREE WebSockets open, all calling setPrice
                  Last one to receive data wins → UI flickers

MEMORY LEAK DIAGRAM:
─────────────────────────────────────────────────────────────────

Component Lifecycle:
  Mount → Render → Effect → User interaction → Re-render → Effect → ...

Without cleanup:
  ┌──────────────────────────────────────────────────────────────┐
  │  Mount (TSLA)                                                 │
  │    └─ WS #1 created ──────────────────────────► [NEVER CLOSED]│
  │                                                                │
  │  Re-render (AAPL)                                             │
  │    └─ WS #2 created ──────────────────────────► [NEVER CLOSED]│
  │                                                                │
  │  Re-render (TSLA)                                             │
  │    └─ WS #3 created ──────────────────────────► [NEVER CLOSED]│
  │                                                                │
  │  Unmount (user navigates away)                                │
  │    └─ Component destroyed                                     │
  │       BUT: WS #1, #2, #3 STILL ALIVE IN MEMORY ❌            │
  │       They keep receiving data, calling setPrice on          │
  │       destroyed component → "Can't update unmounted" warning │
  └──────────────────────────────────────────────────────────────┘
```

```
WITH CLEANUP (correct code):
────────────────────────────────────────────────────────────────

function StockPrice({ symbol }) {
  const [price, setPrice] = useState(null);

  useEffect(() => {
    const ws = new WebSocket(`wss://api.stocks.com/live/${symbol}`);
    ws.onmessage = (event) => {
      setPrice(event.data.price);
    };

    // CLEANUP FUNCTION — runs BEFORE the next effect and on unmount
    return () => {
      ws.close();  // ← close the old connection
    };
  }, [symbol]);

  return <div>{symbol}: ${price}</div>;
}

WHAT HAPPENS NOW:
─────────────────────────────────────────────────────────────────

t=0s:  Mount (TSLA)
       useEffect runs → WS #1 created ✅

t=5s:  Re-render (symbol changes to AAPL)
       ├─ React FIRST runs the cleanup function from previous effect
       │  └─ ws.close() called → WS #1 CLOSED ✅
       └─ Then React runs the NEW effect
          └─ WS #2 created for AAPL ✅

t=10s: Re-render (symbol changes to TSLA)
       ├─ Cleanup runs → WS #2 CLOSED ✅
       └─ WS #3 created for TSLA ✅

Unmount:
       └─ Cleanup runs → WS #3 CLOSED ✅

Result: ONLY ONE WebSocket open at a time, no leaks ✅
```

```
CLEANUP EXECUTION ORDER (critical to understand):
─────────────────────────────────────────────────────────────────

When deps change:
  Step 1: React runs CLEANUP from PREVIOUS effect
  Step 2: React runs NEW effect

When component unmounts:
  Step 1: React runs cleanup from LAST effect
  Step 2: Component destroyed

COMMON MISTAKE — cleanup timing confusion:
─────────────────────────────────────────────────────────────────

// WRONG assumption:
useEffect(() => {
  const ws = new WebSocket(url);
  return () => {
    ws.close();  // "This runs when component unmounts"
  };
}, [url]);
// ❌ WRONG — it ALSO runs before the next effect, not just unmount

// CORRECT understanding:
// Cleanup runs:
//   1. Before re-running effect (when deps change)
//   2. When component unmounts
//   (Two different times, same cleanup code)
```

```
MORE REAL EXAMPLES — Common Cleanup Scenarios:
─────────────────────────────────────────────────────────────────

1. TIMER / INTERVAL
────────────────────
// BAD — timer keeps running after unmount
useEffect(() => {
  setInterval(() => {
    console.log('Tick');  // fires forever, even after unmount
  }, 1000);
}, []);

// GOOD — clear the timer
useEffect(() => {
  const timerId = setInterval(() => {
    console.log('Tick');
  }, 1000);
  return () => clearInterval(timerId);  // ← cleanup
}, []);


2. EVENT LISTENER
─────────────────
// BAD — duplicate listeners pile up
useEffect(() => {
  window.addEventListener('resize', handleResize);
  // Every re-render adds ANOTHER listener
}, []);

// GOOD — remove the old listener
useEffect(() => {
  window.addEventListener('resize', handleResize);
  return () => {
    window.removeEventListener('resize', handleResize);  // ← cleanup
  };
}, []);


3. FETCH / PROMISE
──────────────────
// BAD — old fetch result overwrites new one (race condition)
useEffect(() => {
  fetch(`/api/user/${userId}`)
    .then(r => r.json())
    .then(data => setUser(data));  // might be stale userId
}, [userId]);

// GOOD — cancel stale fetches
useEffect(() => {
  let cancelled = false;  // ← flag to ignore stale results

  fetch(`/api/user/${userId}`)
    .then(r => r.json())
    .then(data => {
      if (!cancelled) {  // only update if still current
        setUser(data);
      }
    });

  return () => {
    cancelled = true;  // ← mark this fetch as stale
  };
}, [userId]);

// BETTER — use AbortController (modern approach)
useEffect(() => {
  const controller = new AbortController();

  fetch(`/api/user/${userId}`, { signal: controller.signal })
    .then(r => r.json())
    .then(data => setUser(data))
    .catch(err => {
      if (err.name !== 'AbortError') {
        console.error(err);  // real error, not cancellation
      }
    });

  return () => {
    controller.abort();  // ← cancel the fetch
  };
}, [userId]);


4. SUBSCRIPTION (e.g., Firebase, Pusher)
─────────────────────────────────────────
// BAD
useEffect(() => {
  const unsubscribe = firestore
    .collection('messages')
    .onSnapshot(snapshot => {
      setMessages(snapshot.docs.map(d => d.data()));
    });
  // unsubscribe function never called → keeps listening forever
}, []);

// GOOD
useEffect(() => {
  const unsubscribe = firestore
    .collection('messages')
    .onSnapshot(snapshot => {
      setMessages(snapshot.docs.map(d => d.data()));
    });

  return unsubscribe;  // ← Firebase returns the cleanup function
}, []);
```

```
EMPTY DEPS ARRAY [] — SPECIAL CASE:
─────────────────────────────────────────────────────────────────

useEffect(() => {
  // runs ONCE on mount
  return () => {
    // cleanup runs ONCE on unmount (NOT on re-render)
  };
}, []);  // ← empty deps = effect never re-runs

USE CASE: Global setup/teardown
  - Add document-level event listener
  - Start global polling
  - Connect to analytics service
  - Initialize third-party SDK

DANGER: Stale closure problem (covered separately)
```

```
DEBUGGING CHECKLIST — "My component has memory leaks"
─────────────────────────────────────────────────────────────────

✅ Does your useEffect create something external?
   (WebSocket, timer, listener, subscription, fetch)
   → YES? You need cleanup.

✅ Does your cleanup function actually run?
   console.log('cleanup') inside return () => {...}
   → Should log BEFORE next effect and on unmount

✅ Are you capturing the right reference?
   const ws = new WebSocket(...);
   return () => ws.close();  ← must close the SAME ws instance

✅ Is your cleanup conditional?
   return () => {
     if (shouldCleanup) ws.close();  ← WRONG, cleanup must be unconditional
   };

✅ Are you creating closures over stale state?
   (Use refs or functional updates)
```

> "The mental model I use: every useEffect creates a 'mini lifecycle' — setup on run, cleanup before next run. If you create something, you must destroy it. If setup returns a function, React calls it as cleanup. That's the contract."

**INTERVIEW FOLLOW-UP QUESTIONS:**

**Q: "What happens if cleanup returns a value?"**

> "React ignores it. Cleanup must be a void function. Returning a promise doesn't make cleanup async — React won't wait for it. If you need async cleanup, use a flag to prevent stale updates instead."

**Q: "Can cleanup read current state?"**

> "Yes, but it reads the state from WHEN THE EFFECT RAN, not current state. It's a closure over that render's snapshot. If you need current values in cleanup, use a ref."

**Q: "When does cleanup run in React 18 StrictMode?"**

> "In development, StrictMode mounts → unmounts → remounts components to surface missing cleanup. So you see: effect → cleanup → effect again. This is ONLY in dev, not production. It's a feature, not a bug — it helps you find missing cleanup early."
