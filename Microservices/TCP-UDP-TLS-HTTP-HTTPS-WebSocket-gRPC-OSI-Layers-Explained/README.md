# PAGE 1 - TCP, UDP, TLS, HTTP, HTTPS, WebSocket, gRPC | OSI Layers Explained
Purpose: Give a beginner-friendly but interview-strong way to explain protocol choices in system design rounds.

Scenario:
You are designing a food delivery system. Home feed, checkout, chat, and live tracking all run together. Interviewer asks: which protocol where, and why?

Interview line to speak:
I map protocols to traffic shape, not buzzwords: HTTPS for secure request-response, WebSocket or SSE for real-time updates, gRPC for internal service RPC, and UDP/QUIC for latency-first streaming.

---

# PAGE 2 - Rapid Answer Script (2-3 Minute Spoken Answer)

Scenario:
Interviewer: Explain HTTP, HTTPS, WebSocket, gRPC, TCP, UDP, TLS, and where OSI layers matter in design.

Interview script:
In system design, I focus mainly on OSI Layer 7, 4, and 3. Layer 7 is application protocols like HTTP, HTTPS, WebSocket, and gRPC. Layer 4 is TCP or UDP transport. Layer 3 is IP routing.

HTTP is request-response and easy to integrate. HTTPS is HTTP over TLS, so it adds encryption, integrity, and server identity checks. For internet traffic, HTTPS should be default.

WebSocket is for long-lived, bidirectional, low-latency communication like chat and live order tracking. It usually starts as HTTP and upgrades to WebSocket.

gRPC is ideal for internal microservice communication. It uses Protobuf, which is compact and fast, and supports unary and streaming calls well.

At transport level, TCP gives reliable, ordered delivery, so I use it for business-critical paths like payments and order placement. UDP is lower overhead and lower latency but does not guarantee delivery, so I use it for media and telemetry-like streams where occasional packet loss is acceptable.

TLS is the security layer for encrypted transport. QUIC uses UDP but adds reliability and encryption features, and HTTP/3 runs over QUIC to reduce latency on unstable networks.

Final rule: correctness-first protocols for money and state transitions, latency-first protocols for live experiences.

---

# PAGE 3 - Glossary (Simple + Real Example)

Scenario:
Swiggy-like app: login, place order, live rider tracking, support chat.

Interview line to speak:
I explain every term with one real production use case so decisions feel concrete.

| Term | Simple Definition | Real Production Example |
|---|---|---|
| OSI Layer 7 | Application communication protocol layer | REST API between mobile app and backend |
| OSI Layer 4 | Transport layer for delivery behavior | TCP for checkout API |
| OSI Layer 3 | Network routing layer with IP | Router sends packets to service IP |
| HTTP | Basic request-response web protocol | GET cart data |
| HTTPS | HTTP secured with TLS | Login, checkout, payment confirmation |
| TLS | Encryption + identity + integrity for transport | Browser verifies certificate before secure session |
| WebSocket | Persistent two-way full-duplex channel | Real-time chat and rider location updates |
| gRPC | RPC framework over HTTP/2 with Protobuf | Order service calling inventory service |
| TCP | Reliable ordered byte stream | Payment authorization flow |
| UDP | Fast connectionless packet transport | Voice/video packets or telemetry bursts |
| QUIC | Secure, low-latency transport over UDP | HTTP/3 for mobile users with flaky network |
| SSE | Server-to-client streaming events | Stock ticker updates in browser |

Memory anchor:
- HTTP/HTTPS = courier with receipt
- WebSocket = open phone call
- gRPC = internal express lane
- TCP = guaranteed parcel delivery
- UDP = fast throw-and-go packets

---

# PAGE 4 - Decision Framework

Scenario:
One app needs checkout correctness and live UX together.

Interview line to speak:
I decide protocol with five filters: direction, reliability, latency, security, and client compatibility.

Step-by-step framework:
1. Is traffic internet-facing or sensitive?
- Yes: use HTTPS (TLS mandatory).

