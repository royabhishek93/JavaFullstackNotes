# Real-Time Patterns in React — 15-YOE Architect Interview Prep

> Target: Senior / Staff / Principal Front-End / Full-Stack Architect interviews
> Covers: WebSocket, SSE, Long Polling, CRDT/OT, Presence, Optimistic UI, Offline-First

---

## 1. BIG PICTURE — Architecture Options

```
REAL-TIME DATA DELIVERY: CHOOSE YOUR WEAPON
═══════════════════════════════════════════════════════════════════════════════

  CLIENT                              SERVER
  ──────                              ──────

  ┌───────────────┐                   ┌──────────────────────────────────────┐
  │  React App    │                   │  Backend Service                     │
  └───────┬───────┘                   └───────────────┬──────────────────────┘
          │                                           │
          ▼                                           │
  ┌───────────────────────────────────────────────────┼───────────────┐
  │  OPTION A: SHORT POLLING  (React Query / SWR)     │               │
  │                                                   │               │
  │  Client ──GET /data──────────────────────────────►│               │
  │  Client ◄──200 + payload──────────────────────────│               │
  │  wait 30s...                                      │               │
  │  Client ──GET /data──────────────────────────────►│               │
  │                                                   │               │
  │  USE WHEN: freshness >30s OK, simple, REST cache  │               │
  └───────────────────────────────────────────────────┼───────────────┘
          │                                           │
  ┌───────────────────────────────────────────────────┼───────────────┐
  │  OPTION B: LONG POLLING                           │               │
  │                                                   │               │
  │  Client ──GET /data──────────────────────────────►│ hold...       │
  │  (server holds request until data available)      │ hold...       │
  │  Client ◄──200 + payload──────────────────────────│ fire!         │
  │  Client ──GET /data──────────────────────────────►│ hold...       │
  │                                                   │               │
  │  USE WHEN: WebSocket unavailable (proxies/corp),  │               │
  │  infrequent events, legacy infra                  │               │
  └───────────────────────────────────────────────────┼───────────────┘
          │                                           │
  ┌───────────────────────────────────────────────────┼───────────────┐
  │  OPTION C: SSE — Server-Sent Events               │               │
  │                                                   │               │
  │  Client ──GET /stream (Accept: text/event-stream)►│               │
  │  Client ◄══ data: {...} ══════════════════════════│ push          │
  │  Client ◄══ data: {...} ══════════════════════════│ push          │
  │  (single long-lived HTTP response, server pushes) │               │
  │                                                   │               │
  │  STRENGTHS:                                       │               │
  │  • Plain HTTP — works through all proxies/CDN     │               │
  │  • HTTP/2: multiplex 100s of SSE streams per conn │               │
  │  • Auto-reconnect built into browser EventSource  │               │
  │  • Ordered, text-based, simple to debug           │               │
  │                                                   │               │
  │  USE WHEN: server→client only (notifications,     │               │
  │  live feeds, AI token streaming, dashboards)      │               │
  └───────────────────────────────────────────────────┼───────────────┘
          │                                           │
  ┌───────────────────────────────────────────────────┼───────────────┐
  │  OPTION D: WebSocket (WS / WSS)                   │               │
  │                                                   │               │
  │  Client ──HTTP Upgrade ──────────────────────────►│               │
  │  Client ◄──101 Switching Protocols────────────────│               │
  │  ◄═══════════════════ FULL DUPLEX ════════════════►               │
  │  Client ══ msg ══════════════════════════════════►│               │
  │  Client ◄══ msg ══════════════════════════════════│               │
  │                                                   │               │
  │  USE WHEN: bidirectional, low-latency, chat,      │               │
  │  collaborative editing, gaming, trading UIs        │               │
  └───────────────────────────────────────────────────┼───────────────┘
          │                                           │
  ┌───────────────────────────────────────────────────┼───────────────┐
  │  OPTION E: CRDT-BACKED SYNC (Yjs / Automerge)    │               │
  │                                                   │               │
  │  Peer A ──── WS / WebRTC ────────────────────────►│ Relay         │
  │  Peer B ◄─── WS / WebRTC ─────────────────────────│               │
  │                                                   │               │
  │  Each peer holds full CRDT document               │               │
  │  Merges are always convergent (no conflicts)      │               │
  │                                                   │               │
  │  USE WHEN: Google-Docs-style collab, offline-ok   │               │
  └───────────────────────────────────────────────────┘───────────────┘


CONNECTION LIFECYCLE — WebSocket in React
═══════════════════════════════════════════════════════════════════════════════

  App Boot
     │
     ▼
  ┌──────────────────────────────┐
  │  WS Singleton Created        │  ← module-level or Context/Zustand
  │  new WebSocket(url)          │    NOT inside component render
  └──────────┬───────────────────┘
             │
             ▼
  ┌──────────────────────────────┐
  │  CONNECTING (readyState: 0)  │
  └──────────┬───────────────────┘
             │  onopen
             ▼
  ┌──────────────────────────────┐
  │  OPEN (readyState: 1)        │◄─── send/receive messages here
  └──────────┬───────────────────┘
             │  onerror / onclose
             ▼
  ┌──────────────────────────────┐
  │  CLOSING / CLOSED (2 / 3)    │
  └──────────┬───────────────────┘
             │
             ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │  Reconnect with Exponential Backoff + Jitter                     │
  │                                                                  │
  │  attempt  delay = min(cap, base * 2^attempt) + random(0..1000ms) │
  │     1     min(30s, 1s * 2^1) + jitter  ≈  2–3s                  │
  │     2     min(30s, 1s * 2^2) + jitter  ≈  4–5s                  │
  │     3     min(30s, 1s * 2^3) + jitter  ≈  8–9s                  │
  │     6+    capped at 30s + jitter                                 │
  │                                                                  │
  │  Jitter prevents thundering herd when server restarts            │
  └──────────────────────────────────────────────────────────────────┘


DECISION MATRIX
═══════════════════════════════════════════════════════════════════════════════

  Need               │ Polling  │ Long Poll │  SSE  │  WS   │ CRDT
  ───────────────────┼──────────┼───────────┼───────┼───────┼──────
  Freshness >30s     │   ✓      │    ✓      │   ✓   │   ✓   │  ✓
  Server→Client only │   ✓      │    ✓      │  ✓✓   │   ✓   │  ✓
  Bidirectional      │   ✗      │    ✗      │   ✗   │  ✓✓   │  ✓
  Works thru proxies │  ✓✓      │   ✓✓      │  ✓✓   │  ~    │  ~
  HTTP/2 compat.     │  ✓✓      │   ✓✓      │  ✓✓   │  ✗    │  ✗
  Collaborative edit │   ✗      │    ✗      │   ✗   │   ~   │  ✓✓
  Offline-capable    │   ✗      │    ✗      │   ✗   │   ✗   │  ✓✓
  Simple infra       │  ✓✓      │    ✓      │   ✓   │   ~   │  ✗
```

