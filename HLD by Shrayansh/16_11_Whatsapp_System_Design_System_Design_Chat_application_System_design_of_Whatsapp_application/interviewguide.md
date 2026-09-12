# Interview Guide: Design a Chat Application (WhatsApp / Discord / Slack style)

## 🗣️ The Interview Scenario

> "Design a chat application like WhatsApp — support 1:1 messaging, group chats, online/last-seen status, and assume we have around 50 million daily active users. Walk me through why a plain HTTP request/response model breaks down for receiving messages, and how you'd route a message to a specific user across a fleet of chat servers without every server having to know about every other user."

This question is popular precisely because the "obvious" HTTP-based design breaks immediately on the receive path, and the interviewer wants to watch you discover and fix that in real time.

## 🏗️ Architect's Explanation (For a New Developer)

Normal HTTP is like a **customer walking up to a counter and asking a question** — the customer (client) always initiates, and the clerk (server) always responds. That works great for *sending* a message ("here's my message, please deliver it"), but it completely fails for *receiving* one, because the server would need to walk up to the customer's house and hand them something **without being asked** — and HTTP has no built-in way for a server to initiate contact with a client.

**WebSocket** solves this by turning that one-directional counter interaction into a **standing phone line that never hangs up**. Once the handshake happens, both sides can speak whenever they want, and the connection stays open until either side hangs up or the network drops it. This is what lets a chat server "push" an incoming message to a recipient the instant it arrives, instead of the recipient having to keep asking "do you have anything for me yet?"

The second big idea is a **"phone directory" service** (called the User Mapping Service here, functionally a Zookeeper-style coordinator) that tracks which of the many identical chat servers each user is currently connected to. Without it, if User A's message lands on Chat Server 100, that server has no way of knowing whether User B is connected to Chat Server 500, 501, or is offline entirely — the directory is what makes routing across a fleet of servers possible.

## 📊 Visualize It

**Core 1:1 message routing:**

```
User1 --(WebSocket)--> Chat Server 100 --"where is User2?"--> User Mapping Service
                              |                                  (Zookeeper-like)
                              |<--"User2 is on Chat Server 500"---|
                              |
                              +--forward message--> Chat Server 500 --(WebSocket)--> User2
```

**Offline user handling (before/after coming back online):**

```
BEFORE (User2 offline):                    AFTER (User2 logs back in):

User1 sends "hello" -> Chat Server 100     User2 -> Login (HTTP) -> User Mapping Service
  -> asks User Mapping Service for User2      assigns nearest Chat Server (e.g. CS3)
  -> NO entry found (user2 offline)         -> CS3 checks NoSQL DB for User2's
  -> message just persisted to DB,             unread/undelivered messages
     NOT delivered live                     -> pushes "hello" to User2 over new socket
```

## 🔧 Deep Dive: How It Actually Works

### 1. Requirements
- **Functional:** 1:1 send/receive (text first, extensible to images/files), **group** messaging (create groups, send to groups), **last seen / online-offline** status, user login/authentication.
- **Non-functional:** **scalability** (must handle traffic on the order of millions/billions of messages per day, matching what FB Messenger/Discord actually handle), **low latency** (message delivery should feel real-time), **availability** (the service must stay up).

### 2. Back-of-the-envelope math
- Assume **2 billion total users**, **50 million DAU** (daily active users).
- Assume each user sends **10 messages to 4 different people** per day → **40 messages/user/day**.
- Total messages/day: `50,000,000 × 40 = 2,000,000,000` → **~2 billion messages/day**.
- Assume **100 bytes per message** → `2 billion × 100 bytes = 200 GB/day`.
- For a **10-year** chat history retention requirement: `200 GB × 365 × 10` → scales into the **terabyte/petabyte** range, driving the choice of a horizontally-scalable storage layer.

### 3. Why peer-to-peer and plain HTTP don't work
- **Peer-to-peer** (clients messaging each other directly via IP) doesn't scale to 50M DAU and provides no way to maintain chat history centrally — rejected immediately in favor of a **client-server** architecture with a chat server in the middle.
- **HTTP for sending** is fine — the client initiates a "send message" request, and the server processes it like any normal request/response.
- **HTTP for receiving is fundamentally broken** — HTTP requires the *client* to initiate every exchange; the server has no mechanism to push a message to a client that isn't currently asking for one.
- Three candidate fixes are evaluated in order:
  1. **Polling:** client repeatedly asks "is there a message for me?" — server replies "no" most of the time. Each ask/answer opens and closes a full TCP/HTTP connection, wasting huge amounts of server resources for what is usually a "no." Explicitly rejected as not scalable.
  2. **Long polling (a.k.a. "pushing"):** client asks once, and the server **holds the connection open** for a threshold (example used: 1 minute), replying immediately if a message arrives, or replying "no" only once the threshold expires. This cuts the number of round-trips dramatically (one call per minute instead of, say, 100 calls per minute) — but it still ties up a server-side thread/connection **waiting**, which doesn't scale to millions of concurrently-connected users.
  3. **WebSocket:** a **bi-directional, persistent** connection. "Bi-directional" means either side (client or server) can initiate a message once connected. "Persistent" means the connection stays open across many messages and is only closed by an explicit shutdown or a network failure — not after every single exchange. This is the chosen solution, and once WebSocket is in place for receiving, it's used for **sending too** (no need to maintain two different protocols).

