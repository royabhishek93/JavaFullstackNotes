# Interview Guide: Proxy vs Reverse Proxy (and how they differ from VPN & Load Balancer)

## 🗣️ The Interview Scenario

> "Your company has a fleet of internal developer machines that all need to reach the public internet, and also a public-facing web service behind several backend servers. Someone on your team says 'let's just put a proxy in front of everything.' Explain what a forward proxy and a reverse proxy actually do here, why you might need both, and then tell me: how is a reverse proxy different from a load balancer, and how is a proxy different from a VPN?"

Interviewers ask this because these four concepts (proxy, reverse proxy, VPN, load balancer) look deceptively similar on a whiteboard — a box sitting "in the middle" — and candidates who can't cleanly separate them tend to also struggle explaining CDNs, API gateways, and firewalls later in the interview.

## 🏗️ Architect's Explanation (For a New Developer)

Imagine a small child who wants a chocolate from a shop. Instead of walking up to the shopkeeper directly, the child asks their **mom**. Mom walks to the shop, buys the chocolate, and hands it to the child. The child never talked to the shopkeeper directly — mom acted **on behalf of** the child.

That's exactly what a **proxy server** is: an intermediary that sits between a client and a server and makes requests *on behalf of* the client (or a whole group of clients). Neither side talks to the other directly — everything passes through the proxy.

There are two directions this can point, and the direction is the entire difference:

- **Forward Proxy**: sits in front of a group of **clients** (like an office network) and forwards their requests out to the internet. It protects/represents the **client side**.
- **Reverse Proxy**: sits in front of a group of **servers** and receives all incoming internet requests on their behalf, then forwards them to the right backend server. It protects/represents the **server side**.

Once you internalize "forward protects clients, reverse protects servers," the rest of the topic (VPN, load balancer, firewall comparisons) becomes just listing what *extra* capability each one adds on top of or instead of that core proxy behavior.

## 📊 Visualize It

**Forward Proxy vs Reverse Proxy — direction is everything:**

```
FORWARD PROXY (protects clients):
  Client-1 (172.1.0.1) ─┐
  Client-2 (172.2.0.1) ─┼──► [Forward Proxy] ──► Internet ──► google.com
  Client-3 (172.3.0.1) ─┘         │
                                   uses its OWN ip (192.3.0.1)
                                   when talking to google.com
                                   → server never learns the real client IP

REVERSE PROXY (protects servers):
  Internet Users ──► [Reverse Proxy] ──┬──► Server-1
                                        ├──► Server-2
                                        └──► Server-3
                        │
                        clients only ever see the reverse proxy's IP
                        → attacker (DDoS) can only hit the proxy, not the real servers
```

**CDN as a geographically-distributed reverse proxy:**

```
User in Paris ──► CDN-Paris (cache) ──┐
User in US    ──► CDN-US    (cache) ──┼──► (cache miss only) ──► Origin Server (Singapore)
User in India ──► CDN-India (cache) ──┘
   (each CDN node = a reverse proxy: caches data, reduces latency, absorbs attacks locally)
```

## 🔧 Deep Dive: How It Actually Works

### Forward Proxy — Mechanics & Advantages
A forward proxy sits in front of a closed network / intranet / group of personal computers, and every outbound request passes through it before reaching the internet.

Key mechanism: when Client-1 (IP `172.1.0.1`) requests `google.com`, the **forward proxy substitutes its own IP address** (e.g., `192.3.0.1`) as the source before forwarding to the actual destination server. The destination server only ever learns about the proxy's IP — never the real client's IP.