---

## 2. CONVERSATIONAL INTERVIEW SCRIPT — 15-YOE Architect Voice

---

**Interviewer:** Walk me through how you'd design a real-time notification system for a SaaS dashboard with 50k concurrent users.

**You (architect voice):**

"First thing I'd ask is: what's the communication direction and acceptable latency? Notifications are almost always server-to-client — a user doesn't push notifications back to the server. That narrows the solution space immediately toward SSE over WebSocket.

Here's my reasoning: SSE is plain HTTP. It multiplexes beautifully over HTTP/2 — one TCP connection can carry hundreds of SSE streams, which is a significant infra win at 50k users versus maintaining 50k WebSocket upgrade connections. SSE has automatic reconnect baked into the browser's EventSource API, and every CDN and corporate proxy understands it because it's just a long-lived HTTP response.

WebSocket becomes the right tool when the client also pushes high-frequency data: think collaborative text editing, live cursors, trading terminals. For notifications, SSE is the simpler, more scalable choice.

On the React side, I'd expose this through a custom hook — useNotificationStream — that wraps EventSource, handles the reconnect states visually ('connecting', 'live', 'reconnecting'), and integrates with React Query's queryClient.invalidateQueries to trigger data refreshes on certain event types. The hook cleans up the EventSource on component unmount but the actual subscription logic lives in a module-level manager so a page navigation doesn't close and reopen the stream unnecessarily.

At 50k users I'd also think about connection load on the server: fan-out via Redis Pub/Sub or a message broker like Kafka, with SSE workers that hold open connections. Horizontal scaling with sticky sessions or stateless fan-out both work."

---

**Interviewer:** And for a Google Docs-style collaborative editor?

**You:**

"Now the answer flips. You need bidirectional, low-latency, and — critically — offline-capable merge semantics. That's a CRDT problem.

I'd reach for Yjs in production. It's battle-tested, the bundle overhead is ~40KB gzipped which is acceptable, and it has bindings for ProseMirror, TipTap, Quill, and Monaco. Yjs documents are CRDTs — Conflict-free Replicated Data Types — meaning two users can edit offline and when they reconnect, their changes always merge to a consistent state with no server-side conflict resolution logic.

The transport layer becomes almost secondary: Yjs works over WebSocket (y-websocket), WebRTC peer-to-peer (y-webrtc), or even HTTP with y-indexeddb for local persistence.

What I'd caution architects about is reinventing this: Operational Transforms — the OT algorithm that Google Docs uses — are notoriously hard to implement correctly. The transformation function must satisfy commutativity and associativity properties. Every off-by-one is a bug that corrupts documents. CRDTs sidestep that entirely through structure — the data type itself guarantees convergence. For any new project I'd default to Yjs/CRDT unless there's a specific reason to go OT."

---

**Interviewer:** How do you handle the connection state UI — those 'connecting' / 'offline' banners?

**You:**

"I treat connection state as first-class application state. I've seen too many apps where the WebSocket silently fails and the user thinks they're seeing live data when they're not — that's a trust killer.

My pattern: a useConnectionStatus hook that returns an enum — 'connecting' | 'connected' | 'reconnecting' | 'offline' — derived from the WebSocket readyState plus the browser's navigator.onLine. This state lives in a small Zustand slice or React context.

A global ConnectionBanner component subscribes to that state and renders nothing when 'connected', a subtle yellow bar for 'reconnecting' with a retry countdown, and a red bar for 'offline' with a manual retry button. The banner is mounted once at the app root, not inside each feature component.

One nuance: 'reconnecting' should only show after the first reconnect attempt fails, not immediately on the first connection attempt — you don't want the banner to flash on every page load."

---

## 3. SCENARIO Q&As — PRODUCTION CONTEXT

---

### Scenario 1: Chat Application — Connection Architecture

**Q:** You're building a real-time chat feature. A junior engineer puts `new WebSocket(url)` inside a React component. What's wrong and how do you fix it?

**A:**

Every component mount creates a new WebSocket connection. In a typical navigation pattern — user opens chat, goes to settings, comes back — you get 3 connections, with the old ones potentially leaking if cleanup isn't careful. Even with useEffect cleanup, you're creating unnecessary churn: connection setup, TLS handshake, authentication handshake — all repeated on every mount.

The fix depends on scope:

- **App-wide chat**: Module-level singleton. A `wsManager.ts` file exports a single WebSocket instance with reconnect logic. Components call `wsManager.subscribe(handler)` and `wsManager.unsubscribe(handler)`. The WebSocket itself is never created inside React's lifecycle.
- **Feature-scoped**: React Context with a Provider mounted high in the tree. The Context holds the connection and exposes a `useWebSocket` hook. Consumers subscribe to messages but do not own the connection.
- **State-manager approach**: Zustand store that holds the ws instance and dispatch functions. Middleware handles reconnect logic outside React.

What you must never do: close the shared connection when a consumer component unmounts. That's the useEffect cleanup trap — cleaning up the subscription is correct, cleaning up the shared socket is wrong.

---

### Scenario 2: React Query + WebSocket Integration

**Q:** Your app uses React Query for data fetching. How do you integrate real-time WebSocket updates without refetching everything?

**A:**

Two strategies depending on the update type:

