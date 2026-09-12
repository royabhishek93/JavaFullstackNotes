# Communication Patterns — Webhook vs WebSocket vs gRPC vs REST
### Which to use in which system design scenario — Easy English Guide

---

## THE ONE QUESTION THAT DECIDES EVERYTHING

```
Who talks first? And how often?

  "My app asks, other side replies"              → RestTemplate / WebClient / FeignClient / gRPC
  "Other side tells me when something happens"   → Webhook
  "Both sides talk freely, anytime"              → WebSocket
  "Server pushes updates, client just listens"   → SSE
```

---

## PART 1 — WHAT EACH ONE IS (EASY ENGLISH)

---

### RestTemplate — Old telephone (synchronous, blocking)

You call someone. You wait on the line until they answer and reply. You can't do anything else while waiting.

```
Your App ──── HTTP GET /orders/123 ────► Other Service
Your App ◄─── "Here is order 123" ──────  (thread blocked, waiting here doing nothing)
```

**Production use:** Swiggy's order-service calls payment-service to check if payment succeeded. Waits for the response before continuing.

```java
RestTemplate restTemplate = new RestTemplate();
Order order = restTemplate.getForObject("http://order-service/orders/123", Order.class);
// Thread is BLOCKED here until response arrives
```

**Problem:** If 1000 requests come in and payment-service is slow → 1000 threads sitting idle → server runs out of threads → crash.

**Status:** Deprecated in Spring 6. Use WebClient instead.

---

### WebClient — Smart telephone (non-blocking, reactive)

You call someone, leave a message saying "call me back when ready", and go do other work. When they respond, you handle it.

```
Your App ──── HTTP GET /orders/123 ────► Other Service
Your App → goes and handles other requests (NOT blocked)
           ← response arrives later → Your App handles it
```

**Production use:** Swiggy's API gateway calls 5 microservices simultaneously (restaurant, menu, rider, ETA, offers). WebClient fires all 5 at the same time without blocking any thread.

```java
WebClient client = WebClient.create("http://order-service");
Mono<Order> order = client.get()
    .uri("/orders/123")
    .retrieve()
    .bodyToMono(Order.class);
// Thread NOT blocked — goes and handles other requests
```

**Use when:** High-traffic services. Calling multiple APIs in parallel. Spring Boot 3+.

---

### FeignClient — Lazy telephone (declarative, just write an interface)

You don't write any HTTP code at all. You just define WHAT you want to call, and Spring generates all the HTTP code for you.

```java
// You write just this interface:
@FeignClient(name = "payment-service")
public interface PaymentClient {
    @GetMapping("/payments/{orderId}")
    Payment getPayment(@PathVariable String orderId);
}

// You use it like a normal method call:
Payment payment = paymentClient.getPayment("ORD-123");
// Feign generates all HTTP, retry, load-balancing code under the hood
```

**Production use:** Every microservice in Flipkart that calls another internal microservice. Write the interface, Spring handles load balancing, retries, circuit breaker.

**Use when:** Spring Boot microservices calling other internal services. Clean, readable, zero boilerplate.

**Gotcha:** Synchronous (blocking) by default. Fine for most cases. For very high traffic use WebClient.

---

### WebSocket — Phone call that stays open (bidirectional, real-time)

You open a connection and BOTH sides can send messages at ANY time without hanging up and calling again. One persistent connection, messages flow both ways instantly.

```
                    One connection opened at start
                    ┌──────────────────────────────┐
Client              │                              │  Server
  ─────────────────►│ "open connection"            │
                    │                              │
                    │◄── "rider is 2.3 km away" ───│  (server pushes anytime)
                    │◄── "rider is 1.8 km away" ───│  (3 seconds later)
                    │─── "customer: add extra sauce"►│  (client sends anytime)
                    │◄── "restaurant accepted" ─────│
                    └──────────────────────────────┘
                    Connection stays open entire session
```

**Production use:**
- **Swiggy:** Live order tracking — server pushes rider location every 3 seconds to customer's app without app asking each time
- **WhatsApp:** You send a message → instantly appears on the other person's phone
- **Stock trading apps:** Price changes pushed to your screen the moment they happen
- **Multiplayer games:** Every player's moves pushed to all others in real-time

```java
@ServerEndpoint("/tracking/{orderId}")
public class TrackingWebSocket {
    @OnMessage
    public void onMessage(String message, Session session) {
        // received from client
    }

    public void pushToClient(String location) {
        session.getBasicRemote().sendText(location); // server pushes anytime
    }
}
```