This substitution unlocks five concrete advantages:
1. **Anonymity** — client IP/location is hidden from the outside world; no server can talk directly to a client.
2. **Grouping of requests** — if multiple clients request the same resource (e.g., `google.com`), the proxy can consolidate/club these into fewer outbound calls.
3. **Access to restricted content** — since the outbound request appears to originate from the proxy's location (e.g., appearing to come from the UK/US instead of India), geographically-blocked content can be bypassed.
4. **Security / access control** — since all client traffic funnels through one point, you can apply centralized rules (e.g., "block facebook.com for all internal clients") at the proxy layer instead of per-machine.
5. **Caching** — the proxy checks its own cache first before making an outbound call; if 100 clients request the same static content, only the first request actually reaches the internet, and subsequent identical requests are served from the proxy's cache.

**Disadvantage:** forward proxies operate at the **application layer**, which means you must configure a separate proxy setup **per application** — there's no single packet-level solution that works for every protocol at once.

### Reverse Proxy — Mechanics & Advantages
A reverse proxy sits in front of a company's server(s) and intercepts **all incoming internet requests** — no request is allowed to reach a backend server directly. The reverse proxy decides which internal server actually handles each request.

Advantages:
1. **Security via IP hiding + DDoS mitigation** — the outside world only knows the reverse proxy's IP, never the real backend server IPs. An attacker attempting a DDoS attack can only hit the reverse proxy layer (which typically has more resources/technology to absorb such attacks), not the actual application servers.
2. **Caching** — same benefit as forward proxy but from the server side: repeated requests for the same data are served from the reverse proxy's cache without hitting the origin server.
3. **Latency reduction** — reverse proxies (like CDN nodes) can be placed geographically close to end users (e.g., one in Paris, one in US, one in India, with the origin server in Singapore) so local users get faster responses, falling back to the origin only on a cache miss.
4. **Load balancing** — a reverse proxy sitting in front of multiple backend servers can distribute incoming traffic across them (e.g., "send some requests to Server-1, some to Server-2, some to Server-3").

**Key fact for interviews:** a **CDN is literally a type of reverse proxy** — this is explicitly called out because it comes up constantly in "design YouTube / design Facebook"-style questions.