**Strategy A — Invalidation (simpler, sufficient for most cases):**
When a WebSocket message arrives indicating a resource changed, call `queryClient.invalidateQueries({ queryKey: ['orders'] })`. React Query re-fetches in the background and updates the UI. This is eventually consistent — there's a brief window where the UI shows stale data.

**Strategy B — Direct cache update (lower latency):**
Parse the WebSocket message as a full or partial entity, then call `queryClient.setQueryData(['order', id], newData)`. The UI updates instantly without a network round-trip. This is essentially optimistic UI backed by server push rather than speculative local mutation.

For cursor/typing indicators (ephemeral state), skip React Query entirely — use local React state or Zustand. React Query's cache is for server state; presence data isn't "server state" in the traditional sense.

On reconnect: in the WebSocket's `onopen` handler, invalidate all stale queries with `queryClient.invalidateQueries()`. This ensures the UI catches up on any changes that arrived while disconnected.

---

### Scenario 3: SSE for AI Token Streaming

**Q:** You're implementing a ChatGPT-style streaming response in a Next.js app. How do you approach this?

**A:**

This is a textbook SSE use case. The server streams LLM tokens as they're generated; the client appends each token to the display. Direction is server→client only, so WebSocket would be over-engineering.

Server side (Next.js App Router route handler):
```typescript
// app/api/chat/route.ts
export async function POST(req: Request) {
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      for await (const chunk of llmStream) {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ token: chunk })}\n\n`));
      }
      controller.close();
    },
  });
  return new Response(stream, {
    headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache' },
  });
}
```

Client side: use the `EventSource` API or the `fetch` streaming approach with `response.body.getReader()`. EventSource doesn't support POST with body, so for chat (which needs to send the message) I use fetch with streaming read:

```typescript
const response = await fetch('/api/chat', { method: 'POST', body: JSON.stringify({ message }) });
const reader = response.body!.getReader();
// read chunks and parse SSE format
```

The React hook maintains a `content` string in state, appending each token. On error or abort, it cancels the reader. A ref holds the AbortController so the user can cancel mid-stream.

---

### Scenario 4: Presence System — Who's Online

**Q:** Design a "who's online" presence system with live cursor positions for a collaborative tool. What are the real-time engineering challenges?

**A:**

There are two distinct data types here with very different update frequencies:

**Presence (online/offline):** Low frequency — updated on join, leave, heartbeat every 30s. Suitable for broadcasting via WebSocket, stored in Redis with TTL.

**Cursor positions:** High frequency — 10-60 updates/second per user. Broadcasting raw cursor events to all collaborators at this rate is a firehose problem.

Solutions:

1. **Throttle on the sender**: Throttle cursor position updates to 50ms minimum intervals before sending over WebSocket. The human eye can't perceive the difference at 20fps.

2. **Debounce idle detection**: If no cursor movement for 3s, stop broadcasting. Resume on next movement.

3. **Interpolation on receiver**: Don't render cursor at the exact received position. Interpolate smoothly between received positions using requestAnimationFrame. This makes 20fps cursor updates feel smooth.

4. **Scope to room**: Cursor updates are scoped to a document/room ID. A user not viewing that document doesn't receive those events.

In React: cursor data lives in a ref (not state) to avoid triggering re-renders on every movement. A custom `useCursors` hook subscribes to cursor WebSocket events and updates the ref. A canvas or overlay layer reads from the ref on each animation frame.

---

### Scenario 5: Optimistic UI for Real-Time

**Q:** User sends a chat message. You update the UI instantly before the server confirms. The server rejects the message. How do you handle the rollback?

**A:**

The pattern is: assign a client-generated `tempId` to the optimistic message, render it with a 'sending' visual state, and reconcile once the server responds.

```typescript
// Pseudocode for the pattern
const sendMessage = (text: string) => {
  const tempId = crypto.randomUUID();
  // Optimistically add to local state
  addMessage({ id: tempId, text, status: 'sending', tempId });
  
  ws.send(JSON.stringify({ type: 'SEND_MESSAGE', tempId, text }));
};

