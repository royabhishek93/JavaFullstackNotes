# WebSocket vs SSE vs Long Polling — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE | Episode: 39

## HOOK (0:00–0:30)

Picture this: a gaming leaderboard app goes viral overnight. 100,000 users open it at the same time to watch their rank update live. The backend team had built it with plain HTTP polling — every client asking "any updates?" every 2 seconds. Within an hour, the server fleet is pegged at 100% CPU, not from computing ranks, but from opening and closing HTTP connections. Every single poll costs roughly 500 bytes of headers, round-tripped every 2 seconds, times 100,000 clients. That's tens of millions of wasted requests per hour — for data that changes maybe once every few seconds.

The fix wasn't "add more servers." The fix was picking the right real-time transport in the first place. That's what we're breaking down today.

[Screen cue: A graph spiking to 100% CPU, then a "?" over three logos — WebSocket, SSE, Long Polling]

## THE PROBLEM (0:30–2:00)

Here's the core issue: HTTP was never designed for the server to talk first. Client asks, server answers. Client asks again, server answers again. The client always has to initiate — the server can never just say "hey, something changed" out of nowhere.

But think about the apps you use every day. A live leaderboard. A chat app. A stock ticker. An Uber map showing your driver moving in real time. In every one of these, the server knows something changed *before* you do — a new message arrived, a stock price ticked, a driver moved three meters. If your architecture forces the client to keep asking "anything new? anything new? anything new?" you're either wasting resources polling too often, or your users are staring at stale data because you're polling too rarely.

Think about it this way: it's like calling a restaurant every 30 seconds to ask if your table is ready, instead of the host just calling you when it's your turn. One of those approaches doesn't scale past a handful of tables. The other one is what every real-time system actually needs.

[Screen cue: Diagram — a client repeatedly firing "GET /status?" arrows at a server, each one immediately answered "no", looping forever]

## THE SOLUTION (2:00–5:00)

There are exactly three ways engineers solve this, and each is a different trade-off between simplicity, latency, and direction of data flow.

**First: Long Polling.** The client sends a request, but instead of answering immediately, the server just... holds it open. It waits. If nothing happens for 20 seconds, maybe it times out and responds empty, and the client immediately fires another request. But the moment something DOES happen — say a new leaderboard event arrives — the server responds right then, with that data. The client processes it and immediately opens a new long-poll request. It's a hack, but a clever one: you get near-push behavior using vanilla HTTP request-response. The catch: every single round trip still carries full HTTP headers — about 500 bytes of overhead — and in a blocking server model, each waiting connection often ties up a full server thread.

**Second: Server-Sent Events, or SSE.** Now watch what happens when the client opens the connection differently — with `Content-Type: text/event-stream`. Instead of closing after one response, the connection stays open indefinitely. The server just keeps writing tiny `data: {...}` chunks down that same open pipe, whenever it wants. At t=1 second: a score update. At t=3 seconds: a rank change. At t=5 seconds: another score. No new requests. No new handshakes. Just a continuous drip of events, and it's built entirely on standard HTTP — your browser's native `EventSource` API handles it, including automatic reconnection if the connection drops.

**Third: WebSocket.** This one starts as a normal HTTP request but with an `Upgrade: websocket` header. The server responds `101 Switching Protocols`, and at that point the underlying TCP connection stops being HTTP entirely — it becomes a raw, bidirectional pipe. Client sends a frame, server sends a frame back, either side can talk at any time, with only about 2 bytes of framing overhead instead of hundreds of bytes of HTTP headers. This is the only one of the three where the client can push data over the *same* channel it's receiving on.

Now map this onto real systems. A chat app like WhatsApp needs WebSocket — Alice sends a message and receives replies on the exact same connection; that's bidirectional by nature. A leaderboard just needs SSE — the server pushes rank changes, but users never send rank data back; it's one-way. Uber's driver tracking needs WebSocket — the driver's phone sends GPS coordinates every few seconds *and* receives dispatch events at the same time, so both directions are active simultaneously. A collaborative editor like Google Docs needs WebSocket too — every keystroke goes out immediately, and every collaborator's edits come back, sub-100ms. And a stock trading app needs WebSocket — the client places orders while simultaneously receiving a live bid/ask stream every 100 milliseconds.

[Screen cue: Live-drawn diagram — three lanes, "Long Polling" showing repeated open/close arrows, "SSE" showing one persistent arrow server→client, "WebSocket" showing a persistent double-headed arrow]

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)

Let's get into the traps, because this is where interviews — and production systems — actually separate people who understand this from people who memorized buzzwords.

**Trap one: picking WebSocket by default because it "sounds more real-time."** WebSocket is not automatically the best choice. If your leaderboard only needs to push rank updates, WebSocket adds unnecessary complexity: you now need to manage reconnection logic yourself, because unlike SSE, WebSocket has no built-in auto-reconnect. Drop the connection, and your client code has to detect it and reconnect manually. SSE gives you that for free through `EventSource`.

