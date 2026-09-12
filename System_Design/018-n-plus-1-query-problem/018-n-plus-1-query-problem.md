# The N+1 Query Problem
### ORM Fetches 1 Parent Then N Children Individually — How to Fix

---

## PART 1 — THE STUDENT CONVERSATION

**Imagine you're a waiter at a restaurant.**

A table of 10 guests orders food. Normal approach: walk to the table once, take all 10 orders, go to the kitchen once. Done.

N+1 approach: walk to the table, ask guest 1 what they want, go to the kitchen, come back. Ask guest 2, go to the kitchen, come back. Ask guest 3… Do this 10 times.

You made **11 trips** (1 to take the table order + 10 trips for each guest) instead of 2.

That's exactly what happens with the N+1 query problem.

You query the database for a list of orders (1 query). Then for each order, your ORM automatically queries for that order's items (N queries). If you have 100 orders: 1 + 100 = 101 database queries for what should have been 1 or 2.

---

## PART 2 — THE PROBLEM IN CODE

### The Entity Setup (JPA/Hibernate)

```java
@Entity
public class Order {
    @Id
    private Long id;
    private String status;
    private Long customerId;

    @OneToMany(mappedBy = "order", fetch = FetchType.LAZY)
    private List<OrderItem> items;   // ← LAZY: not loaded until accessed
}

@Entity
public class OrderItem {
    @Id
    private Long id;
    private String productName;
    private Integer quantity;
    private BigDecimal price;

    @ManyToOne
    private Order order;
}
```

### The Bug (looks innocent, isn't)

```java
// Service code:
List<Order> orders = orderRepository.findAll();   // Query 1

for (Order order : orders) {
    System.out.println(order.getItems());          // Query 2, 3, 4... N+1 ← HERE
}
```

### The SQL That Gets Generated

```sql
-- Query 1 (the "1" in N+1):
SELECT * FROM orders;
-- Returns 100 rows

-- Query 2 (for order id=1):
SELECT * FROM order_items WHERE order_id = 1;

-- Query 3 (for order id=2):
SELECT * FROM order_items WHERE order_id = 2;

-- Query 4 (for order id=3):
SELECT * FROM order_items WHERE order_id = 3;

-- ... 97 more queries ...

-- Query 101 (for order id=100):
SELECT * FROM order_items WHERE order_id = 100;

-- Total: 101 queries to the database
-- Each query: ~2ms
-- Total time: 101 * 2ms = 202ms
-- If you used a JOIN: 1 query = ~5ms
```

---

## PART 3 — DIAGRAMS

```
N+1 EXECUTION FLOW:
───────────────────────────────────────────────────────────────

  App Server                              Database
  ──────────                              ────────
  findAll() ──────────────────────────►  SELECT * FROM orders
            ◄──────────────────────────  [100 rows returned]

  loop order[0]:
  getItems() ─────────────────────────►  SELECT * FROM order_items WHERE order_id=1
             ◄─────────────────────────  [3 rows]

  loop order[1]:
  getItems() ─────────────────────────►  SELECT * FROM order_items WHERE order_id=2
             ◄─────────────────────────  [2 rows]

  loop order[2]:
  getItems() ─────────────────────────►  SELECT * FROM order_items WHERE order_id=3
             ◄─────────────────────────  [5 rows]
  ...
  (97 more round trips)

  Total: 101 queries, 101 network round trips
  Total time: ~200ms (at 2ms per query)

─────────────────────────────────────────────────────────────────

FIXED EXECUTION FLOW (JOIN FETCH):
  App Server                              Database
  ──────────                              ────────
  findAllWithItems() ─────────────────►  SELECT o.*, oi.*
                                         FROM orders o
                                         JOIN order_items oi ON oi.order_id = o.id
                     ◄──────────────────  [all rows in one result set]

  Total: 1 query, 1 network round trip
  Total time: ~5ms
```