2. Is communication request-response only?
- Yes: REST/HTTP(S) or gRPC unary.

3. Is communication real-time and bidirectional?
- Yes: WebSocket.
- No, server push only: SSE.

4. Is strict ordering and guaranteed delivery required?
- Yes: TCP-based protocols.
- No, low-latency is more important: UDP/QUIC path can fit.

5. Is this browser/public API or internal mesh?
- Browser/public: REST over HTTPS is easiest.
- Internal high-throughput services: gRPC is often better.

Hard conditions (no vague "it depends"):
- Payment/order write path: TCP + TLS + idempotency.
- Live map pings every second: WebSocket or UDP/QUIC telemetry.
- External partner integration: HTTPS REST first for compatibility.

Quick visual anchors for new learners:

Diagram A: OSI layers used in system design interviews
```text
Layer 7 (Application): HTTP, HTTPS, WebSocket, gRPC, SSE
Layer 6 (Presentation): TLS encryption context (practical view)
Layer 5 (Session): connection/session behavior
Layer 4 (Transport): TCP / UDP / QUIC transport behavior
Layer 3 (Network): IP routing (IPv4/IPv6)

Design focus for interviews: Layer 7 + Layer 4 + Layer 3
```

Diagram B: HTTP -> TLS -> HTTPS flow
```text
Client                     Server
	| ---- TCP connect -----> |
	| <--- TCP ready -------- |
	| ---- TLS hello -------> |
	| <--- cert + keys ------ |
	| ---- TLS established -> |
	| ---- HTTPS request ---> |
	| <--- HTTPS response --- |
```

Diagram C: Traffic-shape comparison at a glance
```text
REST/HTTP:
Client -> Request -> Server -> Response -> Client

WebSocket:
Client <========== persistent two-way channel ==========> Server

gRPC (internal):
Service A -> compact binary RPC -> Service B
Service B -> typed response -> Service A
```

---

# PAGE 5 - Category-by-Category Comparison Table

Scenario:
E-commerce flash sale: heavy read traffic + critical checkout.

Interview line to speak:
I compare protocols by workload category, not by popularity.

| Category | Primary Need | Best Choice | Alternate | Why |
|---|---|---|---|---|
| Public APIs | Compatibility + security | HTTPS REST | HTTPS GraphQL | Broad client/tool support |
| Internal sync RPC | Throughput + strict schema | gRPC | REST JSON | Smaller payload, codegen, faster calls |
| Real-time two-way | Full duplex low latency | WebSocket | gRPC streaming | Persistent channel both directions |
| Real-time one-way push | Simplicity | SSE | WebSocket | Easy for browser server-push |
| Critical transactions | Reliability + auditability | TCP + TLS | gRPC mTLS | Ordered guaranteed delivery |
| Media-like stream | Lowest latency | UDP/QUIC | TCP | Drops tolerated for freshness |

---

# PAGE 6 - Top 2 Technologies Per Category (When to Choose / Not Choose)

Scenario:
Interviewer asks concrete stack, not abstract protocol names.

Interview line to speak:
I always give two options with clear choose and avoid boundaries.

## A) Public API
1. Spring Boot REST over HTTPS
- Choose when: external consumers, browser/mobile clients, fast onboarding.
- Do not choose when: internal high-QPS mesh where JSON overhead is expensive.

2. Spring GraphQL over HTTPS
- Choose when: frontend needs field-level flexibility and aggregate reads.
- Do not choose when: team cannot enforce query governance and cost limits.

## B) Internal Service Communication
1. gRPC (grpc-java + Protobuf)
- Choose when: strict contracts, high throughput, low latency, streaming.
- Do not choose when: direct browser access is required without gateway translation.

2. REST JSON (Spring MVC/WebFlux)
- Choose when: debugging simplicity and broad team familiarity matter most.
- Do not choose when: payload efficiency and p99 latency are top priorities.

