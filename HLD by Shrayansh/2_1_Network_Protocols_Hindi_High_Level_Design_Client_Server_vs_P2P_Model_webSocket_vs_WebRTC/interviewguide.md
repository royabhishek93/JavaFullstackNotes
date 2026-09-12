# Interview Guide: Network Protocols — Client-Server vs P2P, WebSocket vs WebRTC, TCP vs UDP

## 🗣️ The Interview Scenario

> "You need to design three very different products: a WhatsApp-style messaging app, a video-calling feature like Google Meet, and a plain content website. All three need 'network communication' — but would you use the same protocol stack for all three? Walk me through your protocol choices and justify each one."

This question tests whether a candidate can map **business requirements** (real-time bidirectional chat vs. low-latency media vs. simple request/response pages) to the **correct protocol layer choices** — instead of reflexively saying "just use HTTP for everything."

## 🏗️ Architect's Explanation (For a New Developer)

A **network protocol** is simply an agreed-upon set of rules that two systems follow so they can understand each other — like two people agreeing to speak the same language and follow the same conversational etiquette before they can have a meaningful conversation.

At a high level, think of network communication happening in **layers** (the classic OSI 7-layer model), but for system design interviews only two layers really matter day-to-day:

- **Application Layer** — the "what are we actually talking about" layer (HTTP, FTP, SMTP, WebSocket, WebRTC).
- **Transport Layer** — the "how do we physically move the bytes reliably (or quickly)" layer (TCP, UDP).

At the Application Layer, protocols split into two communication **models**:

- **Client-Server Model** — one side (the client) always **initiates** the conversation; the other side (the server) only **responds**. Like a customer walking up to a shop counter — the customer speaks first, the shopkeeper replies. Examples: HTTP, FTP, SMTP/IMAP.
- **Peer-to-Peer (P2P) Model** — any participant can talk directly to any other participant, with no strict "always ask first" hierarchy. Example: WebRTC (video calling).

A common point of confusion: **WebSocket looks peer-to-peer because both sides can send messages at will, but it is still technically a client-server protocol** — it's just a client-server connection that stays open and allows **bidirectional** communication over that single persistent connection, instead of the client having to ask a new question every time.

## 📊 Visualize It

**Client-Server (HTTP) vs. WebSocket vs. Peer-to-Peer (WebRTC):**

```
CLIENT-SERVER (classic HTTP)          WEBSOCKET (still client-server,        PEER-TO-PEER (WebRTC)
                                       but persistent + bidirectional)
Client -----request----> Server        Client <==persistent conn==> Server    Peer A <----direct----> Peer B
Client <----response---- Server        Client <---- server push ---- Server   Peer A <----direct----> Peer C
(new request needed                    (server can send without           (no central server relays
 for every interaction;                 client asking first — good for      the actual media/data;
 connection closes after)               chat apps, live notifications)      server only helps set up
                                                                             the connection)
```

**TCP (reliable, ordered) vs. UDP (fast, best-effort):**

```
TCP                                          UDP
Client ---SYN---> Server                    Client ---datagram 1---> Server
Client <--ACK/SYN- Server   (handshake,      Client ---datagram 2---> Server  (no handshake,
Client ---ACK----> Server    connection        (packet 2 arrives      no acknowledgment,
                              established)       BEFORE packet 1 —     no guaranteed order —
Client ---pkt#1--> Server                        that's OK for UDP)    packets can be dropped
Client <--ACK#1---- Server  (each packet                                or arrive out of order)
Client ---pkt#2--> Server    acknowledged;
Client <--ACK#2---- Server   lost packets
                              are resent)
```

## 🔧 Deep Dive: How It Actually Works

### The Application Layer: Client-Server Protocols

**HTTP (HyperText Transfer Protocol):**
- **Connection-oriented** — a connection is established for the interaction.
- Used to access **web pages**; supports navigating ("jumping") from one page/resource to another.
- **HTTPS** = HTTP + a security layer (TLS/SSL) — indicated by the padlock/"https" prefix, meaning the transfer is encrypted and secure.