---

## PART 4 — THE FIXES

### Fix 1: JOIN FETCH (JPQL — most common fix)

```java
// Repository:
@Query("SELECT o FROM Order o JOIN FETCH o.items")
List<Order> findAllWithItems();

// Generated SQL:
// SELECT o.*, oi.*
// FROM orders o
// INNER JOIN order_items oi ON oi.order_id = o.id
// → Single query, all data returned at once
```

### Fix 2: @EntityGraph (Spring Data JPA — cleaner)

```java
@Repository
public interface OrderRepository extends JpaRepository<Order, Long> {

    @EntityGraph(attributePaths = {"items"})
    List<Order> findAll();
    // Hibernate generates a LEFT JOIN automatically
}
```

### Fix 3: Batch Loading (@BatchSize — Hibernate)

```java
@OneToMany(mappedBy = "order", fetch = FetchType.LAZY)
@BatchSize(size = 25)   // ← load items in batches of 25 orders at a time
private List<OrderItem> items;

// Instead of 100 queries, generates:
// SELECT * FROM order_items WHERE order_id IN (1,2,3,...,25)  ← query 1
// SELECT * FROM order_items WHERE order_id IN (26,27,...,50)  ← query 2
// SELECT * FROM order_items WHERE order_id IN (51,...,75)     ← query 3
// SELECT * FROM order_items WHERE order_id IN (76,...,100)    ← query 4
// Total: 4 queries instead of 100 ← still not ideal but much better
```

### Fix 4: DTO Projection (most performant — for read-only endpoints)

```java
// Create a flat DTO:
public record OrderWithItemsDTO(
    Long orderId, String status,
    Long itemId, String productName, Integer quantity
) {}

// Query:
@Query("""
    SELECT new com.example.dto.OrderWithItemsDTO(
        o.id, o.status, oi.id, oi.productName, oi.quantity)
    FROM Order o JOIN o.items oi
    """)
List<OrderWithItemsDTO> findOrdersWithItems();

// Then group in Java:
Map<Long, List<OrderWithItemsDTO>> grouped =
    results.stream().collect(groupingBy(OrderWithItemsDTO::orderId));
```

---

## PART 5 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your API endpoint `/orders` is slow — 500ms for 100 orders. How do you debug it?"

**You (architect answer):**

> "First thing I'd check is whether this is an N+1 problem. Classic symptoms: the endpoint gets
> slower linearly as the result set grows — 100 orders takes 500ms, 200 orders takes 1000ms —
> because you're doing N+1 database round trips.
>
> I'd enable Hibernate's SQL logging in development:
> `spring.jpa.show-sql=true` and `logging.level.org.hibernate.SQL=DEBUG`.
> If I see 101 queries in the log for a 100-row request, N+1 is confirmed.
>
> The fix depends on the access pattern. If this is a read endpoint that always needs order items,
> I'd use JOIN FETCH or @EntityGraph to eager-load items in a single query. If only some callers
> need items (some just need the order header), I'd keep LAZY loading but add a separate
> endpoint or projection for the detailed view.
>
> In production, I'd use Datadog APM or Micrometer + Prometheus to track queries-per-request
> as a metric. If that number grows proportionally with result set size, something has regressed
> back to N+1. I treat queries-per-request as a KPI, not just query latency."

---

## PART 6 — N+1 IN OTHER FRAMEWORKS

### Django ORM (Python)

```python
# N+1 problem:
orders = Order.objects.all()           # 1 query
for order in orders:
    print(order.items.all())           # N queries

# Fix: select_related (for ForeignKey) or prefetch_related (for ManyToMany/reverse FK)
orders = Order.objects.prefetch_related('items').all()  # 2 queries total
# Query 1: SELECT * FROM orders
# Query 2: SELECT * FROM order_items WHERE order_id IN (1, 2, 3, ...)
```

### ActiveRecord (Ruby on Rails)