// On server ack
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.type === 'MESSAGE_CONFIRMED') {
    // Replace temp message with confirmed server message
    replaceMessage(msg.tempId, { ...msg.serverMessage, status: 'sent' });
  } else if (msg.type === 'MESSAGE_FAILED') {
    // Mark as failed, show retry option
    updateMessage(msg.tempId, { status: 'failed', error: msg.reason });
  }
};
```

Key decisions:

- **Timeout-based rollback**: If no server ack within 10s, treat as failure. Don't leave 'sending' messages in limbo forever.
- **Conflict on update (not insert)**: If two users update the same field, the "last write wins" from the server may silently discard one user's change. Proper conflict resolution requires either OT, CRDT, or at minimum showing a conflict UI.
- **React Query**: `useMutation` with `onMutate` / `onError` / `onSettled` hooks handles this pattern cleanly for REST. The `onMutate` does the optimistic update; `onError` rolls it back via the context returned from `onMutate`.

---

### Scenario 6: Long Polling — When and Why

**Q:** A client's environment blocks WebSocket upgrades (corporate proxy). SSE also fails. What's your fallback?

**A:**

Long polling is the universal fallback that works everywhere because it's just HTTP GET requests.

Implementation: client sends `GET /api/events?since=<lastEventId>`. Server holds the connection open until an event is available or a timeout (typically 30-60s) expires. Client immediately re-requests on response.

The React side:

```typescript
const longPoll = async (since: string, signal: AbortSignal) => {
  while (!signal.aborted) {
    try {
      const res = await fetch(`/api/events?since=${since}`, { signal });
      const data = await res.json();
      if (data.events.length > 0) {
        processEvents(data.events);
        since = data.lastEventId;
      }
    } catch (e) {
      if (signal.aborted) break;
      await sleep(2000); // back off on error
    }
  }
};
```

Cleanup: the AbortController's signal is passed to fetch, so navigating away cancels in-flight requests cleanly.

Long polling vs SSE: SSE is strictly better when it's available — lower overhead (no repeated request headers), ordered delivery with built-in reconnect. Long polling is the fallback for hostile network environments.

---

### Scenario 7: Offline-First Architecture

**Q:** Your mobile web app needs to work offline and sync when reconnected. How do you architect this?

**A:**

Offline-first requires three components: local persistence, background sync, and conflict resolution.

**Local persistence:** IndexedDB via Dexie.js or idb. The app reads from the local DB first. Mutations are written to local DB immediately (user sees instant feedback) and queued for sync.

**Background sync:** Service Worker with Background Sync API. The SW registers a sync tag when a mutation is queued. When connectivity returns (even if the tab is closed), the browser fires the sync event, the SW processes the queue.

**Conflict resolution strategy (choose one based on domain):**
- Last-write-wins with server timestamp: simplest, acceptable for most non-collaborative data
- Client-wins: use for UX-sensitive mutations (user explicitly made a choice)
- Server-wins: use for financial data where server is authoritative
- CRDT merge: use for text editing or any data where both changes must survive

In React: `useQuery` and `useMutation` from React Query integrate with the local DB as the cache layer. A `useSyncStatus` hook exposes whether the sync queue is empty or has pending items. The UI shows a "changes pending sync" indicator.

---

### Scenario 8: Connection State Indicators

**Q:** How do you implement reliable "offline" detection in a browser? Is `navigator.onLine` sufficient?

**A:**

`navigator.onLine` is notoriously unreliable. It returns `true` when you're connected to a local network even if that network has no internet access. In a corporate wifi with a captive portal, `navigator.onLine === true` but all fetches fail.

A production offline detection strategy:

1. **`navigator.onLine` as a fast path**: When it transitions to `false`, you know you're definitely offline. When it transitions to `true`, you might be online.

2. **Probe request to confirm**: On `online` event, send a small `HEAD` request to a reliable endpoint (your own health-check URL or a CDN-hosted asset). Only mark as 'online' if the probe succeeds.

3. **WebSocket heartbeat**: If you have a WebSocket connection, use ping/pong or application-level heartbeat messages. Missing 2-3 heartbeats = offline. WebSocket `onclose` firing = connection lost.

4. **Combine signals**: The `useConnectionStatus` hook aggregates these signals into a single state machine: `offline` (navigator.onLine false), `suspected-offline` (WS heartbeat missing but navigator.onLine true), `online` (probe + WS both healthy).

This prevents false positives (showing offline banner when the user is actually online) and false negatives (showing online when the connection is degraded).

---

## 4. ADVANCED SCENARIO Q&As

---

### Advanced 1: OT vs CRDT — Architect Deep Dive

**Q:** Your team is building a collaborative spreadsheet. A senior engineer suggests Operational Transforms because "Google uses it." Another suggests Yjs. How do you decide?

**A:**

The "Google uses OT" argument is historically accurate but practically misleading. Google built their OT implementation in 2006 before CRDTs were mature. It took years of engineering and has had documented correctness bugs. Rebuilding it from scratch in 2025 for a team that doesn't have distributed systems specialists is high-risk.

Here's the technical distinction:

**OT (Operational Transforms):**
- Operations are transformed relative to concurrent operations to preserve intent
- Requires a central server to serialize operations and ensure consistent transform order
- Transform function complexity grows with operation type count
- Hard to make peer-to-peer (every peer would need to agree on operation ordering)
- The Jupiter algorithm (Google Docs) requires a central authority

**CRDT:**
- Data structures designed so all concurrent operations commute — merge order doesn't matter
- Fully peer-to-peer capable
- No central transform server needed (though a relay helps with discovery)
- Yjs specifically uses a YATA (Yet Another Transformation Approach) algorithm optimized for text
- Offline-capable by design

**My decision framework:**
- Green field collaborative text/rich-text/code editor: Yjs. Bindings exist for every editor.
- Collaborative spreadsheet: Yjs has experimental spreadsheet support, but the data model is harder. Automerge 2.0 with its columnar storage might be better.
- Legacy system with existing OT server: don't migrate, too risky.
- Custom conflict resolution rules that CRDTs can't express: consider a custom CRDT or OT.

The main legitimate argument against CRDTs: bundle size (~40KB) matters for some use cases, and the mental model is unfamiliar to most engineers. Neither is a blocker for a product that needs real collaboration.

---

### Advanced 2: Scaling WebSocket at 100k Connections

**Q:** Your WebSocket server is falling over at 50k concurrent connections. How do you scale?

**A:**

This is an infrastructure problem as much as an application problem, but the front-end architect needs to understand the constraints to design correctly.

**Why WebSocket scaling is hard:** Each connection is stateful — the server must know which socket belongs to which user to fan out targeted messages. You can't just throw load balancers in front naively.

**Horizontal scaling approaches:**

1. **Sticky sessions (simplest):** Load balancer routes each client to the same WebSocket server based on user ID hash. That server owns the connection. Server-to-server fan-out via Redis Pub/Sub. Works but creates hot spots if some users are more active.

2. **Stateless relay architecture:** WebSocket servers are pure relays — they hold connections but don't process business logic. Publish events to a message broker (Kafka, NATS). Any server can pick up any event and fan out to its connected clients. Requires each server to know which users are connected to it (local in-memory map + Redis for global lookup).

3. **Connection offloading:** Use a dedicated WebSocket infrastructure service (Ably, Pusher, AWS API Gateway WebSocket) that handles connection scaling. Your backend publishes events to their API; they handle the fan-out. Adds cost but removes the scaling burden entirely.

**Front-end implications:** 
- The client should reconnect to any server, not assume connection affinity
- Include the user's auth token in the WebSocket upgrade request for stateless auth
- Don't send connection-specific state to the client — reconstruct state from server queries after reconnect

---

### Advanced 3: Message Queue on the Client

**Q:** Your WebSocket reconnects frequently on mobile. Messages sent during disconnection are lost. How do you handle this?

**A:**

Implement a client-side send queue with acknowledgment protocol:

Every outbound message gets a sequence number. The server acknowledges each message with its sequence number. Messages not acknowledged are re-sent after reconnect.

```typescript
class ReliableWebSocket {
  private sendQueue: Map<number, { payload: unknown; timestamp: number }> = new Map();
  private seq = 0;