**Use when:** Real-time 2-way communication. Chat, live tracking, multiplayer games, live dashboards where user can also interact.

**Cost:** Each open connection = ~50KB server RAM. 100K users = 5GB RAM just for connections. Plan capacity accordingly.

---

### Webhook — Doorbell / automated callback

You tell another service "when something happens at your end, ring my doorbell (call my URL)". You don't keep asking "did it happen yet?" — they call YOU when it's done.

```
Bad approach — polling:
  Your App → "did payment succeed?" → Razorpay
  Your App → "did payment succeed?" → Razorpay  (5 sec later)
  Your App → "did payment succeed?" → Razorpay  (5 sec later)
  ... 100 wasted calls before success ...

Correct approach — webhook:
  1. Your App → tells Razorpay: "when payment succeeds, call https://swiggy.com/webhook/payment"
  2. Customer pays on Razorpay's page
  3. Razorpay ──► POST https://swiggy.com/webhook/payment {"status":"success","orderId":"ORD-123"}
  4. Swiggy processes it immediately
```

**Production use:**
- **Razorpay/Stripe/PayU:** Calls your `/webhook/payment` URL when customer pays
- **GitHub:** Calls your CI/CD URL when code is pushed → triggers Jenkins / GitHub Actions build
- **Twilio:** Calls your URL when SMS delivery is confirmed or failed

**Gotcha:** Always return `200 OK` within 5 seconds (just acknowledge, process async). If you take too long → Razorpay thinks it failed → calls again → duplicate processing. Verify webhook signature to confirm it's genuinely from Razorpay (not a fake POST from attacker).

**Use when:** Event-driven integration with external systems (payment gateways, third-party APIs, CI/CD triggers).

---

### gRPC — Military radio (binary, ultra-fast, strict contract)

Instead of sending human-readable JSON text, you send compressed binary data. 10x smaller payload, 5-10x faster. Both sides must agree on the exact message format upfront using a `.proto` file.

```
REST/JSON:
  {"orderId": "ORD-123", "status": "DELIVERED", "amount": 250.00}
  → 60 bytes of text + JSON parsing CPU overhead

gRPC/Protobuf:
  [binary bytes: 08 01 12 07 4f 52 44 2d 31 32 33]
  → 11 bytes of binary + zero-copy deserialization
  → ~5x less data, ~10x faster processing
```

**Production use:**
- **Flipkart internal services:** inventory-service ↔ order-service ↔ warehouse-service — all gRPC because they handle 100K+ calls/second during Big Billion Days
- **Netflix:** All internal service-to-service calls use gRPC. REST only for mobile/browser clients
- **Uber:** Maps, routing, matching engines — all gRPC for sub-10ms latency requirement

```protobuf
// order.proto — the contract both sides agree on
service OrderService {
    rpc GetOrder (OrderRequest) returns (OrderResponse);
    rpc StreamUpdates (OrderRequest) returns (stream OrderUpdate); // server can stream!
}
message OrderRequest { string order_id = 1; }
message OrderResponse { string status = 1; double amount = 2; }
```

