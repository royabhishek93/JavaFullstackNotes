# WebSocket vs SSE vs Long Polling
### What Each Is, Latency, When to Pick Which

---

## PART 1 — THE STUDENT CONVERSATION

**The problem: HTTP is request-response. But real-time apps need the SERVER to push data to the CLIENT.**

Normal HTTP: client asks, server answers. Client asks again, server answers again. The client always initiates. The server can never say "hey, something changed" without being asked first.

But for a live leaderboard, a chat app, a stock ticker, or an Uber driver's location — you need the server to push updates the moment they happen, not when the client decides to ask.

Three solutions exist, each with different trade-offs:

1. **Long Polling** — the client asks and the server holds the connection open until it has something to say. Old-school but widely compatible.
2. **Server-Sent Events (SSE)** — a persistent one-way channel from server to client. Simple, uses regular HTTP.
3. **WebSocket** — a full two-way persistent connection. Real-time, bidirectional. The gold standard for true real-time.

---

## PART 2 — HOW EACH WORKS

### Long Polling

```
Client                                    Server
──────                                    ──────

GET /events?lastId=42 ─────────────────► Receives request.
                                         Checks: any new events since id=42?
                                         No → HOLD the connection open...
                                         (server does not respond yet)

                                         ... 20 seconds pass ...

                                         New event arrives! Event id=43
GET /events?lastId=42 ◄──────────────── Respond: { event: {...}, id: 43 }

Client processes event, immediately sends next request:
GET /events?lastId=43 ─────────────────► Server holds again...

Characteristics:
  Connection: closed after each response, client immediately re-opens
  Direction: client → server always initiates
  Latency: delay = server hold time variance (up to a few seconds)
  Overhead: HTTP headers on every request (~500 bytes × many requests)
  Compatibility: works everywhere (HTTP/1.1, firewalls, proxies)
  Server resources: 1 thread per waiting connection (in blocking model)
```

### Server-Sent Events (SSE)

```
Client                                    Server
──────                                    ──────

GET /events ───────────────────────────► Opens persistent HTTP connection.
                                         Content-Type: text/event-stream
                                         Connection stays OPEN.

                                         New event at t=1s:
              ◄────────────────────────── data: {"type":"score","value":9821}\n\n

                                         New event at t=3s:
              ◄────────────────────────── data: {"type":"rank","rank":1}\n\n

                                         New event at t=5s:
              ◄────────────────────────── data: {"type":"score","value":9900}\n\n

              (connection stays open indefinitely)

Characteristics:
  Connection: persistent, server keeps it open
  Direction: SERVER → CLIENT only (one-way push)
  Latency: <100ms (no round trip, server pushes immediately)
  Overhead: single connection, minimal per-event overhead
  Compatibility: all browsers natively (EventSource API), HTTP/1.1 and HTTP/2
  Auto-reconnect: browser handles automatically (built into EventSource)
  Server resources: 1 connection per client (efficient with async servers)
  Limitation: client cannot send data over SSE (use separate POST requests)
```

### WebSocket

```
Client                                    Server
──────                                    ──────

HTTP Upgrade request:
GET /ws ────────────────────────────────► 
  Connection: Upgrade
  Upgrade: websocket
  Sec-WebSocket-Key: dGhlIHNhbXBsZQ==

                       ◄──────────────── HTTP 101 Switching Protocols
                                         Upgrade: websocket
                                         Sec-WebSocket-Accept: ...

TCP connection is NOW a WebSocket. HTTP headers no longer needed.

Client → Server (frame):
{ type: "chat", text: "Hello!" } ──────►

Server → Client (frame):
              ◄────────────────────────── { type: "chat", from: "Bob", text: "Hi!" }

Server → Client (frame):
              ◄────────────────────────── { type: "notification", ... }

Client → Server (frame):
{ type: "ping" } ──────────────────────►

              ◄────────────────────────── { type: "pong" }

Characteristics:
  Connection: persistent TCP connection, no HTTP overhead per message
  Direction: BIDIRECTIONAL (both can send at any time)
  Latency: <50ms (no HTTP overhead, pure TCP frames)
  Overhead: 2 bytes per frame (vs ~500 bytes HTTP headers)
  Compatibility: all modern browsers, some corporate firewalls block it
  Reconnect: manual (no built-in auto-reconnect, must implement)
  Server resources: 1 socket per client (very efficient)
```

---

## PART 3 — COMPARISON TABLE