  send(payload: unknown) {
    const id = ++this.seq;
    this.sendQueue.set(id, { payload, timestamp: Date.now() });
    if (this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ id, payload }));
    }
    // else: stays in queue until reconnect
  }

  private onReconnect() {
    // Replay unacknowledged messages in order
    for (const [id, { payload }] of this.sendQueue) {
      this.ws.send(JSON.stringify({ id, payload }));
    }
  }

  private onAck(id: number) {
    this.sendQueue.delete(id);
  }
}
```

Additional considerations:
- **Queue TTL**: Messages older than 60s should be dropped with an error callback — they're no longer relevant (chat message from a minute ago, stale cursor position)
- **Queue cap**: Limit queue size (e.g., 100 messages). If the queue fills, the connection is considered unhealthy.
- **Idempotency on server**: The server must deduplicate by sequence number since the client may re-send messages the server already processed but the ack was lost.

---

### Advanced 4: Testing Real-Time React Components

**Q:** How do you write reliable tests for a React component that subscribes to WebSocket updates?

**A:**

Testing real-time components requires abstracting the transport layer so tests don't need real WebSocket servers.

**Strategy 1 — Mock the hook:**
If the component consumes a `useWebSocket` hook, mock that hook in tests. Provide a mock that returns a controllable `lastMessage` and `readyState`. Tests call `act(() => mockSendMessage({ type: 'UPDATE', data: ... }))` and assert on rendered output.

**Strategy 2 — Mock the WebSocket class:**
```typescript
// test-utils/mockWebSocket.ts
class MockWebSocket {
  static instance: MockWebSocket;
  readyState = WebSocket.OPEN;
  onmessage: ((e: MessageEvent) => void) | null = null;
  
  constructor(public url: string) {
    MockWebSocket.instance = this;
  }
  
  send(data: string) { /* capture sent messages in test */ }
  close() { this.readyState = WebSocket.CLOSED; }
  
  // Test helper: simulate server push
  simulateMessage(data: unknown) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }));
  }
}

global.WebSocket = MockWebSocket as unknown as typeof WebSocket;
```

Tests then call `MockWebSocket.instance.simulateMessage(...)` inside `act()`.

**Strategy 3 — MSW (Mock Service Worker) for SSE:**
MSW supports intercepting EventSource connections. Define handlers that emit SSE events on a schedule. This tests the full hook + component integration without a real server.

**Key testing concerns:**
- Test reconnect logic: simulate `onclose`, assert reconnect timer fires, simulate `onopen`, assert stale query invalidation
- Test cleanup: unmount component, assert no memory leaks, assert event listeners removed
- Test error states: simulate failed connection, assert error UI renders

---

## 5. SENIOR TRAP QUESTIONS

---

### Trap 1: "Use WebSocket for Everything Real-Time"

**The trap:** Interviewer or candidate says "for any real-time feature, use WebSocket — it's the modern standard."

**Why it's wrong:**
SSE is strictly better for server-to-client-only communication:
- Works through all HTTP proxies and CDNs (WebSocket upgrades are blocked by some corporate proxies and older CDNs)
- HTTP/2 multiplexes many SSE streams over a single TCP connection; WebSocket requires a separate connection per stream
- Built-in reconnect via EventSource API (WebSocket requires manual reconnect logic)
- Standard HTTP authentication, compression, caching headers apply
- Simpler server implementation — any HTTP server can stream SSE

**Correct answer:**
"The transport choice depends on communication direction. For notifications, live feeds, AI streaming, dashboards — SSE over HTTP/2 is superior. WebSocket is the right choice for bidirectional, low-latency communication: chat, collaborative editing, live gaming, trading UIs. Using WebSocket for a notification feed is like renting a bulldozer to mow your lawn."

---

### Trap 2: "Create WebSocket Connection in the Component"

**The trap:** `useEffect(() => { const ws = new WebSocket(url); ... }, [])` inside a feature component.

**Why it's wrong:**
1. Every mount creates a new TCP connection + TLS handshake
2. React StrictMode double-invokes effects in development — you get two connections
3. Navigating away and back re-creates the connection
4. Multiple components using the same data each create separate connections

**Correct answer:**
"Connection ownership must live outside React's component lifecycle. The WebSocket instance should live in a module-level singleton, React Context provider mounted at the app root, or a state manager (Zustand). Components subscribe to messages and send through the shared instance. They do not create or destroy the connection."

---

### Trap 3: "useEffect Cleanup Should Close the WebSocket"

**The trap:** Adding `return () => ws.close()` in the useEffect cleanup of a component that uses a shared WebSocket.

**Why it's wrong:**
If the WebSocket is shared, closing it when one component unmounts disconnects all other subscribers. A user navigating from the chat view to the settings page would disconnect the WebSocket, breaking any other active real-time subscriptions.

**Correct answer:**
"Cleanup must distinguish between closing a connection and unsubscribing from a shared connection. Components unsubscribe their message handlers on cleanup. The connection itself closes only when all subscribers are gone (reference counting) or when the app session ends. A useEffect cleanup that calls `ws.close()` is only correct if that component exclusively owns the WebSocket instance — which, in a well-designed app, should be rare."

---

### Trap 4: "Real-Time Always Means WebSocket / Persistent Connection"

**The trap:** Assuming every 'real-time' requirement needs persistent connections.

**Why it's wrong:**
React Query with a 30-second refetch interval is operationally simpler, works through all proxies, leverages HTTP caching, and is perfectly adequate for many 'real-time' requirements:
- Dashboard metrics that update every minute
- Feed of new articles
- Status of a background job

A persistent connection adds operational complexity: connection pooling, reconnect logic, server-side fan-out infrastructure, load balancer configuration.

**Correct answer:**
"Before reaching for WebSocket or SSE, I ask: what's the required freshness? If 30 seconds is fine, React Query's `refetchInterval` is operationally simpler and just as correct. If I need sub-5-second updates and the volume is low, SSE is ideal. WebSocket is reserved for scenarios where the client also pushes high-frequency data or sub-second latency is a hard requirement."

---

### Trap 5: "CRDTs Solve All Collaboration Problems"

**The trap:** "Just use CRDTs/Yjs — they handle all conflicts automatically, no need to think about conflict resolution."

**Why it's wrong:**
1. **Intent preservation**: CRDTs guarantee convergence, not intent. If Alice deletes a paragraph and Bob edits a sentence in that paragraph simultaneously, the CRDT merges "correctly" but the result may not match either user's intent.
2. **Bundle size**: Yjs adds ~40KB gzipped. For apps where bundle size is critical this matters.
3. **Mental model complexity**: Your team needs to understand CRDT semantics to debug anomalies. "Why did my deletion disappear?" — because a concurrent insert created a non-deleted sibling element.
4. **Not all data types**: CRDTs work well for text, arrays, and maps. They're awkward for relational data with complex invariants (e.g., spreadsheet formulas with cross-cell dependencies).
5. **Tombstones**: Deleted CRDT elements leave tombstones that accumulate over time. Long-lived documents require compaction strategies.

**Correct answer:**
"CRDTs are the right tool for collaborative text editing where convergence matters more than perfect intent preservation. For simpler collaborative features — like multiple users updating a form — last-write-wins with optimistic locking and conflict notification is often sufficient and far simpler to implement and debug."

---

### Trap 6: "Store WebSocket Messages Directly in Component State"

**The trap:** `const [messages, setMessages] = useState<Message[]>([])` and pushing every incoming message into this state.

**Why it's wrong:**
1. **Render thrashing**: Each incoming message triggers a re-render of the component and its entire subtree
2. **No persistence across navigation**: State is lost when the component unmounts
3. **Multiple consumers**: If two components need message data, either you duplicate the subscription or you prop-drill excessively
4. **Memory leak with no virtualization**: An unbounded array in state that grows with every message will cause memory issues in long-running chat sessions

**Correct answer:**
"Messages belong in a normalized store (Zustand slice or React Query cache keyed by conversation ID), not in local component state. Components subscribe to the slice they need. New messages trigger store updates, not component-level setState. For display, I use a virtualized list (react-window or tanstack-virtual) so only visible messages are in the DOM regardless of total message count."

---

## 6. PRODUCTION CODE EXAMPLES

---

### Example 1: WebSocket Singleton with Reconnect + Jitter

```typescript
// lib/wsManager.ts
type MessageHandler = (data: unknown) => void;