**Use when:** Internal microservice-to-microservice calls where performance matters (>10K calls/sec). NOT for browser/mobile clients (browsers can't use gRPC directly without grpc-web proxy).

**Gotcha:** Hard to debug (binary, not human-readable). Need `grpcurl` or Postman gRPC mode. Both sides must regenerate code every time `.proto` changes.

---

### SSE (Server-Sent Events) — One-way news subscription

Server pushes updates to browser/client, but client can't push back. Like subscribing to a live news feed. Simpler than WebSocket when you only need server → client updates.

```
Browser ──── GET /live-scores ────► Server  (single HTTP request)
Browser ◄──── "Score: 0-1" ────────          (pushed when it happens)
Browser ◄──── "Score: 1-1" ────────          (20 min later)
Browser ◄──── "Full time: 1-1" ────          (90 min later)
```

**Production use:**
- Hotstar: Live cricket score updates on the webpage
- Swiggy: "Restaurant is preparing your order" progress steps pushed to screen
- Flipkart: Order status page — "Packed → Shipped → Out for Delivery" updating live
- Any long-running job: progress bar for "generating your invoice" or "exporting your data"

**vs WebSocket:**
- SSE = server pushes only (simpler, works on HTTP/1.1, browser auto-reconnects on disconnect)
- WebSocket = both sides can send (complex, needs HTTP upgrade)

**Use when:** One-way live updates from server. User just watches, doesn't interact.

---

## PART 2 — WHICH TO USE IN WHICH SYSTEM DESIGN INTERVIEW

---

### Food Delivery (Swiggy/Zomato)

| What needs to happen | Use | Why |
|---------------------|-----|-----|
| Customer sees rider moving on map | **WebSocket** | Rider location pushed every 3s — HTTP polling would create 3 requests/second per user |
| Payment confirmation from Razorpay | **Webhook** | Razorpay calls you when paid — you never poll them |
| Order-service calls restaurant-service | **FeignClient** | Internal microservice, clean interface, low frequency |
| Backend calls payment + ETA + rider at same time | **WebClient** | Non-blocking, all 3 called in parallel |
| Inventory-service ↔ order-service (peak traffic) | **gRPC** | Flash sale: 50K+ calls/sec between internal services |

---

### Chat App (WhatsApp/Slack)

| What needs to happen | Use | Why |
|---------------------|-----|-----|
| Send and receive messages in real-time | **WebSocket** | Both sides send anytime — persistent connection required |
| Typing indicator ("Priya is typing…") | **WebSocket** | Server pushes to all participants instantly |
| Upload a photo/file | **REST (WebClient)** | One-time upload, no need for persistent connection |
| Push notification when app is in background | **Webhook → FCM/APNs** | App is offline — Firebase delivers to device |
| Read receipts (✓✓) | **WebSocket** | Server pushes delivery confirmation instantly |

---

### Ride-Sharing (Uber/Ola)

| What needs to happen | Use | Why |
|---------------------|-----|-----|
| Driver location → customer's map | **WebSocket** | Continuous bidirectional — driver sends GPS, customer receives it |
| "Driver accepted your ride" notification | **WebSocket** | Already connected — push directly, no FCM needed |
| Matching-service calls pricing-service | **gRPC** | Ultra-low latency needed, 100K+ calls/sec |
| Surge pricing broadcast to all drivers | **WebSocket or SSE** | Server pushes only → SSE is simpler |
| Booking history, profile, settings | **REST (WebClient)** | Simple request-response, not real-time |

---

### E-Commerce (Flipkart/Amazon)

| What needs to happen | Use | Why |
|---------------------|-----|-----|
| Product search, browse, add to cart | **REST (WebClient)** | Request-response, no real-time needed |
| Order-service → inventory-service (flash sale) | **gRPC** | 200K calls/sec during Big Billion Days, binary = fast |
| Payment done callback from PayU/Razorpay | **Webhook** | Payment gateway calls your `/webhook/payment` |
| Flash sale: "Only 3 left!" live counter | **WebSocket or SSE** | Inventory count must update on screen in real-time |
| Order status tracking page | **SSE** | Server pushes "Packed → Shipped → Delivered", user just watches |

---

### Stock Broker / Trading App

| What needs to happen | Use | Why |
|---------------------|-----|-----|
| Live price updates on screen | **WebSocket** | Prices change every millisecond, must push instantly to all users |
| Place a buy/sell order | **REST (WebClient)** | One-time request-response, not real-time |
| Order-service → risk-engine → exchange | **gRPC** | < 10ms latency budget — binary protocol mandatory |
| Exchange confirms trade execution | **Webhook** | NSE/BSE calls your backend when trade executes |
| Portfolio P&L updating live | **WebSocket** | Changes every time any holding's price ticks |

---

### OTT Platform (Netflix/Hotstar)

| What needs to happen | Use | Why |
|---------------------|-----|-----|
| Fetch movie list, search, browse | **REST (WebClient)** | Simple request-response, cacheable |
| Video playback — fetch next chunk | **REST (range requests)** | HTTP range headers for streaming segments |
| Live match score overlay on screen | **WebSocket** | Both user interactions + score updates needed |
| Recommendation-service → catalog-service | **gRPC** | ML inference at scale, sub-100ms budget |
| "Still watching?" popup + response | **WebSocket** | Bidirectional interaction needed |

---

### Notification System

| What needs to happen | Use | Why |
|---------------------|-----|-----|
| Push notification (user offline) | **Webhook → FCM → Device** | You call Firebase API; Firebase delivers to phone |
| In-app notification (user is online) | **WebSocket** | Already connected, push directly without FCM |
| Email when order placed | **Webhook → SendGrid** | Your server calls SendGrid API (or SendGrid webhooks delivery status back to you) |
| SMS OTP | **REST → Twilio** | One-time call to Twilio API |

---

### Google Drive / Cloud Storage

| What needs to happen | Use | Why |
|---------------------|-----|-----|
| File upload/download | **REST (multipart/range)** | Standard HTTP, supports chunked upload |
| Real-time collaborative editing (Google Docs) | **WebSocket** | Every keystroke synced to all editors — both ways |
| File processing progress ("converting video…") | **SSE** | Server pushes progress %, user just watches |
| Metadata-service → storage-service | **gRPC** | High frequency internal calls |
| File shared with you notification | **Webhook or WebSocket** | If online: WebSocket push. If offline: email/notification webhook |

---

## PART 3 — THE 30-SECOND DECISION RULE

```
Step 1: External (browser/mobile/third-party) or Internal (microservice)?
  ┌─────────────────────────────────────────────────────────────────────┐
  │ INTERNAL microservice to microservice:                              │
  │   > 10K calls/sec? → gRPC                                          │
  │   < 10K calls/sec? → FeignClient (simple) or WebClient (parallel)  │
  └─────────────────────────────────────────────────────────────────────┘
  ┌─────────────────────────────────────────────────────────────────────┐
  │ EXTERNAL (browser, mobile, third-party):                            │
  │   Does user need to SEE live updates?                               │
  │     YES + user also sends data (chat, tracking with interaction)    │
  │       → WebSocket                                                   │
  │     YES + user just watches (score, progress, price)                │
  │       → SSE                                                         │
  │     NO (normal request-response: search, login, submit form)        │
  │       → REST (WebClient)                                            │
  │   Does a THIRD-PARTY notify YOU when something happens?             │
  │     (payment success, code pushed, SMS delivered)                   │
  │       → Webhook                                                     │
  └─────────────────────────────────────────────────────────────────────┘
```

---

## QUICK REFERENCE CARD

```
RestTemplate   → Deprecated. Old sync HTTP. Don't use in new code.

WebClient      → Modern non-blocking HTTP. Use for all outgoing HTTP calls.
                 Call multiple APIs in parallel. Spring Boot 3+.

FeignClient    → Declarative HTTP. Just write an interface. Best for clean
                 microservice calls. Sync by default.

WebSocket      → Persistent 2-way connection. Use for: chat, live tracking,
                 gaming, any real-time feature where user ALSO sends data.

SSE            → Server pushes only. Simpler than WebSocket. Use for:
                 progress bars, live scores, order status, stock prices
                 where user just watches.

Webhook        → They call you. Use for: payment callbacks, GitHub triggers,
                 any event from an external system.
                 Rule: return 200 OK fast, process async, verify signature.

gRPC           → Binary, fast, strict contract. Use for: internal
                 microservice calls >10K/sec. NOT for browsers.

Decision:
  real-time + 2-way    → WebSocket
  real-time + 1-way    → SSE
  external event       → Webhook
  internal high-speed  → gRPC
  internal normal      → FeignClient or WebClient
  everything else      → WebClient (REST)
```

---

## WHERE THIS APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

| System | Communication patterns that come up |
|--------|-------------------------------------|
| **04 — Chat (WhatsApp)** | WebSocket for messages + typing indicators. Webhook → FCM for offline push. REST for file upload. |
| **06 — UBER/OLA** | WebSocket for driver location. gRPC for matching/pricing engine. Webhook for payment confirmation. |
| **07 — Payment Processing** | Webhook from payment gateway (Razorpay/Stripe). gRPC internal order→payment→ledger. |
| **08 — Food Delivery (Swiggy)** | WebSocket for live tracking. Webhook for payment. FeignClient for internal services. |
| **09 — E-Commerce (Flipkart)** | gRPC for inventory at flash sale scale. Webhook for payment. SSE for order tracking page. |
| **17 — OTT Platform (Netflix)** | REST for content APIs. WebSocket for live events. gRPC for recommendation engine. |
| **19 — Stock Broker** | WebSocket for live prices. gRPC for order→risk→exchange chain. Webhook for trade confirmation. |
| **10 — Cloud Storage (Google Drive)** | REST for upload/download. WebSocket for collaborative editing. SSE for processing progress. |

**Architect's one-liner:**
*"WebSocket when both sides talk in real-time, SSE when only server pushes, Webhook when a third-party calls you on events, gRPC for high-frequency internal calls, and WebClient/FeignClient for everything else."*