**FTP (File Transfer Protocol):**
- Used for transferring files between systems.
- Maintains **two separate connections**:
  - **Control connection** — stays active/persistent for the entire session (handles commands).
  - **Data connection** — created only when needed for an actual file transfer, and can be disconnected afterward.

**SMTP & IMAP (Email protocols):**
- **SMTP (Simple Mail Transfer Protocol)** — used for **sending** email.
- **IMAP (Internet Message Access Protocol)** — used for **receiving/reading** email; unlike the older POP3 approach (where reading an email downloads and *deletes* it from the server), IMAP keeps mail synced on the server so it can be read from **multiple devices**.
- Under the hood, email systems use an **MTA (Message Transfer Agent)**: the sender's MTA hands off the message, and it's ultimately delivered to the recipient's mailbox — this is itself a client-server relationship (mail client ↔ mail server).

### Why Messaging Apps Need WebSocket, Not Plain HTTP

In a pure client-server HTTP model, the **client must always initiate**. For a messaging app like WhatsApp, if you only had HTTP, the client would have to continuously **poll** the server ("Do I have a new message? Do I have a new message? Do I have a new message?") — wasteful and slow.

**WebSocket** solves this: it establishes **one persistent, bidirectional connection**, so the **server can push** a new message to the client the instant it arrives, without the client having to keep asking. This is why messaging/chat applications are built on WebSocket rather than plain request-response HTTP.

### Why Video Calling / Live Streaming Needs Peer-to-Peer (WebRTC)

For real-time video/audio (video calling, live streaming), routing all media data through a central server adds latency and server load. **WebRTC** enables **direct peer-to-peer** communication between the participating devices for the actual media stream (a server may still help with initial connection setup/signaling, but the bulk data path is direct peer-to-peer).

### The Transport Layer: TCP vs. UDP

**TCP (Transmission Control Protocol):**
- **Connection-oriented** — a virtual connection is established and maintained before data flows (handshake).
- Data is broken into **packets** that are **sequenced** (numbered) so they can be reassembled in the correct order at the destination, even if they don't arrive in that order.
- Every packet requires an **acknowledgment (ACK)**; if an ACK isn't received for a packet, that packet is **retransmitted**.
- Reliable and ordered, but this overhead (handshake + acknowledgments + ordering) makes it **slower** compared to UDP.

**UDP (User Datagram Protocol):**
- **Connectionless** — no persistent virtual connection is maintained.
- Data is sent as independent **datagrams**; there is **no sequencing guarantee** and **no acknowledgment mechanism** — packets can arrive out of order, or not arrive at all, and UDP doesn't retry.
- Because it skips all that overhead, UDP is **faster**, making it the right choice when speed matters more than perfect reliability — e.g., **live video streaming** and **video calling**, where a dropped or slightly out-of-order frame is preferable to introducing lag by waiting for retransmission.

### Choosing the Right Combination (Design Decision Framework)

| Use case | Application layer | Transport layer | Why |
|---|---|---|---|
| Regular website / API | HTTP(S) | TCP | Need reliability and correct ordering of data; no strict need for server-initiated push. |
| Messaging app (WhatsApp/Telegram) | WebSocket | TCP | Need persistent bidirectional connection so server can push messages instantly; still need reliable delivery of each message. |
| Video calling / live streaming | WebRTC (P2P) | UDP | Need lowest possible latency; occasional dropped/late frames are acceptable, waiting for retransmission is not. |
| File transfer | FTP | TCP | File integrity matters — can't afford missing/corrupted bytes. |

## 🔥 Real Production Incident & Fix

**What broke:** An engineering team building a chat feature initially implemented "real-time" notifications using **HTTP short-polling** — the client called `GET /messages/new` every 2 seconds. It worked fine in the demo with 10 test users.