## C) Real-Time Experience
1. Spring WebSocket (STOMP optional)
- Choose when: chat, collaborative editing, live status feedback loops.
- Do not choose when: updates are infrequent and simple polling is enough.

2. SSE (EventSource)
- Choose when: one-way updates like progress bars and market tickers.
- Do not choose when: client must frequently push events upstream.

## D) Low-Latency Transport
1. HTTP/3 over QUIC
- Choose when: mobile users, lossy networks, many reconnects.
- Do not choose when: legacy infra lacks HTTP/3 support.

2. Raw UDP with app-level controls
- Choose when: live media/telemetry where freshness beats perfect delivery.
- Do not choose when: financial correctness and strict ordering are required.

---

# PAGE 7 - End-to-End Architecture View (Plain Text Diagrams)

Scenario:
Order placement + live tracking + internal microservices.

Interview line to speak:
I split correctness flows and real-time flows so each gets the right protocol.

Diagram 1: Full stack protocol map
```text
[Mobile/Web]
		|
		| HTTPS (REST/GraphQL)
		v
[API Gateway/BFF]
		|------------------------------|
		|                              |
		| gRPC (sync internal RPC)     | WebSocket/SSE (real-time push)
		v                              v
[Order Service] <----Kafka----> [Tracking Service]
		|
		| gRPC
		v
[Inventory Service] ---> [Postgres/Redis]
```

Diagram 2: Secure transaction path
```text
Client -> HTTPS(TLS) -> Payment API -> gRPC(mTLS) -> Fraud Service
			-> Ledger Service -> DB Commit -> Event Outbox -> Notification
```

Diagram 3: Live location path
```text
Rider App --(UDP/QUIC telemetry)--> Edge Ingest
Edge Ingest --(event stream)-------> Tracking Engine
Tracking Engine --(WebSocket)------> Customer App
```

---

# PAGE 8 - Capacity Estimation Mini-Framework (With Formulas)

Scenario:
You need to justify whether REST JSON is enough or gRPC is required internally.

Interview line to speak:
I estimate request volume, payload cost, and connection model before finalizing protocols.

1. Estimate QPS

Formula:
QPS = Total Daily Requests / 86400

Peak QPS = Average QPS x Peak Factor

Example:
- Daily requests = 900,000,000
- Average QPS = 900,000,000 / 86,400 ≈ 10,417
- Peak factor = 5
- Peak QPS ≈ 52,085

2. Estimate bandwidth

Formula:
Bandwidth (bytes/s) = QPS x Avg Payload (bytes)

Example:
- Avg payload = 2.5 KB
- Bandwidth ≈ 52,085 x 2.5 KB ≈ 130 MB/s (before protocol overhead)

3. Estimate persistent WebSocket load

Formula:
Concurrent connections = Peak active users x Real-time adoption %

Example:
- Peak active = 1,200,000
- Real-time users = 25%
- Concurrent connections = 300,000

4. Compare JSON vs Protobuf rough savings

Formula:
Savings % = (JSON size - Protobuf size) / JSON size x 100

Example:
- JSON 1.0 KB, Protobuf 0.42 KB
- Savings ≈ 58%

5. Latency budget split (p99)

Example target: p99 <= 250 ms
- Edge and auth: 60 ms
- Service chain: 90 ms
- DB/cache: 70 ms
- Buffer: 30 ms

---

# PAGE 9 - Interview Scripts (Ready to Speak)

Scenario:
Interviewer asks why multiple protocols in one architecture.

Interview line to speak:
I avoid one-size-fits-all and optimize by path criticality.

Script A: Why not just REST for everything?
REST is excellent for public compatibility, but high-volume internal calls suffer from larger JSON payloads and repeated parse overhead. I keep REST at boundaries and use gRPC on hot internal paths.

Script B: When WebSocket over polling?
If updates are frequent and freshness matters, polling wastes bandwidth and adds latency. WebSocket pushes updates immediately over one persistent channel.

Script C: TCP vs UDP in one line?
TCP for guaranteed ordered business data; UDP for low-latency streams where occasional loss is acceptable.

