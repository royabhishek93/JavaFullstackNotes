# Interview Guide: Network Protocols — HTTP, WebSocket, WebRTC, TCP & UDP

## 🗣️ The Interview Scenario

> "You need to design three different products: a REST-based e-commerce API, a WhatsApp-style chat app, and a Google Meet-style video calling app. For each one, which network protocol would you choose at the transport and application layer, and why would using the wrong one break the product?"

This question tests whether you understand protocols as **design decisions with real consequences**, not just trivia you memorized in college networking class.

## 🏗️ Architect's Explanation (For a New Developer)

Think about how two strangers who don't speak the same language would ever manage to trade goods at a market. They need an agreed **set of rules** — maybe pointing, maybe specific hand gestures — so that even without shared vocabulary, the interaction is predictable. A **network protocol** is exactly this: an agreed set of rules so two computers can exchange data reliably, even though they don't inherently "understand" each other.

There are two big questions to answer when picking protocols for a system:

1. **Who talks to whom?** Is it always "client asks, server answers" (client-server), or can any two peers just talk directly (peer-to-peer)?
2. **How much reliability do I need versus how much speed?** Do I need every single packet to arrive, in order, guaranteed (like a bank transfer)? Or can I tolerate losing a few packets if it means things arrive *faster* (like a live video call, where a single dropped frame doesn't matter because you're already watching the next one)?

Once you can answer those two questions for your specific product, the protocol choice becomes obvious rather than memorized.

## 📊 Visualize It

```
CLIENT-SERVER MODEL (HTTP, WebSocket, FTP, SMTP)
   Client 1 ──request──▶  ┌────────┐
   Client 1 ◀─response──  │ Server │
   Client 2 ──request──▶  │        │
   Client 2 ◀─response──  └────────┘
   Clients NEVER talk directly to each other, even via WebSocket.

PEER-TO-PEER MODEL (WebRTC)
   Peer A ◀──────direct connection──────▶ Peer B
             (server only used briefly for signaling/discovery)
```

```
TRANSPORT LAYER: TCP vs UDP

TCP (ordered, reliable, connection-oriented)
  [Pkt1]→[Pkt2]→[Pkt3] ... if Pkt3 is lost → ACK missing → RESEND Pkt3
  Guarantees: ordering + acknowledgment + retransmission

UDP (best-effort, connectionless)
  [Datagram1] [Datagram2] [Datagram3] → sent in parallel, no ACKs
  If Datagram2 is lost → nobody resends it → stream just continues
  Guarantees: NONE, but much lower latency
```

## 🔧 Deep Dive: How It Actually Works

### The 7-layer model, scoped down to what actually matters for HLD

Out of the classic OSI seven layers (application, presentation, session, transport, network, data link, physical), interview-relevant system design almost always concerns just two: **Application layer** and **Transport layer**.

### Application Layer — split into Client-Server vs Peer-to-Peer

**Client-Server protocols:** HTTP, SMTP, WebSocket.
- **Rule:** the client always initiates, the server always responds. One-directional initiation, even if data flows both ways after the connection is set up.
- **HTTP (HyperText Transfer Protocol):** connection-oriented; used to fetch/navigate web pages via hyperlinks. This is the default choice for typical request/response APIs. Prefer **HTTPS** (HTTP + TLS) in production — plain HTTP and especially **FTP are not secure** because the data connection is unencrypted.
- **FTP (File Transfer Protocol):** maintains **two connections** — a **control connection** (stays alive for the session) and a **data connection** (created/torn down per file transfer). Rarely used today specifically because the data connection is unencrypted, making it insecure for real production use.
- **SMTP / IMAP / POP3 (email):** SMTP is used only for **sending** mail. IMAP and POP3 are used for **receiving/reading** mail. POP3 downloads and then **deletes** the message from the server (bad for multi-device access). IMAP keeps mail synced on the server so you can read it from multiple devices — which is why SMTP+IMAP is the dominant combination today, not SMTP+POP3. Internally, a **User Agent** sends to an **MTA (Message Transfer Agent)**, which routes to another MTA, which finally hands off to the recipient's User Agent.
- **WebSocket:** Still fundamentally client-server (a common misconception is calling it peer-to-peer — it is **not**). Its defining feature is **bidirectional** communication over a single persistent connection: the client can push to the server, and — critically — the **server can push to the client** without the client having to poll. This is why WebSocket is the correct choice whenever the server needs to *proactively* notify a client (e.g., "a new chat message has arrived") instead of the client wastefully polling "did a message arrive? did a message arrive?" repeatedly.

**Peer-to-Peer protocols:** WebRTC.
- No mandatory server hop for the actual data exchange — peers can talk **directly** to each other. Any participant can act as both client and server, whoever holds the needed data.
- Because it skips the server round-trip for the actual media/data payload, it is **fast** — this is exactly why it's the protocol underneath real-time video calling apps.

### Transport Layer — TCP vs UDP

**TCP/IP:**
- Maintains a **virtual connection** before any data flows.
- Breaks data into small **packets** and assigns **sequence numbers**.
- **Ordering is guaranteed** — packets are reassembled in the correct sequence on the receiving side even if they arrive out of order.
- **Acknowledgment-based reliability** — every packet is ACKed; if a sender doesn't receive an ACK for a packet, it **retransmits** it.
- Trade-off: all this reliability machinery (handshake, sequencing, ACKs, retransmission) costs latency.