```ruby
# N+1:
orders = Order.all
orders.each { |o| puts o.items }    # N queries

# Fix: includes
orders = Order.includes(:items).all  # 2 queries total
```

### TypeORM (Node.js / TypeScript)

```typescript
// N+1:
const orders = await orderRepo.find();
for (const order of orders) {
    await order.items;  // lazy loaded per order
}

// Fix: relations in find options
const orders = await orderRepo.find({ relations: ['items'] });
// Or: createQueryBuilder().leftJoinAndSelect('order.items', 'item').getMany()
```

---

## PART 7 — WHEN JOIN FETCH CREATES A DIFFERENT PROBLEM

```
The "cartesian product" problem:

  Order 1 has 3 items
  Order 2 has 4 items

  JOIN result:
  order_id  item_id
  ────────  ───────
  1         item-A     ← order 1 row repeated 3 times
  1         item-B
  1         item-C
  2         item-D     ← order 2 row repeated 4 times
  2         item-E
  2         item-F
  2         item-G

  SELECT COUNT(*) = 7 rows for 2 orders
  For 100 orders with avg 10 items each: 1000 rows transferred, not 100

  Fix: use DISTINCT in JOIN FETCH:
  @Query("SELECT DISTINCT o FROM Order o JOIN FETCH o.items")

  Or use pagination carefully:
  JOIN FETCH + LIMIT doesn't work as expected in Hibernate
  (it fetches ALL rows then limits in memory — warns: "HHH90003004")
  Fix for pagination: use @BatchSize instead of JOIN FETCH when paginating
```

---

## QUICK REFERENCE CARD

```
┌──────────────────────┬───────────────┬──────────────────────────┐
│ Fix                  │ Queries       │ Best for                 │
├──────────────────────┼───────────────┼──────────────────────────┤
│ JOIN FETCH (JPQL)    │ 1             │ Always-needed relations  │
│ @EntityGraph         │ 1             │ Cleaner syntax           │
│ @BatchSize           │ N/batchSize   │ Pagination, large sets   │
│ DTO Projection       │ 1             │ Read-only, max perf      │
│ FetchType.EAGER      │ 1             │ Never (loads always)     │
└──────────────────────┴───────────────┴──────────────────────────┘

Diagnostic tools:
  Dev:  spring.jpa.show-sql=true
  Dev:  p6spy (logs all SQL with timing)
  Prod: Datadog APM, New Relic, Dynatrace → "slow DB queries" dashboard
  Metric to watch: queries_per_request (should be constant regardless of N)

Rule of thumb:
  If your endpoint response time grows linearly with result set size → N+1
  If it grows logarithmically → probably an index issue
  If it's flat → you're good
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** N+1 is the most common backend performance mistake — interviewers ask about feed loading, listing pages, and order history specifically to check whether you know this trap.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **05 — Social Media (Instagram/Facebook)** | Feed loads 20 posts → ORM lazily fetches each post's author profile separately → 21 queries instead of 1. At 1 million users loading their feed simultaneously, that's the difference between 1M and 21M DB queries per second. Fix: JOIN FETCH or @EntityGraph on the post-author relationship. |
| **08 — Food Delivery** | Restaurant listing loads 50 restaurants → ORM lazily fetches each restaurant's menu categories → 51 queries per page load. At scale this collapses the DB under listing traffic. Fix: @EntityGraph on the restaurant-categories relationship reduces to 1 JOIN query. |
| **09 — E-Commerce** | Product search returns 40 products → ORM fetches each product's seller info and aggregate rating separately → 81 queries per search. Fix: DTO projection with an explicit JOIN query fetches all data in 1 round trip, and the covering index means no heap fetch at all. |

**Architect's one-liner for the interview:**
*"N+1 happens when you let your ORM drive — the fix is to tell the DB what you need upfront with a JOIN, not ask it 'what's this entity's related data?' one row at a time."*