Script D: Why HTTPS default?
Because TLS protects confidentiality, integrity, and server identity. Without it, credentials and business data can be intercepted.

---

# PAGE 10 - Senior Trap Questions with Strong Model Answers

Scenario:
Panel pushes edge cases to test practical maturity.

Interview line to speak:
I answer traps with conditions, failure modes, and operational trade-offs.

1. Trap: gRPC is always better than REST.
Strong answer:
Not always. gRPC is superior for internal high-throughput contracts, but REST is often better for public APIs, partner adoption, browser compatibility, and simpler debugging.

2. Trap: Use WebSocket for all APIs to reduce latency.
Strong answer:
WebSocket adds stateful connection management and scaling complexity. For normal CRUD, HTTPS request-response is simpler and more cost-efficient.

3. Trap: UDP is unreliable so it is useless.
Strong answer:
UDP is valuable for real-time workloads where stale data is worse than dropped data, such as voice/video and telemetry. Reliability can be added selectively at app layer.

4. Trap: Internal traffic need not be encrypted.
Strong answer:
In zero-trust and compliance-focused systems, east-west encryption with mTLS is required to prevent lateral movement and data leakage.

5. Trap: HTTP/3 makes TCP obsolete.
Strong answer:
HTTP/3 over QUIC helps many internet paths, but TCP remains essential across many protocols, environments, and legacy systems.

---

# PAGE 11 - What Not to Say

Scenario:
Candidate loses confidence marks by giving vague or absolute lines.

Interview line to speak:
I avoid trendy one-liners and always tie protocol to workload and risk.

Avoid these:
- "We should use WebSocket because it is modern."
- "gRPC is fastest so I use it everywhere."
- "UDP is bad because packets can drop."
- "We can add TLS later."
- "It depends" without conditions.

Say this instead:
- "I use WebSocket only where low-latency bidirectional updates are product-critical."
- "I use gRPC for internal hot paths; REST for public and partner-friendly APIs."
- "UDP is intentional for real-time streams where freshness beats strict delivery."
- "TLS is baseline security, not optional hardening."
- "For this workload, I choose X because Y constraints matter most."

Memory anchor:
Problem-first answer, not protocol-first answer.

---

# PAGE 12 - Key Numbers to Memorize

Scenario:
Interviewer checks if your trade-offs are grounded.

Interview line to speak:
I use directional numbers to justify design choices quickly.

- IPv4 address space is about 4.3 billion.
- IPv6 address space is effectively massive for foreseeable internet scale.
- Persistent connections can hit file descriptor and memory limits before CPU limits.
- JSON is typically larger than Protobuf for structured service messages.
- p99 latency is a better production KPI than average latency for UX-critical APIs.
- TLS and handshake overhead are usually worth the security gain for internet traffic.

---

# PAGE 13 - Whiteboard Draw Order

Scenario:
40-minute interview: you need structure under time pressure.

Interview line to speak:
I draw from user journey to protocol mapping to reliability controls.

Draw order:
1. User channels
- Mobile app
- Web app
- Partner API

2. Entry layer
- CDN/WAF
- API Gateway or BFF

3. Protocol mapping labels
- HTTPS for edge calls
- WebSocket/SSE for real-time
- gRPC for internal synchronous calls
- Event bus for async fan-out

4. Core services and storage
- Order, payment, inventory, tracking
- DB + cache

5. Reliability and security annotations
- Idempotency on writes
- Retries with backoff
- TLS/mTLS boundaries

Whiteboard mini-map:
```text
Users -> HTTPS -> Gateway
								 |-> REST/GraphQL (public APIs)
								 |-> gRPC (internal calls)
								 |-> Kafka (async)
Tracking -> WebSocket/SSE -> Users
Critical path = TCP + TLS + idempotency
Live path = low latency + stale-drop strategy
```

Beginner mini draw (30-second version):
```text
Public API = HTTPS
Real-time = WebSocket/SSE
Internal hot path = gRPC
Money path = TCP reliability first
```

