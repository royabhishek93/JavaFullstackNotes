# The N+1 Query Problem — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE | Episode: 18 of 29

## HOOK (0:00–0:30)

[Screen cue: title card — "The N+1 Query Problem" with a spinning loading icon next to "202ms" crossed out and "5ms" in green]

Imagine you're a waiter at a restaurant. A table of 10 guests sits down to order. If you're smart, you walk to the table once, take all 10 orders, and go to the kitchen once. Two trips total.

But imagine a waiter who walks up, asks guest 1 what they want, walks to the kitchen, comes back, asks guest 2, walks to the kitchen again... and does this for all 10 guests. That's **11 trips** instead of 2.

That waiter is your ORM. And this exact mistake — called the N+1 query problem — is quietly costing companies **40x slower APIs**. One hundred orders. One query to fetch them. Then one hundred more queries, one per order, to fetch their items. That's 101 queries where 1 would do. 202 milliseconds instead of 5.

[Screen cue: on-screen counter animating "1 query... 101 queries... 202ms"]

If you've ever shipped an endpoint that got mysteriously slower as your data grew — this is probably why. Let's fix it.

## THE PROBLEM (0:30–2:00)

[Screen cue: code editor showing the JPA entity classes]

Here's the setup. You've got two JPA entities — `Order` and `OrderItem`. An order has a one-to-many relationship to its items, and — sensibly — you've marked it `FetchType.LAZY`. That's the *correct* default, by the way. You don't want Hibernate eagerly loading every order's items every single time you touch an order. Lazy means "only fetch this when someone actually asks for it."

```java
@Entity
public class Order {
    @Id
    private Long id;
    private String status;

    @OneToMany(mappedBy = "order", fetch = FetchType.LAZY)
    private List<OrderItem> items;   // not loaded until accessed
}
```

Now here's the bug — and it looks completely innocent:

```java
List<Order> orders = orderRepository.findAll();   // Query 1

for (Order order : orders) {
    System.out.println(order.getItems());          // Query 2, 3, 4... N+1
}
```

[Screen cue: highlight `order.getItems()` inside the loop with a red pulsing box]

Nothing here screams "danger." You fetch all the orders, then loop through them and print their items. Totally reasonable-looking code. But because `items` is lazy, the *moment* you call `getItems()` inside that loop, Hibernate fires off a brand-new SQL query — for **that one order only**. And it does this again, and again, once per iteration.

Here's the actual SQL Hibernate generates:

```sql
-- Query 1:
SELECT * FROM orders;                              -- returns 100 rows

-- Query 2 (order id=1):
SELECT * FROM order_items WHERE order_id = 1;

-- Query 3 (order id=2):
SELECT * FROM order_items WHERE order_id = 2;

-- ... 97 more queries ...

-- Query 101 (order id=100):
SELECT * FROM order_items WHERE order_id = 100;
```

One query to get the orders. Then **one hundred separate queries**, each fetching items for a single order. 101 total. At roughly 2 milliseconds per round trip — remember, each one is a full network hop to the database — that's 202 milliseconds. If you'd written this as a single JOIN, you'd get identical data in about 5 milliseconds. That's a 40x difference, and it only gets worse as your order count grows.

## THE SOLUTION (2:00–5:00)

[Screen cue: split-screen diagram — left side "101 round trips" with red arrows bouncing back and forth; right side "1 round trip" with a single green arrow]

There are four real fixes here, and which one you reach for depends on the situation.

**Fix 1: JOIN FETCH in JPQL.** This is the most common fix and the one you should default to when you *always* need the items alongside the order.

```java
@Query("SELECT o FROM Order o JOIN FETCH o.items")
List<Order> findAllWithItems();
```

This tells Hibernate: don't be lazy, don't be eager-by-default either — just do a real SQL JOIN, right now, in this one query. One round trip, all the data.

**Fix 2: @EntityGraph.** If you're using Spring Data JPA and don't want to hand-write JPQL, this is cleaner:

```java
@EntityGraph(attributePaths = {"items"})
List<Order> findAll();
```