**UDP:**
- **No connection is established** beforehand — data is just sent.
- Breaks data into **datagrams** and can send them over multiple parallel virtual paths simultaneously (not a single ordered channel).
- **No ordering guarantee** — a datagram sent later can arrive earlier.
- **No acknowledgment, no retransmission** — it's a **best-effort** delivery mechanism.
- Trade-off: because it skips connection setup, sequencing, and ACK/retry, it is **significantly faster** than TCP.

### Mapping the transport choice to real products

- **Live streaming / video calling:** use **UDP**. If a video frame is lost mid-call, nobody wants the call to pause and retransmit that one frame — you'd rather keep playing the *next* frames and accept the tiny glitch. Speed and continuity matter more than perfect completeness. **WebRTC runs on top of UDP** at the lower layer for exactly this reason.
- **Messaging apps (WhatsApp, Telegram):** use **WebSocket** (client-server, bidirectional) — because the server must be able to *push* a newly arrived message to the recipient client without the client incessantly polling.
- **Standard web/API traffic:** use **HTTP/HTTPS** — connection-oriented, ordered, reliable, and the universal default for typical request-response interactions.
- **File transfer needing encryption:** avoid legacy FTP; use HTTPS-based transfer or SFTP-style secure alternatives instead, because plain FTP's data connection is unencrypted.

## 🔥 Real Production Incident & Fix

**What broke:** A team building a live-bidding auction platform initially implemented "real-time price updates" using **HTTP polling** (client calls `GET /current-price` every 500ms). Under a viral flash-sale event, concurrent users spiked from 5K to 80K, and the polling load alone (80K clients × 2 requests/sec) overwhelmed the API gateway and backend, causing 5xx errors and a full outage during the highest-value bidding window.

**How it was detected:** CloudWatch/API Gateway request-count graphs showed request volume scaling linearly with connected users on a single "cheap" read endpoint, dwarfing all other traffic combined. Load balancer 5xx error-rate alarms fired, and support tickets confirmed users saw stale prices right before the outage (a telltale sign of an overwhelmed polling endpoint, not a data problem).

**Root cause:** Using a client-initiated, client-server request/response protocol (plain HTTP polling) for a use case that is fundamentally "server needs to push updates" is the wrong protocol shape — it multiplies load linearly with connected clients and polling frequency instead of scaling with actual price-change events.

**The fix:** The team replaced polling with a **WebSocket**-based push channel: clients open one persistent connection, and the server pushes a price update event only when the price actually changes. This collapsed request volume from "N clients × poll frequency" down to "N clients × actual price-change events," which is orders of magnitude lower under bursty conditions. The outage was fully avoided in the next flash-sale event with 3x more concurrent users than the one that caused the original incident.

```
BEFORE (HTTP polling): load scales with (clients × poll rate) — explodes under spikes
  80,000 clients × 2 req/sec = 160,000 req/sec on ONE endpoint

AFTER (WebSocket push): load scales with (clients × actual events) — stays flat
  80,000 persistent connections, server pushes only on real price changes
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Is WebSocket peer-to-peer since both sides can send messages?**
No — this is a very common misconception. WebSocket is still a client-server protocol; it's just bidirectional over one persistent connection. The client always connects to a server, and two clients never talk to each other directly through WebSocket. True peer-to-peer (like WebRTC) allows direct machine-to-machine communication without a server relaying the actual payload.

**Q2: Why would you ever use UDP if it can lose data — isn't that always bad?**
It depends entirely on whether the application can tolerate loss in exchange for speed. For live video/audio calling, a dropped frame is a minor, often unnoticed glitch, and retransmitting it (as TCP would) would actually make the experience worse by introducing lag or stutter waiting for a stale frame. UDP's lack of acknowledgment/retransmission overhead is precisely why it's the transport of choice for real-time streaming.

**Q3: How does TCP guarantee ordering if packets can arrive out of order over the network?**
TCP assigns a sequence number to every packet before sending. The receiving side buffers incoming packets and reassembles them according to sequence number regardless of arrival order, and uses acknowledgments per packet — if an ACK isn't received within an expected window, the sender retransmits that specific packet.

**Q4: Why is WebRTC considered fast if peer-to-peer connections still need some kind of discovery?**
WebRTC typically uses a lightweight signaling step (often over a server) purely to help two peers discover and negotiate connection details, but once that's done, actual media/data flows directly between the peers rather than being relayed through a server. Skipping the server hop for the bulk data transfer is what gives it its speed advantage, and it uses UDP underneath for the same low-latency reasoning as live streaming.

**Q5: Why is FTP considered insecure, and what would you use instead in a modern system?**
FTP maintains a separate data connection for the actual file transfer, and that data connection is unencrypted, so file contents can be intercepted in transit. In a modern system you'd use HTTPS-based file upload/download endpoints or a secure variant, ensuring encryption is applied to both control and data channels — this is the same reasoning that pushes web traffic from HTTP to HTTPS.

**Q6: When designing a chat application, why not just use HTTP with fast polling instead of WebSocket?**
Polling means the client asks "any new messages?" on a fixed interval regardless of whether anything actually happened, which wastes resources and adds visible latency (a message could sit unseen until the next poll tick). WebSocket lets the server push the message to the client the instant it's ready, giving true real-time delivery with far less wasted request volume, especially at scale — this exact trade-off is why polling failed in the auction-platform incident above.

## 🔑 Key Takeaway

Pick your protocol by answering two questions — "who initiates communication?" (client-server vs peer-to-peer) and "do I need guaranteed ordered delivery, or do I need raw speed with tolerable loss?" (TCP vs UDP) — and the right choice for HTTP, WebSocket, WebRTC, TCP, or UDP falls out naturally from the actual product requirement, not from memorized rules.