---

# PAGE 14 - How to Adapt This Guide for Any Company

Scenario:
Same protocol fundamentals, different business constraints by domain.

Interview line to speak:
I customize protocol decisions by compliance pressure, user behavior, and integration needs.

## Fintech
- Priority: correctness, audit, security.
- Typical choice:
	- HTTPS + TLS everywhere.
	- TCP for transaction paths.
	- gRPC internal for low-latency risk/fraud checks.
- Example:
	- UPI transfer confirmation uses HTTPS/TCP with idempotency key and replay protection.

## E-commerce
- Priority: checkout correctness + promotional real-time UX.
- Typical choice:
	- HTTPS REST for product/cart/checkout APIs.
	- WebSocket/SSE for stock countdown and order status.
	- gRPC between order and inventory services.
- Example:
	- Flash sale stock updates pushed via SSE; final buy call is HTTPS transactional.

## Social
- Priority: fanout scale and responsiveness.
- Typical choice:
	- WebSocket for chat/presence.
	- HTTPS for feed CRUD and media metadata.
	- gRPC for internal ranking and graph service calls.
- Example:
	- Typing indicator favors low latency; message send path uses durable backend flow.

## SaaS (B2B)
- Priority: partner integration, predictable operations, tenant isolation.
- Typical choice:
	- REST-first public APIs.
	- gRPC for internal microservice mesh.
	- SSE for dashboard progress streams.
- Example:
	- Enterprise report generation sends progress events to browser via SSE.

---

# PAGE 15 - Common Follow-up Questions

Scenario:
Interviewer goes deeper after your main protocol explanation.

Interview line to speak:
I answer follow-ups with one risk and one mitigation.

1. How do you secure WebSocket?
- Use WSS, token validation at upgrade, heartbeat, origin checks, and server-side session expiry.

2. How do you handle WebSocket disconnect storms on mobile?
- Add jittered exponential reconnect, backpressure, connection limits, and graceful fallback to SSE/polling.

3. How do you version gRPC and REST safely?
- Enforce backward-compatible schema changes, additive fields, contract testing, and sunset timelines.

4. How do you avoid duplicate order creation on retries?
- Use idempotency keys, dedupe table/cache with TTL, and transaction boundaries on write path.

5. What metrics prove protocol choice is right?
- p95/p99 latency, error rate, retry rate, dropped events, connection churn, infra cost per 1M requests.

6. Where do QUIC/HTTP3 pilots usually start?
- At edge/CDN first, with A/B rollout and latency-error comparison before broader adoption.

---

# PAGE 16 - Final Quick Revision (One-Page Cheat Sheet)

Purpose: Last 5-minute recap before interview.

Interview line to speak:
I choose protocol by reliability class and traffic shape, then validate with scale and failure modes.

## Fast mapping
- Public APIs: HTTPS REST
- Internal high-throughput: gRPC
- Two-way real-time: WebSocket
- One-way push: SSE
- Latency-first stream: UDP/QUIC
- Money path: TCP + TLS + idempotency

## Golden rules
- Correctness paths first, then optimize for speed.
- Do not use WebSocket where simple HTTPS is enough.
- Keep external interfaces easy to consume.
- Keep internal interfaces efficient and strongly typed.

## Red flags
- UDP for payment or order commit path.
- WebSocket for basic CRUD only.
- Plaintext internal service traffic in regulated systems.
- No reconnect/replay strategy for live channels.

## Formula box
- QPS = Daily Requests / 86400
- Peak QPS = Avg QPS x Peak Factor
- Bandwidth = QPS x Avg Payload
- Concurrent WS = Active Users x Realtime %

## 30-second close
In my design, I use HTTPS for secure external calls, gRPC for efficient internal service communication, and WebSocket or SSE for real-time updates. TCP handles correctness-critical paths, while UDP/QUIC is used only where low latency matters more than perfect delivery. This separation gives reliability for business operations and responsiveness for user experience.