**Trap two: ignoring corporate firewalls.** WebSocket connections start as an HTTP upgrade, but some corporate proxies and older firewalls don't understand the upgrade handshake and just block it outright. SSE and long polling, being plain HTTP, sail right through those same environments. If you're building something that has to work inside enterprise networks, that's a real constraint, not a theoretical one.

**Trap three: forgetting load balancer stickiness.** Both SSE and WebSocket hold a persistent connection to one specific backend server. If your load balancer round-robins each new request to a different server, your persistent connection breaks the moment a health check or reconnect hits a different node. You need sticky sessions — the load balancer has to route based on connection, not per-request. Long polling doesn't need this because every request is short-lived and stateless — any server can pick it up.

**Trap four: using long polling for anything under a 5-second update frequency.** Look at the overhead math again: roughly 500 bytes of HTTP headers, on every single request, and if you're polling every second, that's 500 bytes times however many clients times 3,600 seconds an hour. Long polling is a legacy fallback — appropriate for low-frequency updates like a notification bell checking every 30+ seconds, and appropriate when you truly must support ancient or restrictive network environments. Anything faster than that, you're burning bandwidth and server threads for no reason.

**Trap five: assuming SSE can receive data from the client.** It can't. SSE is explicitly one-way, server-to-client only. If your app needs the client to send something back — even occasionally — you either pair SSE with a separate POST endpoint for the outbound direction, or you just use WebSocket, which supports both directions on the same channel. Engineers sometimes try to force bidirectional behavior into SSE and end up building a worse, more complicated version of a WebSocket.

**Trap six: not knowing the HTTP/2 advantage of SSE.** Because SSE rides on regular HTTP, it benefits from HTTP/2 multiplexing — meaning multiple SSE streams can share a single underlying TCP connection. WebSocket, by contrast, owns its own protocol once the upgrade happens; it doesn't multiplex the same way. That's a meaningful infrastructure difference when you're running thousands of connections through the same edge server.

Look at the actual latency numbers side by side: Long Polling sits at 1 to 5 seconds of delay because you're bound by however long the server holds the connection open before it has to time out and reconnect. SSE gets you under 100 milliseconds because the server can push the instant it has something — no round trip needed. WebSocket gets you under 50 milliseconds because there's no HTTP framing at all, just raw TCP frames with about 2 bytes of overhead versus roughly 500 bytes of HTTP headers per message.

[Screen cue: Comparison table — Direction / Latency / Overhead per message / Reconnect / Firewall friendly / HTTP2 multiplexing / Client sends data / LB stickiness needed, across all three columns]

## REAL WORLD (8:00–9:30)

Let's ground this in scale. Take a leaderboard system built to serve 100,000 concurrent users watching live rank changes. The architect's answer here — and this is a real interview-tested pattern — is SSE, backed by nginx as a reverse proxy with upstream keepalive, sitting in front of async servers like Spring WebFlux or Go. Why does that combination matter? Because each SSE connection is a lightweight async handle, not an OS thread. A single async server can hold 100,000-plus SSE connections with moderate memory, where a naive thread-per-connection model would fall over. Score events flow from Kafka into a Redis sorted set, and a dedicated SSE Publisher service reads from Kafka and pushes rank-change events out to connected clients — sharded by leaderboard ID, so every user watching the "global" leaderboard is routed to the same pool of SSE servers.

Now think about India-scale real-time products. A ride-hailing app tracking driver location in real time is exactly the WebSocket use case we described — the driver's app is sending GPS pings every few seconds while simultaneously receiving dispatch and ETA updates, both directions live, sub-100ms latency expected by users watching that car icon glide across the map. A live-scores or live-leaderboard feed inside a fantasy sports or gaming app is the textbook SSE case — thousands to lakhs of viewers, one-way push, no client data going back over that channel, which is exactly why SSE scales so much more cheaply than standing up a WebSocket per viewer. And a stock or trading app needs WebSocket specifically because the client is doing two things at once on one connection: placing orders, and consuming a live bid/ask stream updating every 100 milliseconds — that combination of "client sends AND receives, both fast" is the single clearest signal in any interview that the answer is WebSocket, not SSE, not long polling.

[Screen cue: Three company-style logos with numbers — "100K concurrent SSE connections", "GPS updates every 3s bidirectional", "100ms bid/ask stream + live order placement"]

## OUTRO + NEXT EPISODE (9:30–10:00)

So here's the one-liner to remember, straight from the architect's playbook: if the client needs to send data in real-time, you need WebSocket. If it's server-to-client only, SSE is simpler and just as fast. Long polling is the fallback for environments where persistent connections get blocked.

If you liked this breakdown, hit subscribe — we're going through a full system design series, one hard problem at a time. Next episode, we're tackling something that breaks distributed systems in the worst possible way: the split-brain problem, when two nodes both think they're the primary at the same time. If you've ever wondered how a cluster can have two "leaders" arguing with each other, that's episode 40 — see you there.

[Screen cue: "Next: 040 — Split-Brain Problem: Two Primary Nodes" with subscribe button animation]