class WebSocketManager {
  private ws: WebSocket | null = null;
  private handlers = new Set<MessageHandler>();
  private reconnectAttempt = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private readonly url: string;

  constructor(url: string) { this.url = url; }

  connect() {
    this.ws = new WebSocket(this.url);
    this.ws.onopen = () => { this.reconnectAttempt = 0; };
    this.ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      this.handlers.forEach((h) => h(data));
    };
    this.ws.onclose = () => this.scheduleReconnect();
  }

  private scheduleReconnect() {
    const base = 1000;
    const cap = 30000;
    const jitter = Math.random() * 1000;
    const delay = Math.min(cap, base * 2 ** this.reconnectAttempt) + jitter;
    this.reconnectAttempt++;
    this.reconnectTimer = setTimeout(() => this.connect(), delay);
  }

  subscribe(handler: MessageHandler) { this.handlers.add(handler); }
  unsubscribe(handler: MessageHandler) { this.handlers.delete(handler); }
  send(data: unknown) {
    if (this.ws?.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify(data));
  }
  disconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
  }
}

export const wsManager = new WebSocketManager(process.env.NEXT_PUBLIC_WS_URL!);
```

---

### Example 2: useWebSocket Hook with ReadyState Tracking

```typescript
// hooks/useWebSocket.ts
import { useEffect, useCallback, useSyncExternalStore } from 'react';
import { wsManager } from '@/lib/wsManager';

type ReadyState = 'connecting' | 'connected' | 'reconnecting' | 'offline';

let readyState: ReadyState = 'connecting';
const listeners = new Set<() => void>();
const notifyListeners = () => listeners.forEach((l) => l());

export function useWebSocket<T>(onMessage: (data: T) => void) {
  const state = useSyncExternalStore(
    (cb) => { listeners.add(cb); return () => listeners.delete(cb); },
    () => readyState
  );

  useEffect(() => {
    const handler = (data: unknown) => onMessage(data as T);
    wsManager.subscribe(handler);
    return () => wsManager.unsubscribe(handler);
  }, [onMessage]);

  const send = useCallback((data: unknown) => wsManager.send(data), []);
  return { readyState: state, send };
}
```

---

### Example 3: useSSE — Server-Sent Events Hook

```typescript
// hooks/useSSE.ts
import { useEffect, useRef, useState } from 'react';

type SSEStatus = 'connecting' | 'open' | 'closed' | 'error';

export function useSSE<T>(url: string, onMessage: (data: T) => void) {
  const [status, setStatus] = useState<SSEStatus>('connecting');
  const esRef = useRef<EventSource | null>(null);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    const es = new EventSource(url);
    esRef.current = es;
    es.onopen = () => setStatus('open');
    es.onerror = () => setStatus('error');  // EventSource auto-reconnects
    es.onmessage = (e) => {
      try { onMessageRef.current(JSON.parse(e.data)); } catch { /* skip malformed */ }
    };
    return () => { es.close(); setStatus('closed'); };
  }, [url]);

  return { status };
}
```

---

### Example 4: React Query + WebSocket Invalidation

```typescript
// hooks/useOrdersWithRealtime.ts
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';
import { wsManager } from '@/lib/wsManager';

export function useOrdersWithRealtime(userId: string) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['orders', userId],
    queryFn: () => fetchOrders(userId),
    staleTime: 30_000,
  });

  useEffect(() => {
    const handler = (msg: { type: string; orderId: string }) => {
      if (msg.type === 'ORDER_UPDATED') {
        // Invalidate triggers background refetch
        queryClient.invalidateQueries({ queryKey: ['orders', userId] });
        // Or for instant update without refetch:
        // queryClient.setQueryData(['orders', userId], updater);
      }
    };
    wsManager.subscribe(handler);
    return () => wsManager.unsubscribe(handler);
  }, [userId, queryClient]);

  return query;
}
```

---

### Example 5: Optimistic Message Send

```typescript
// hooks/useSendMessage.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import type { Message } from '@/types';