**How it was detected:** After rolling out to ~50,000 concurrent users, the on-call team was paged for API gateway CPU saturation and a spike in database read replica latency. Dashboards (Grafana + request-rate metrics) showed that the `/messages/new` endpoint alone accounted for over 70% of total API traffic, almost entirely returning **empty responses** (no new messages), i.e., wasted polling.

**Root cause:** Client-server HTTP fundamentally requires the client to initiate every interaction. At scale, polling every 2 seconds per user turns into tens of thousands of near-useless requests per second, overwhelming the backend with load that carries almost no actual information.

**The fix:** The team migrated the "new message" delivery path to **WebSocket**. Instead of clients repeatedly asking "anything new?", each client opened one persistent WebSocket connection, and the server **pushed** new messages the moment they were produced (fed from the message queue). This collapsed the constant polling traffic into an event-driven push model, cutting the relevant API traffic to a small fraction of its former volume and eliminating the wasted empty-response calls entirely.

```
BEFORE (HTTP polling):                       AFTER (WebSocket push):
Client --GET /new?----> Server (empty)       Client <==persistent WS conn==> Server
Client --GET /new?----> Server (empty)       (server pushes message the instant
Client --GET /new?----> Server (empty)        it's available — zero wasted requests)
   ... x thousands of users, every 2 sec
   = massive wasted load
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: If WebSocket allows both sides to send messages freely, why do we still call it "client-server" and not peer-to-peer?**
Because the connection is still established by a client to a specific server (or server cluster) — the server is a distinct, addressable endpoint that clients connect *to*, whereas true peer-to-peer means arbitrary participants can establish direct connections to each other without a fixed server role; WebSocket just removes the "client must always ask first" restriction while keeping the underlying client-server relationship.

**Q2: Why would you ever use UDP instead of TCP if UDP can lose data?**
For real-time media (video calls, live streams), a lost or late packet just causes a brief visual/audio glitch that's often imperceptible, but TCP's retransmission-and-reordering guarantee would instead cause the entire stream to stall waiting for a missing packet, introducing lag that's much worse for the user experience than a dropped frame.

**Q3: How does IMAP differ from POP3, and why does that matter for multi-device usage?**
POP3 typically downloads mail to a single device and removes it from the server, so reading the same mailbox from a second device would show it as missing; IMAP keeps the mail synced on the server and just reflects read/unread state to each connected client, so the same mailbox stays consistent across multiple devices.

**Q4: Why does FTP maintain two separate connections (control and data) instead of one?**
Separating them lets the control connection remain lightweight and always available for issuing commands (list files, navigate directories) without being tied up by the potentially large and long-running data transfers, and it lets data connections be opened/closed per-transfer without disrupting the ongoing control session.

**Q5: For a video-calling product, would you use WebRTC end-to-end, or is a server still involved?**
Media typically flows directly peer-to-peer via WebRTC once the connection is established, but a server (often called a signaling server) is still needed for the initial setup — exchanging connection metadata like network addresses and codecs (and for cases where direct peer connection isn't possible due to NAT/firewall issues, a relay server like a TURN server may be used) — so it's peer-to-peer for the media path but not necessarily 100% serverless for setup.

**Q6: Is HTTPS a separate protocol from HTTP at the transport layer?**
No — HTTPS is HTTP running over an encrypted transport (TLS/SSL) layered on top of TCP; the application-layer semantics (requests, responses, methods, status codes) are the same as HTTP, the difference is that the entire exchange is encrypted so it can't be read or tampered with by anyone intercepting the network traffic.

## 🔑 Key Takeaway

Choose your application-layer protocol based on the **interaction pattern** you need (simple request/response → HTTP, persistent bidirectional push → WebSocket, direct low-latency media → WebRTC/P2P) and your transport-layer protocol based on whether you need **guaranteed reliable ordering** (TCP) or **raw speed with tolerable loss** (UDP) — the wrong combination is one of the most common root causes of scalability and latency problems in real systems.