### 4. Core 1:1 messaging architecture
- **Client ↔ Chat Server**, connected via **WebSocket** (not HTTP). Multiple chat servers exist (Chat Server 1, 2, ... N) behind this layer.
- **User Mapping Service** (described as functioning like **Zookeeper**, a distributed coordinator): maintains the mapping of `user -> which chat server they're currently connected to` (e.g., "User 1 is connected to Chat Server 100," "User 2 is connected to Chat Server 500").
- **How the mapping gets populated:** when a user comes online (establishes their WebSocket connection, typically right after login over HTTP), the User Mapping Service **assigns them a chat server** — the assignment can be geography-aware (e.g., a user in India gets a chat server nearest to their location).
- **Send flow:** User1 sends "hello, from=User1, to=User2" (the request also carries a **type** field distinguishing 1:1 vs. group) to its own connected chat server (e.g., CS100) over the open WebSocket. CS100 doesn't know where User2 is, so it asks the User Mapping Service, gets back "User2 is on CS101," and forwards the message internally to CS101, which delivers it to User2 over *its* WebSocket connection.

### 5. Choosing the database — NoSQL, and why
- Read operations identified: read a specific chat history, read group member details, read profile info — **no complex/multi-table joins** required for any of these.
- Write operations identified: send message, update profile picture — again simple, non-relational writes.
- A specific low-latency **search** requirement is called out: searching a keyword across potentially millions of historical messages for a heavy chat user needs to be fast even at huge data volume.
- These two properties — **no complex joins needed** + **low-latency search/lookup at huge scale** — are the exact signals (from the companion SQL-vs-NoSQL framework) that point to **NoSQL**, plus the general need for horizontal scalability and high availability. Real systems cited: **Discord and Facebook both use Cassandra** (a column-wise NoSQL DB).
- **Message table schema:** `message_id | from | to | timestamp`.
- **Partitioning:** the **partition key is `(from, to)`** — this pair determines which node a given conversation's data is routed to (the same horizontal-sharding mechanism from the consistent-hashing topic).
- **Ordering:** `message_id` provides ordering **within a single partition** (conversation), since maintaining chat order matters. Because NoSQL has no built-in auto-increment like SQL, a **timestamp-based local ID generator** is used — critically, this does **not** need to be a *global* unique ID generator (like Snowflake), because sequencing only ever needs to be correct *within one partition* — two different partitions can legally reuse the same `message_id` value since they're never compared against each other.

### 6. Offline delivery handling
- If a recipient's chat-server entry is missing from the User Mapping Service (they're offline, or their chat server crashed and the entry was removed), the sender's chat server cannot find a destination — the message is simply **persisted to the NoSQL DB** and delivery stops there (no live push).
- When the recipient later logs back in (HTTP-based login flow), the User Mapping Service assigns them a **new** chat server (again, geography-aware). That new chat server then **checks the DB** for any unread/undelivered messages for that user and pushes them over the freshly-established WebSocket connection.

### 7. Group messaging
- A separate **Group Management Service** (HTTP-based) owns group lifecycle: create, delete, join, add/remove members — with its own DB (could be SQL or NoSQL; no hard dependency either way, since group metadata is small and low-volume compared to messages).
- **Group message table:** `group_id | from | message | time`, with **`group_id` as the partition key** (analogous to `(from,to)` for 1:1) and `message_id` again providing intra-partition ordering.
- **Group send flow:** User1 sends a message to Group1. Their chat server asks the Group Service "who are the members of Group1?" (gets back User1, User2, User3, User4). The chat server then asks the User Mapping Service which chat server *each* of those members (excluding the sender) is connected to, and forwards the message to each of those respective chat servers for delivery.