Same result — Hibernate generates a LEFT JOIN automatically — but you get to keep using the derived query methods you already have, like `findAll()` or `findByStatus()`, without writing custom JPQL for each one.

**Fix 3: @BatchSize.** This one's important for pagination scenarios, and I'll come back to why in the deep dive. Instead of eagerly joining, you tell Hibernate to batch the lazy loads:

```java
@OneToMany(mappedBy = "order", fetch = FetchType.LAZY)
@BatchSize(size = 25)
private List<OrderItem> items;
```

Now, instead of 100 individual `WHERE order_id = ?` queries, Hibernate groups them into batches of 25 using `IN` clauses:

```sql
SELECT * FROM order_items WHERE order_id IN (1,2,3,...,25);
SELECT * FROM order_items WHERE order_id IN (26,...,50);
SELECT * FROM order_items WHERE order_id IN (51,...,75);
SELECT * FROM order_items WHERE order_id IN (76,...,100);
```

**Four queries instead of a hundred.** Not as good as one JOIN, but a massive improvement, and — critically — it doesn't have the side effect that JOIN FETCH has, which we'll get to.

**Fix 4: DTO Projection.** This is the highest-performance option, and it's what I reach for on read-only, high-traffic endpoints:

```java
public record OrderWithItemsDTO(
    Long orderId, String status,
    Long itemId, String productName, Integer quantity) {}

@Query("""
    SELECT new com.example.dto.OrderWithItemsDTO(
        o.id, o.status, oi.id, oi.productName, oi.quantity)
    FROM Order o JOIN o.items oi
    """)
List<OrderWithItemsDTO> findOrdersWithItems();
```

You skip hydrating full entity objects entirely — no Hibernate proxies, no entity tracking overhead — you just get flat rows back, and you group them into a map in Java afterward. For a `GET /orders` endpoint that's purely displaying data, this is as fast as it gets.

[Screen cue: quick-reference table — "JOIN FETCH: 1 query, always-needed relations. @EntityGraph: 1 query, cleaner syntax. @BatchSize: N/batchSize queries, pagination. DTO Projection: 1 query, max perf."]

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)

[Screen cue: mock interview transcript scrolling on screen]

Let's talk about how this actually comes up in an interview, because it's one of the most common "debug this" questions for mid-to-senior backend roles.

**Interviewer:** "Your `/orders` endpoint is slow — 500ms for 100 orders. How do you debug it?"

Here's the answer that separates someone who's actually hit this in production from someone reciting theory:

"First thing I'd check is whether this is an N+1 problem. The classic symptom is *linear growth* — 100 orders takes 500ms, 200 orders takes 1000ms. That proportional relationship between result-set size and latency is the fingerprint of N+1.

I'd turn on Hibernate's SQL logging in development — `spring.jpa.show-sql=true` and `logging.level.org.hibernate.SQL=DEBUG`. If I see 101 queries in the log for a 100-row request, that confirms it immediately."

[Screen cue: terminal log scrolling showing 101 near-identical `SELECT * FROM order_items WHERE order_id = ?` lines]

That diagnostic rule is worth memorizing: **if your endpoint's response time grows linearly with the result set size, it's almost always N+1.** If it grows logarithmically, that's usually a missing index. If it's flat regardless of size, you're in good shape.

Now — this problem isn't unique to Java and Hibernate. Every ORM has this trap, and every ORM has a version of the fix:

- **Django** — naive loop is `orders.each { order.items.all }`, N queries. Fix is `prefetch_related('items')`, which drops it to 2 queries total: one for orders, one `WHERE order_id IN (...)` for all items at once.
- **Ruby on Rails, ActiveRecord** — same pattern, fix is `.includes(:items)`.
- **TypeORM in Node** — accessing `order.items` lazily per row is the bug; fix is passing `{ relations: ['items'] }` to `find()`, or using `leftJoinAndSelect` in a query builder.

The mechanism is identical everywhere: one query for the parent, then a bug that fires one query per row for the child, versus a fix that either joins upfront or batches the child fetch into a single `IN` clause.

[Screen cue: diagram — "Order 1: 3 items, Order 2: 4 items" joined into a 7-row result table]