```
┌──────────────────────┬────────────────┬───────────────────┬─────────────────┐
│                      │  Long Polling  │   SSE             │   WebSocket     │
├──────────────────────┼────────────────┼───────────────────┼─────────────────┤
│ Direction            │ Client→Server  │ Server→Client     │ Both            │
│ Latency              │ 1–5s           │ <100ms            │ <50ms           │
│ Overhead per msg     │ ~500B headers  │ ~50B              │ ~2B             │
│ Reconnect            │ Built-in       │ Built-in          │ Manual          │
│ Firewall friendly    │ Yes            │ Yes (HTTP)        │ Sometimes no    │
│ HTTP/2 multiplexing  │ No             │ Yes               │ No (own proto)  │
│ Client sends data    │ New request    │ Separate POST     │ Same connection │
│ Load balancer sticky │ Not needed     │ Needed (conn)     │ Needed (conn)   │
│ Server framework     │ Any            │ Any async         │ Needs WS support│
└──────────────────────┴────────────────┴───────────────────┴─────────────────┘
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your leaderboard needs to show real-time rank updates. How do you push updates to 100K concurrent users?"

**You (architect answer):**

> "For a leaderboard with rank updates, I'd use SSE. Here's my reasoning:
>
> The leaderboard is read-only from the user's perspective. Users watch their rank change —
> they don't send rank updates back to the server. That's a one-way push from server to client.
> SSE is purpose-built for this: it's a persistent HTTP connection where the server streams
> events as they happen. No WebSocket handshake complexity, no protocol upgrade, just a
> persistent HTTP GET with chunked transfer encoding.
>
> For 100K concurrent users: I'd use nginx as a reverse proxy with upstream keepalive,
> and behind it async Java (Spring WebFlux) or Go servers. Each SSE connection is a
> lightweight async handle — not a thread. Async servers can hold 100K+ SSE connections
> per server with moderate memory.
>
> The update flow: score events flow from Kafka into Redis ZSET. A separate SSE Publisher
> service reads from Kafka and pushes rank change events to connected SSE clients.
> I'd shard by leaderboard ID — all users watching leaderboard:global connect to
> SSE servers responsible for that leaderboard.
>
> If the user also needs to submit scores (e.g., a gaming client), I'd use WebSocket for
> that — bidirectional. SSE for the read-heavy leaderboard view, WebSocket for the
> interactive game session."

---

## PART 5 — WHEN TO PICK WHICH

```
Long Polling:
  ✓ Legacy systems that can't upgrade to WebSocket/SSE
  ✓ Need to work through all corporate firewalls/proxies
  ✓ Low frequency updates (every 30+ seconds)
  ✗ Avoid for <5 second update frequency (too much overhead)
  Use case: simple notification bell, periodic status checks

SSE (Server-Sent Events):
  ✓ Server pushes to client only (one-way)
  ✓ Simple, works on standard HTTP/HTTPS
  ✓ Auto-reconnect built into browser
  ✓ Works with HTTP/2 (multiple SSE streams over one TCP connection!)
  ✓ Best for: dashboards, feeds, leaderboards, live scores, news tickers
  ✗ Client can't send data over SSE channel
  Use case: leaderboard, stock ticker, live feed updates, progress notifications

WebSocket:
  ✓ True bidirectional communication
  ✓ Lowest latency, lowest overhead per message
  ✓ Client and server both initiate messages
  ✗ More complex (connection management, reconnection logic)
  ✗ Some corporate firewalls block WebSocket upgrade
  ✗ Stateful: sticky sessions needed at load balancer
  Use case: chat (WhatsApp), multiplayer gaming, collaborative editing (Google Docs),
            live trading, real-time cursor sharing

Your 21 systems:
  Chat App (04):           WebSocket (bidirectional messages)
  Leaderboard (13):        SSE (server pushes rank updates)
  Stock Broker (19):       WebSocket (bid/ask updates + order placement)
  Uber driver tracking (06): WebSocket or SSE (server pushes location)
  Collaborative Editor (18): WebSocket (real-time cursor, edits)
```

---

## QUICK REFERENCE CARD

```
Decision tree:
  Does client need to SEND data over the real-time channel?
    YES → WebSocket
    NO  → SSE (simpler, more compatible)

  Is latency <100ms acceptable (vs <50ms)?
    YES → SSE
    NO  → WebSocket

  Working through enterprise firewalls/proxies?
    YES → SSE or Long Polling (plain HTTP)
    NO  → WebSocket OK

SSE in Spring Boot:
  @GetMapping(value="/events", produces=MediaType.TEXT_EVENT_STREAM_VALUE)
  public Flux<ServerSentEvent<String>> stream() {
      return Flux.interval(Duration.ofSeconds(1))
          .map(i -> ServerSentEvent.<String>builder()
              .data("rank:" + getRank())
              .build());
  }

WebSocket in Spring Boot:
  @Configuration
  @EnableWebSocket
  public class WsConfig implements WebSocketConfigurer {
      public void registerWebSocketHandlers(WebSocketHandlerRegistry r) {
          r.addHandler(new ChatHandler(), "/ws/chat").setAllowedOrigins("*");
      }
  }

Interview one-liner:
"SSE is a one-way persistent HTTP stream — perfect for server-to-client
dashboards and feeds. WebSocket is a bidirectional TCP channel — needed
when clients also send data in real-time. Long polling is the fallback
for environments where persistent connections are blocked."
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Interviewers pick real-time problems specifically to test whether you know which protocol fits — getting this wrong signals you're guessing.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **04 — Chat (WhatsApp)** | WebSocket — bidirectional. Alice sends a message AND receives replies on the same connection. SSE is one-way; chat needs two-way. |
| **06 — UBER** | WebSocket — driver sends GPS location every 3s (client→server) AND receives dispatch events (server→client). Both directions active simultaneously. |
| **13 — Leaderboard** | SSE — server pushes rank updates to viewing users. Users don't send rank data back. One-way push = SSE. No WebSocket complexity needed. |
| **18 — Text Editor (Google Docs)** | WebSocket — every keystroke sent immediately (client→server). Changes broadcast to all collaborators (server→client). Sub-100ms latency required. |
| **19 — Stock Broker** | WebSocket — client places orders (client→server) AND receives bid/ask stream updates every 100ms (server→client). Low latency bidirectional = only WebSocket. |

**Architect's one-liner for the interview:**
*"If the client sends data in real-time, you need WebSocket — SSE is one-way server push, long polling is a workaround from 2005."*