### Proxy vs VPN
- Both can provide **IP anonymity**, and a proxy can also do **caching** and **logging**.
- But a **VPN does far more**: it creates an encrypted **VPN tunnel** between a VPN client (on the user's machine) and a VPN server. All traffic is **encrypted** at the client side and **decrypted** at the VPN server side before reaching the destination.
- **The core distinguishing fact:** a plain proxy only masks/relays the IP address — it does **not** encrypt the data in transit. A VPN both masks the IP *and* encrypts the entire data payload through a secure tunnel.

### Proxy vs Load Balancer
- A **reverse proxy CAN act as a load balancer** (load balancing is just one of its capabilities, alongside caching, anonymity, and logging).
- A **load balancer CANNOT act as a full proxy** — it doesn't inherently provide IP anonymity, caching, or logging as core features the way a reverse proxy does.
- **Litmus test:** if you have only **one** backend server, you don't need a load balancer at all — but you might still want a reverse proxy for its caching, anonymity, or logging benefits even with a single server.

### Proxy vs Firewall
- A traditional **firewall works at the packet level** — it inspects packet headers: source/destination IP, source/destination port number — and applies allow/deny rules based on that. This is sometimes called **packet scanning**.
- A **proxy works at the application layer** — it has visibility into the actual data/content of the request, not just header/port metadata, so its rules can be far richer (e.g., blocking based on response content, not just IP/port).
- Modern proxies increasingly blend in firewall-like blocking capabilities, and these are sometimes called "proxy firewalls" — but the fundamental difference remains: **firewall = packet-level filtering; proxy = application-level filtering**, and a proxy must be set up per-application while a packet-level firewall is protocol/application-agnostic.

## 🔥 Real Production Incident & Fix

**What broke:** A company deployed a reverse proxy (NGINX) in front of three backend API servers, intending it to also serve as a simple load balancer. During a marketing campaign, one backend server's disk filled up and it started returning HTTP 500 errors for every request, but the reverse proxy kept routing roughly a third of all traffic to it anyway, causing a third of all user requests to fail.

**How it was detected:** The team's APM dashboard (e.g., Datadog) showed an overall error rate climbing to ~33% — suspiciously close to "1 of 3 servers," which was the first clue. Checking NGINX access logs (`upstream_status` field) confirmed that one specific upstream server was consistently returning 500s while the other two were healthy, yet NGINX kept forwarding requests to it in round-robin fashion regardless.

**Root cause:** The reverse proxy was configured for basic round-robin distribution without **active health checks** on the upstream servers. A reverse proxy acting as a load balancer only helps if it also knows which backend servers are actually healthy — without health checks, it blindly forwards to a dead/broken server exactly as often as to a healthy one.

**The fix:** The team added active health check probes (a `/health` endpoint polled every 5 seconds) to the NGINX upstream configuration, so unhealthy servers are automatically removed from the rotation until they recover. They also added a circuit-breaker-style `max_fails`/`fail_timeout` setting so a server returning errors gets temporarily excluded after a few consecutive failures instead of waiting for a full health-check cycle.

```
BEFORE (no health checks):                    AFTER (active health checks):
Client ─► Reverse Proxy ─┬─► Server-1 (OK)     Client ─► Reverse Proxy ─┬─► Server-1 (OK)
                         ├─► Server-2 (500!)✖                          ├─► Server-2 (marked DOWN, skipped)
                         └─► Server-3 (OK)                              └─► Server-3 (OK)
   ~33% of all requests fail                      100% of requests land on healthy servers
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Can a single system be both a forward proxy and a reverse proxy?**
Not for the same traffic flow — the classification depends entirely on which side (client or server) the proxy is protecting/representing for a given request. However, a single physical/logical deployment could be configured to act as a forward proxy for one network segment and a reverse proxy for another, since the distinction is about the direction of protection, not the software itself.

**Q2: Why can't you just use one proxy setup for all your applications (like you can with a firewall)?**
Because a proxy operates at the application layer and needs to understand and potentially rewrite headers/payloads relevant to *that specific application's protocol* — a proxy tuned for HTTP won't correctly handle a different application-layer protocol without separate configuration, unlike a packet-level firewall which filters based on IP/port regardless of the application protocol.

**Q3: If a reverse proxy caches responses, how do you avoid serving stale data after the origin server updates?**
You need a cache invalidation strategy — common approaches include setting appropriate `Cache-Control`/`TTL` headers so cached entries expire automatically, or explicitly purging/invalidating the reverse proxy's cache when the origin data changes (e.g., via a cache-busting API call or versioned URLs).

**Q4: Does using a proxy break client-IP-based rate limiting or logging on the backend?**
Yes — since the destination server only sees the proxy's IP, naive IP-based rate limiting would incorrectly throttle *all* clients behind the proxy as if they were one client. The standard fix is for the proxy to forward the original client IP in a header like `X-Forwarded-For`, and for the backend to use that header instead of the raw connection IP.

**Q5: Why would an attacker prefer to DDoS a reverse-proxy-protected system versus one without a reverse proxy?**
They wouldn't prefer it — that's the point. Without a reverse proxy, an attacker can directly target backend server IPs. With a reverse proxy, the attacker can only reach the proxy's IP; the origin servers' IPs are hidden, so the defense can be concentrated at the highly-resourced proxy/CDN layer rather than needing to harden every backend server individually.

**Q6: Is a VPN a type of proxy?**
Not exactly the same thing, even though both provide IP masking. A VPN's defining, differentiating feature is that it also encrypts the data over a tunnel between client and VPN server — a capability a bare proxy doesn't provide. Think of VPN as "proxy + encryption + a dedicated secure tunnel."

## 🔑 Key Takeaway
Say this out loud: **"Forward proxy protects and represents the client to the outside world; reverse proxy protects and represents the server from the outside world — everything else (VPN's encryption, load balancer's traffic distribution, firewall's packet filtering) is just an additional or alternative capability layered on top of that same core 'sit-in-the-middle' idea."**