export function useSendMessage(conversationId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (text: string) =>
      fetch('/api/messages', { method: 'POST', body: JSON.stringify({ conversationId, text }) }).then(r => r.json()),

    onMutate: async (text) => {
      await queryClient.cancelQueries({ queryKey: ['messages', conversationId] });
      const previous = queryClient.getQueryData<Message[]>(['messages', conversationId]);
      const tempMsg: Message = { id: crypto.randomUUID(), text, status: 'sending', createdAt: new Date().toISOString() };
      queryClient.setQueryData<Message[]>(['messages', conversationId], (old = []) => [...old, tempMsg]);
      return { previous, tempId: tempMsg.id };
    },

    onError: (_err, _vars, ctx) => {
      // Roll back to previous state
      queryClient.setQueryData(['messages', conversationId], ctx?.previous);
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['messages', conversationId] });
    },
  });
}
```

---

### Example 6: Throttled Cursor Presence

```typescript
// hooks/useCursorBroadcast.ts
import { useCallback, useRef } from 'react';
import { wsManager } from '@/lib/wsManager';

export function useCursorBroadcast(documentId: string) {
  const lastSentRef = useRef(0);
  const THROTTLE_MS = 50; // max 20fps

  const broadcastCursor = useCallback((x: number, y: number) => {
    const now = Date.now();
    if (now - lastSentRef.current < THROTTLE_MS) return;
    lastSentRef.current = now;
    wsManager.send({ type: 'CURSOR_MOVE', documentId, x, y });
  }, [documentId]);

  return broadcastCursor;
}
```

---

### Example 7: Connection State Banner

```typescript
// components/ConnectionBanner.tsx
import { useConnectionStatus } from '@/hooks/useConnectionStatus';

const MESSAGES = {
  connecting: null,
  connected: null,
  reconnecting: 'Reconnecting…',
  offline: 'You are offline. Changes will sync when reconnected.',
};

export function ConnectionBanner() {
  const status = useConnectionStatus();
  const message = MESSAGES[status];
  if (!message) return null;

  return (
    <div role="status" aria-live="polite"
      className={`fixed top-0 left-0 right-0 py-2 text-center text-sm font-medium z-50
        ${status === 'offline' ? 'bg-red-600 text-white' : 'bg-yellow-400 text-yellow-900'}`}>
      {message}
    </div>
  );
}
```

---

### Example 8: useConnectionStatus with Navigator + WS Probe

```typescript
// hooks/useConnectionStatus.ts
import { useSyncExternalStore } from 'react';

type Status = 'connecting' | 'connected' | 'reconnecting' | 'offline';
let status: Status = 'connecting';
const subs = new Set<() => void>();
const emit = () => subs.forEach((s) => s());

const setStatus = (s: Status) => { if (status !== s) { status = s; emit(); } };

if (typeof window !== 'undefined') {
  window.addEventListener('online', () => setStatus('connecting'));
  window.addEventListener('offline', () => setStatus('offline'));
}

export function notifyWsOpen() { setStatus('connected'); }
export function notifyWsClose() {
  setStatus(navigator.onLine ? 'reconnecting' : 'offline');
}

export function useConnectionStatus(): Status {
  return useSyncExternalStore(
    (cb) => { subs.add(cb); return () => subs.delete(cb); },
    () => status
  );
}
```

---

### Example 9: Long Polling Hook

```typescript
// hooks/useLongPoll.ts
import { useEffect, useRef } from 'react';