Now here's the part that trips people up *after* they've applied the fix. JOIN FETCH solves N+1, but it can introduce a **cartesian product**. If Order 1 has 3 items and Order 2 has 4 items, the JOIN result isn't 2 rows — it's 7. Order 1's columns get repeated 3 times, once per item; Order 2's columns repeat 4 times. For 100 orders averaging 10 items each, that's 1,000 rows coming back over the wire instead of 100 — more data transferred than you'd expect, even though it's still just 1 query.

And here's the trap that actually breaks things: **JOIN FETCH plus pagination doesn't work the way you'd expect.** If you try to do `JOIN FETCH` with a `LIMIT`, Hibernate can't apply the limit at the SQL level — because limiting rows in a cartesian-product result set would cut off some order's items halfway through. So Hibernate does something sneaky: it fetches *all* matching rows into memory and then applies the limit in application code. You'll see this exact warning in your logs: **`HHH90003004`**. If you don't know what that means, you'll ship a "paginated" endpoint that's secretly pulling your entire table into memory on every page request.

The fix, when you need pagination: **don't use JOIN FETCH — use @BatchSize instead.** Fetch the parent page with a normal `LIMIT`, then let `@BatchSize` batch-load the children in `IN` clauses afterward. That's precisely why I mentioned Fix 3 earlier as more than "the lesser option" — it's the *correct* choice specifically when pagination is in play.

## REAL WORLD (8:00–9:30)

[Screen cue: three logos/mockups — a social feed UI, a food delivery restaurant list, an e-commerce search grid]

Let's ground this in scale. Think of an Instagram-style feed. A user opens the app, and you load 20 posts. If your ORM lazily fetches each post's author profile separately, that's 21 queries for one feed load — 1 for the posts, 20 for the authors. Fine at small scale. Now picture **1 million concurrent users** refreshing their feed. 1 million requests times 21 queries each is **21 million database queries per second** — versus 1 million if you'd used a single JOIN FETCH or @EntityGraph on the post-author relationship. That's the difference between a database that falls over and one that doesn't.

Now think about a food delivery app — the kind of restaurant listing you'd see in Zomato or Swiggy. You load 50 restaurants for a city. If each restaurant's menu categories are fetched lazily, that's 51 queries per page load, on every single scroll, for every user browsing restaurants during lunch rush. @EntityGraph on the restaurant-categories relationship collapses that to 1 JOIN query — and that's the difference between your listing page holding up under load or your DB collapsing exactly when traffic peaks.

And for e-commerce — a Flipkart-style product search. You return 40 products. If you separately fetch each product's seller info and its aggregate rating, that's **81 queries per search** — 1 for products, 40 for sellers, 40 for ratings. A DTO projection with an explicit JOIN gets all of that in a single round trip, and if you've got a proper covering index on top of it, you skip the heap fetch entirely.

[Screen cue: on-screen stat card — "Instagram feed: 21M queries/sec at 1M users → fixed with JOIN. Zomato/Swiggy listing: 51 queries → 1 with @EntityGraph. Flipkart search: 81 queries → 1 with DTO projection."]

The one-liner I'd leave you with, the kind of thing you say in an architect-level interview: **N+1 happens when you let your ORM drive — the fix is to tell the database what you need upfront with a JOIN, instead of asking it "what's this row's related data?" one row at a time.**

## OUTRO + NEXT EPISODE (9:30–10:00)

[Screen cue: recap bullets fading in — "LAZY is fine. The loop is the bug. JOIN FETCH, @EntityGraph, @BatchSize, DTO projection. Watch for the cartesian product trap with pagination."]

So to recap: lazy loading itself isn't the problem — it's accessing a lazy relationship inside a loop, one row at a time, without telling your ORM to batch or join upfront. Four fixes, one diagnostic rule: linear growth in latency as your result set grows means N+1, every time.

[Screen cue: next-episode teaser card — "Episode 19: Geohash vs Quadtree — Map Partitioning"]

Next episode, we're moving from database queries to geospatial systems — Geohash versus Quadtree for map partitioning, and how apps like Uber and Swiggy figure out which drivers or restaurants are near you without scanning every row on the map. See you there.
