# #65 — Hibernate OSIV Causing Slow Memory Accumulation

> **Category:** Heap Dump Analysis | **Type:** Scenario Q&A | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"Spring Boot app with JPA — heap grows steadily over the course of a day but never OOMs. Restarts fix it temporarily. What do you suspect?"

## 😊 Explain It Simply (for anyone)
Imagine a librarian (a database "Session") who, whenever you ask for one book, keeps the entire aisle open and reserved for you "just in case" you want to browse more, and doesn't close that aisle until you completely leave the library (finish the whole web request) — not just until you finished reading your one book.

If your website design keeps that entire aisle reserved for the full duration of every visitor's page view (this pattern is called "Open Session In View," on by default in Spring Boot), and visitors browse a lot of books during a page load, over the course of a day, more and more aisles are technically "still reserved" behind the scenes even after visitors leave, slowly clogging the library's floor space until a nightly reset (server restart) tidies everything up again.

## 📊 Visualize It
```
Request scope (BAD - OSIV=true default):
  HTTP request starts
    → Hibernate Session opens
    → Controller → Service → lazy-load Entity A, B, C...
    → View renders (session STILL open here)
  HTTP request ends → Session finally closes

  Over a day: sessions/entities pile up faster than GC clears
  Heap: [■□] → [■■□] → [■■■□] → [■■■■□] (slow creep, no crash)
  Restart → heap drops back to [■□]  ← temporary fix only

Fix: spring.jpa.open-in-view=false
  Session closes at end of @Transactional service method,
  not at end of HTTP request → heap stays flat
```

## 🏭 The Real Production Answer (15-YOE Level)

Classic Open Session In View (OSIV) + large entity graph accumulation pattern.

When `spring.jpa.open-in-view=true` (the Spring Boot default), the Hibernate `Session` is held open for the entire HTTP request lifecycle. If:
- You load large entity graphs
- You trigger lazy loading across the entire request chain
- You're using a second-level cache without eviction

...then the Session accumulates objects, and if sessions are pooled or cached beyond request scope, the objects stay referenced.

Diagnosis in heap dump:
- MAT histogram: Look for high count of `org.hibernate.engine.spi.EntityKey` or `org.hibernate.internal.SessionImpl` objects
- Check retention path: Are `SessionImpl` instances reachable from a long-lived scope (application scope, static field, thread-local)?

```java
// Check Spring config
// application.properties
spring.jpa.open-in-view=false  // Correct for APIs — close session at service layer

// Service layer — explicit transaction boundary
@Transactional(readOnly = true)
public List<OrderDTO> getOrders(Long userId) {
    List<Order> orders = orderRepo.findByUserId(userId);
    return orders.stream().map(OrderDTO::from).collect(toList()); // Convert inside tx
    // Session closes when @Transactional method exits
}
```

## 🔑 Key Takeaway
Set `open-in-view=false` and close the Hibernate Session at the transaction boundary, not the HTTP response boundary.