export function useLongPoll<T>(url: string, onData: (data: T) => void, enabled = true) {
  const onDataRef = useRef(onData);
  onDataRef.current = onData;

  useEffect(() => {
    if (!enabled) return;
    const controller = new AbortController();
    let lastId = '';

    (async () => {
      while (!controller.signal.aborted) {
        try {
          const res = await fetch(`${url}?since=${lastId}`, { signal: controller.signal });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const json = await res.json();
          if (json.data) { onDataRef.current(json.data); lastId = json.lastId ?? lastId; }
        } catch (e: unknown) {
          if (controller.signal.aborted) break;
          await new Promise((r) => setTimeout(r, 2000));
        }
      }
    })();

    return () => controller.abort();
  }, [url, enabled]);
}
```

---

## 7. INTERVIEW CHEAT SHEET

```
╔══════════════════════════════════════════════════════════════════════════════╗
║              REAL-TIME PATTERNS — QUICK REFERENCE                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  TRANSPORT SELECTION                                                       ║
║  ─────────────────────────────────────────────────────────────────────     ║
║  Freshness > 30s          → React Query refetchInterval                    ║
║  Server→Client only       → SSE (EventSource) — simpler, HTTP/2 friendly   ║
║  Bidirectional + low-lat  → WebSocket                                      ║
║  Collaborative editing    → Yjs (CRDT) over WebSocket                      ║
║  Proxy-blocked env        → Long polling fallback                          ║
║  Offline-capable          → IndexedDB + SW Background Sync                 ║
║                                                                            ║
║  CONNECTION OWNERSHIP                                                      ║
║  ─────────────────────────────────────────────────────────────────────     ║
║  App-wide singleton       → Module-level class (wsManager.ts)              ║
║  Feature-scoped           → React Context Provider                         ║
║  Multi-store              → Zustand slice with ws instance                 ║
║  NEVER                    → new WebSocket() inside a component             ║
║                                                                            ║
║  RECONNECT FORMULA                                                         ║
║  ─────────────────────────────────────────────────────────────────────     ║
║  delay = min(30000, 1000 * 2^attempt) + random(0..1000)                    ║
║  Jitter prevents thundering herd on server restart                         ║
║                                                                            ║
║  REACT QUERY INTEGRATION                                                   ║
║  ─────────────────────────────────────────────────────────────────────     ║
║  WS message → invalidateQueries (re-fetch, slightly stale window)          ║
║  WS message → setQueryData     (instant cache update, no re-fetch)         ║
║  Reconnect  → invalidateQueries() all stale                                ║
║                                                                            ║
║  OPTIMISTIC UI PATTERN                                                     ║
║  ─────────────────────────────────────────────────────────────────────     ║
║  1. Assign tempId = crypto.randomUUID()                                    ║
║  2. onMutate: add optimistic item with status='sending'                    ║
║  3. onError: rollback via context.previous                                 ║
║  4. onSuccess: replace tempId with server-confirmed id                     ║
║  5. timeout: mark failed after 10s with no ack                             ║
║                                                                            ║
║  CRDT vs OT                                                                ║
║  ─────────────────────────────────────────────────────────────────────     ║
║  CRDT (Yjs): peer-to-peer, offline-ok, convergent, ~40KB bundle            ║
║  OT (Google Docs): central server, hard to implement, legacy               ║
║  Default choice: Yjs unless legacy system                                  ║
║                                                                            ║
║  PRESENCE SYSTEM                                                           ║
║  ─────────────────────────────────────────────────────────────────────     ║
║  Online status     → heartbeat every 30s, Redis TTL                       ║
║  Cursor positions  → throttle at 50ms (20fps), interpolate on receive      ║
║  Cursor in React   → useRef (not useState), rAF for render                 ║
║                                                                            ║
║  CONNECTION STATE MACHINE                                                  ║
║  ─────────────────────────────────────────────────────────────────────     ║
║  connecting → connected → reconnecting → offline                           ║
║  navigator.onLine + WS heartbeat + probe fetch = reliable detection        ║
║  Banner: show NOTHING when connected, yellow when reconnecting,            ║
║          red when offline                                                   ║
║                                                                            ║
║  TRAPS TO DODGE                                                            ║
║  ─────────────────────────────────────────────────────────────────────     ║
║  ✗ "WS for all real-time" → SSE for server→client                         ║
║  ✗ WS in component       → singleton/context                              ║
║  ✗ ws.close() in cleanup → only unsubscribe handler                       ║
║  ✗ Real-time = WS        → polling for >30s freshness is fine              ║
║  ✗ CRDTs solve all collab → complex, bundle size, tombstones               ║
║  ✗ useState for messages  → Zustand + virtualized list                    ║
║                                                                            ║
║  TESTING STRATEGY                                                          ║
║  ─────────────────────────────────────────────────────────────────────     ║
║  Mock WebSocket class globally before tests                                ║
║  Expose simulateMessage() helper on mock                                   ║
║  Wrap in act() when simulating incoming messages                           ║
║  Test reconnect: simulate onclose, assert timer, simulate onopen           ║
║  MSW for SSE stream mocking                                                ║
║                                                                            ║
║  OFFLINE-FIRST STACK                                                       ║
║  ─────────────────────────────────────────────────────────────────────     ║
║  Storage   → Dexie (IndexedDB wrapper)                                     ║
║  Queue     → Service Worker Background Sync API                            ║
║  Conflicts → Domain-dependent: LWW / client-wins / CRDT                   ║
║  React     → React Query with IndexedDB as cache, useSyncStatus hook       ║
║                                                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## ADDITIONAL TALKING POINTS FOR ARCHITECT-LEVEL DISCUSSION

---

### When to Use Each WebSocket Library

- **Native WebSocket API**: For custom infrastructure, max control, no dependency overhead
- **Socket.IO**: Fallback transport support (long polling), rooms, namespaces. Adds overhead (~45KB). Use when targeting environments with unreliable WebSocket support.
- **@tanstack/query with WebSocket**: Not a WebSocket library — use for cache integration
- **Ably / Pusher**: Managed service; abstracts scaling, presence, history. Use when WebSocket infra is not a core competency

---

### HTTP/2 and SSE — The Multiplexing Advantage

HTTP/1.1 browsers limit connections to ~6 per domain. A page using multiple SSE streams on HTTP/1.1 hits this limit quickly. HTTP/2 solves this entirely: all streams multiplex over a single TCP connection. This makes SSE on HTTP/2 a legitimate replacement for WebSocket in most dashboard and notification scenarios.

WebSocket does not benefit from HTTP/2 multiplexing the same way — each WebSocket connection upgrades from HTTP/1.1 semantics. RFC 8441 defines WebSocket-over-HTTP/2 but support is not universal.

---

### Service Worker + WebSocket: The Edge Case

Service Workers cannot hold WebSocket connections directly (SWs have no persistent lifecycle). The WebSocket must live in the main window or a SharedWorker. A SharedWorker is the correct abstraction if you need a single WebSocket shared across multiple browser tabs from the same origin — only one connection for the entire browser session, not one per tab.

```typescript
// Concept: SharedWorker holds the singleton WS across tabs
// sharedWorker.ts
const ws = new WebSocket(WS_URL);
const ports: MessagePort[] = [];

self.onconnect = (e) => {
  const port = e.ports[0];
  ports.push(port);
  ws.onmessage = (msg) => ports.forEach((p) => p.postMessage(msg.data));
  port.start();
};
```

This pattern is used by Figma and other multi-tab collaborative tools.

---

### Performance: Avoiding Re-Render Storms from Real-Time Updates

High-frequency WebSocket messages (cursor positions, trading prices) can trigger hundreds of re-renders per second if piped directly into React state.

Mitigation pattern:
1. Store incoming data in a ref (`useRef`)
2. On each `requestAnimationFrame`, read the ref and update state if changed
3. Throttle state updates to ~16ms (60fps) or ~32ms (30fps) depending on requirement

```typescript
const latestData = useRef<PriceData | null>(null);

useEffect(() => {
  const handler = (data: PriceData) => { latestData.current = data; };
  wsManager.subscribe(handler);
  return () => wsManager.unsubscribe(handler);
}, []);

useEffect(() => {
  let raf: number;
  const tick = () => {
    if (latestData.current) {
      setDisplayPrice(latestData.current.price);
      latestData.current = null;
    }
    raf = requestAnimationFrame(tick);
  };
  raf = requestAnimationFrame(tick);
  return () => cancelAnimationFrame(raf);
}, []);
```

This decouples the WebSocket receive rate from the React render rate entirely.

---

*End of file — 12_realtime_patterns_interview.md*
*Created: 2026-08-22 | Target: Staff/Principal Front-End/Full-Stack Architect*