### 8. Presence (last seen / online-offline)
- A separate **Presence System** tracks liveness independently from the User Mapping Service (deliberately — see the incident below for why they're kept separate).
- Mechanism: the client sends a **heartbeat every ~3 seconds**. The presence system records the last-heartbeat timestamp per user.
- If no heartbeat is received within a **threshold (example: 1 minute)**, the presence system flips that user's status to **offline**.
- **Why a threshold instead of instant online/offline toggling on every connectivity blip:** the walkthrough gives the "train going through a tunnel" scenario — brief connectivity loss (seconds) would otherwise cause the status to flicker online/offline/online repeatedly, which is explicitly called out as a **very bad user experience**. Using a tolerant threshold means brief blips are absorbed and the user is shown as continuously online.

## 🔥 Real Production Incident & Fix

**What broke:** A very large public/broadcast-style group (a "verified account" broadcast channel with millions of members) went viral overnight. Message send latency for *that specific group* spiked into multiple seconds and some sends began timing out, while every other 1:1 chat and small group in the system remained completely normal.

**How it was detected/diagnosed:** On-call pulled per-partition read/write latency metrics from the Cassandra-backed message store (the kind of stats exposed by `nodetool tablestats`/`cfstats`) and found one specific partition receiving vastly more write traffic than any other — a classic **hot partition**. Correlating partition keys with the incident window showed the hot partition corresponded exactly to the viral group's `group_id`.

**Root cause:** The group-message table used **`group_id` as the sole partition key** (exactly as designed above). That's the right choice for the overwhelming majority of groups, which have modest membership and modest message volume — but it silently assumes no single group will ever produce enough message volume to overload one partition/node. The viral broadcast group violated that assumption: every message to that group, no matter how many members needed to receive it, funneled through **one** partition on **one** set of replica nodes, which became a bottleneck.

**The fix:** The team introduced **time-bucketing into the partition key** for high-volume groups — instead of partitioning purely by `group_id`, the key became something like `group_id + time_bucket` (e.g., a new bucket every few minutes), spreading a single group's ongoing message stream across multiple partitions/nodes instead of concentrating it on one. Very large "broadcast" style groups were additionally routed through a separate fan-out/dispatch pipeline rather than the standard group-send path, since the fan-out cost (pushing to millions of members) is a fundamentally different scaling problem than routing the write itself.

```
BEFORE (group_id only as partition key):        AFTER (group_id + time_bucket):

Viral group's ALL messages -> ONE partition      Viral group's messages spread across
  -> node overloaded, high write latency           multiple partitions over time
  -> timeouts for that group only                  -> latency stays flat under viral load
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Why can't polling or long polling scale to WhatsApp-level traffic?**
Polling forces a full connection open/close cycle for every "any messages?" check, and the answer is "no" the vast majority of the time — that's pure wasted server resource at billions-of-messages-per-day scale. Long polling reduces the *number* of round-trips, but each waiting client still ties up a server-side connection/thread for up to the full timeout window, which doesn't scale to millions of simultaneously-connected users either — you need a model (WebSocket) where an open connection costs near-zero server resources while idle.

**Q2: Why WebSocket specifically, and not just a longer long-poll timeout?**
WebSocket gives you a genuinely **persistent, bi-directional** connection — the server can push the instant a message arrives with no polling interval at all, and the same connection serves both sending and receiving, avoiding the need to maintain two separate protocols/paths for one chat session.

**Q3: Why NoSQL for chat history instead of SQL, given you need strict message ordering?**
The read patterns (own chat history, group members, profile data) require no complex joins, and the write/read volume plus low-latency search requirement across huge historical data point straight at NoSQL's strengths (horizontal scale, fast key-based lookups). Ordering is preserved *within* a partition using `message_id` and a partition key of `(from,to)` or `group_id` — you don't need a globally-ordered ID across the whole system, only a locally-ordered one per conversation, which sidesteps NoSQL's lack of a native auto-increment.

**Q4: How would you avoid message loss if a chat server crashes right after receiving a message but before forwarding it?**
The walkthrough's design already persists every message to the NoSQL DB as part of handling it (this is exactly the mechanism used for offline delivery) — so as long as the write to the DB happens before/atomically with acknowledging the sender, a mid-flight chat-server crash loses only the *live push* to the recipient, not the message itself; the recipient picks it up as an "unread message" the next time their assigned chat server checks the DB.

**Q5: How would you scale the User Mapping Service itself, since every message send depends on it?**
Since it's described as functioning like Zookeeper (a distributed coordination service), it should itself be run as a small distributed cluster with its own partitioning of the `user -> chat server` mapping, so no single instance becomes a bottleneck or single point of failure for what is effectively a lookup on the critical path of every message.

**Q6: Why is the Presence system kept separate from the User Mapping Service instead of inferring "online" from having a User Mapping Service entry?**
Superficially you could say "if the User Mapping Service has an entry for a user, they're online" — but this doesn't match real-world connectivity patterns (e.g., users going in and out of tunnels/dead zones), where the underlying WebSocket connection can drop and reconnect within seconds. A dedicated Presence system with a tolerant heartbeat threshold (e.g., 1 minute) absorbs these blips and avoids flickering the user's visible status online/offline every few seconds, which would be a poor experience.

**Q7: How would you design read receipts (delivered/seen ticks)?**
This extends the same message-delivery pipeline: once a message is pushed to the recipient's chat server and acknowledged as received by the client over the WebSocket, that status update ("delivered") is sent back through the same routing path (recipient's chat server → User Mapping Service lookup for sender's chat server → sender's chat server → sender's client) as a small control message, with a further "seen" event fired once the client marks the message as read in its UI.

## 🔑 Key Takeaway

Say this out loud in the interview: **"The core insight of chat system design isn't the database — it's that HTTP's request-response model can't support server-initiated delivery, so you need a persistent WebSocket connection plus a coordination service (like Zookeeper) that tracks which of many chat servers each user is currently attached to, so any server can route a message to any user."**
