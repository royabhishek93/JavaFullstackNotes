# Q18: Spring Data JPA Advanced — Scenario, Advanced & Trap Questions (15-Yr Architect)

**Study Time:** 20-25 minutes | **Frequency:** 90% in architect rounds 🔥🔥🔥 | **Difficulty:** ⭐⭐⭐⭐⭐

> "We ran a bulk update query that updated 50,000 rows. The next read in the same transaction returned stale data. The DB had the correct values. The JPA first-level cache had the old ones." — The @Modifying clearAutomatically trap.

---

## Scenario 1: @Query + @Modifying — The Stale Cache Trap

### The Bug
```java
@Repository
public interface OrderRepository extends JpaRepository<Order, Long> {

    // WRONG ❌ — first-level cache not cleared after bulk update
    @Modifying
    @Query("UPDATE Order o SET o.status = :status WHERE o.userId = :userId")
    int bulkUpdateStatus(@Param("userId") Long userId,
                         @Param("status") OrderStatus status);
}

@Service
@Transactional
public class OrderService {
    public void processUserOrders(Long userId) {
        orderRepo.bulkUpdateStatus(userId, OrderStatus.PROCESSING);

        // Reads from Hibernate 1st-level cache (EntityManager session cache)
        // Cache has OLD status — DB has new status
        List<Order> orders = orderRepo.findByUserId(userId);
        // orders.get(0).getStatus() → PENDING (wrong!) not PROCESSING
    }
}
```

### Why It Happens
```
Hibernate maintains a 1st-level cache (EntityManager session cache).
@Modifying bulk queries bypass the cache — they go direct to DB.
Cache is now stale. Subsequent reads in same session return old data.
```

### Fix: clearAutomatically + flushAutomatically
```java
@Modifying(
    clearAutomatically = true,   // clears 1st-level cache after update
    flushAutomatically = true    // flushes pending changes to DB before update
)
@Transactional
@Query("UPDATE Order o SET o.status = :status WHERE o.userId = :userId")
int bulkUpdateStatus(@Param("userId") Long userId,
                     @Param("status") OrderStatus status);
```

```
clearAutomatically = true:
  After the bulk UPDATE, Hibernate evicts all entities from
  the session cache. Next read hits the DB → gets fresh data.

flushAutomatically = true:
  Before the bulk UPDATE, Hibernate flushes any pending entity
  changes to DB. Prevents lost-update if you modified entities
  before calling the bulk query.
```

### When to Use Bulk @Modifying
```
Use @Modifying for:
  ✅ Update/delete affecting many rows (hundreds to millions)
  ✅ Batch expiry, status transitions, soft deletes
  ✅ Avoids loading entities into memory just to set one field

Don't use @Modifying for:
  ❌ Updates needing pre/post processing (use entity lifecycle hooks)
  ❌ Updates where you need the returned entity immediately in same TX
     (use clearAutomatically=true if you do)
```

---

## Scenario 2: Projection — Don't Load What You Don't Need

### The Problem
```java
// Loading entire Order entity to show order summary in a list
// Order has: id, userId, status, createdAt, items (lazy collection),
//            shippingAddress, billingAddress, promoCode, metadata...
// You only need: id, status, totalAmount for the order list page

List<Order> orders = orderRepo.findByUserId(userId);
// Loads ALL fields including lazy collections if accessed
// Jackson serializer accesses getItems() → N+1 queries
```

### Fix 1: Interface Projection (Spring Data does the SQL trimming)
```java
// Define a projection interface — Spring Data generates SQL with only these columns
public interface OrderSummary {
    Long getId();
    OrderStatus getStatus();
    BigDecimal getTotalAmount();
    LocalDateTime getCreatedAt();

    // Nested projection — still a JOIN, not N+1
    UserInfo getUser();
    interface UserInfo {
        String getEmail();
    }

    // Computed field via SpEL
    @Value("#{target.totalAmount > 1000 ? 'HIGH_VALUE' : 'STANDARD'}")
    String getValueTier();
}

// Repository — return type drives SQL column selection
List<OrderSummary> findByUserId(Long userId);
// SQL: SELECT o.id, o.status, o.total_amount, o.created_at,
//             u.email FROM orders o JOIN users u... WHERE o.user_id=?
// No unused columns loaded — faster, less memory
```

### Fix 2: DTO Projection (Explicit, Type-Safe)
```java
// DTO record (Java 16+)
public record OrderSummaryDTO(Long id, OrderStatus status,
                              BigDecimal totalAmount, String userEmail) {}

// Repository — JPQL constructor expression
@Query("""
    SELECT new com.example.dto.OrderSummaryDTO(
        o.id, o.status, o.totalAmount, u.email
    )
    FROM Order o JOIN o.user u
    WHERE o.userId = :userId
    ORDER BY o.createdAt DESC
    """)
List<OrderSummaryDTO> findSummaryByUser(@Param("userId") Long userId);
```

### Interface vs DTO Projection — When to Use
```
Interface Projection:
  ✅ Quick, no DTO class needed
  ✅ Spring Data optimises the SELECT automatically
  ⚠️  SpEL computed fields load the full entity (bypasses optimisation)
  ⚠️  Harder to serialize to JSON (need @JsonProperty on methods)

DTO Projection (recommended for production):
  ✅ Type-safe, easy to serialize
  ✅ Predictable SQL (you control the constructor expression)
  ✅ Works in both JPQL and native queries
  ❌ Requires maintaining a DTO class
```

---

## Scenario 3: Specification API — Dynamic Filter Queries

### The Problem
```java
// Order search with optional filters: status, dateRange, userId, minAmount
// Without Specification: combinatorial explosion of query methods
OrderRepository.findByStatus(...)
OrderRepository.findByStatusAndUserId(...)
OrderRepository.findByStatusAndUserIdAndCreatedAtBetween(...)
OrderRepository.findByStatusAndUserIdAndCreatedAtBetweenAndTotalAmountGreaterThan(...)
// ... 15 more combinations
```

### Fix: JPA Specification (Dynamic, Composable Criteria)
```java
public class OrderSpecifications {

    public static Specification<Order> hasStatus(OrderStatus status) {
        return (root, query, cb) ->
            status == null ? null : cb.equal(root.get("status"), status);
    }

    public static Specification<Order> forUser(Long userId) {
        return (root, query, cb) ->
            userId == null ? null : cb.equal(root.get("userId"), userId);
    }

    public static Specification<Order> createdBetween(LocalDate from, LocalDate to) {
        return (root, query, cb) -> {
            if (from == null && to == null) return null;
            if (from == null) return cb.lessThanOrEqualTo(root.get("createdAt"), to.atTime(23, 59));
            if (to == null)   return cb.greaterThanOrEqualTo(root.get("createdAt"), from.atStartOfDay());
            return cb.between(root.get("createdAt"), from.atStartOfDay(), to.atTime(23, 59));
        };
    }

    public static Specification<Order> minAmount(BigDecimal min) {
        return (root, query, cb) ->
            min == null ? null : cb.greaterThanOrEqualTo(root.get("totalAmount"), min);
    }
}

// Repository
public interface OrderRepository extends JpaRepository<Order, Long>,
                                          JpaSpecificationExecutor<Order> {}

// Service — compose dynamically based on what was provided
public Page<Order> searchOrders(OrderSearchRequest req, Pageable pageable) {
    Specification<Order> spec = Specification
        .where(OrderSpecifications.hasStatus(req.getStatus()))
        .and(OrderSpecifications.forUser(req.getUserId()))
        .and(OrderSpecifications.createdBetween(req.getFrom(), req.getTo()))
        .and(OrderSpecifications.minAmount(req.getMinAmount()));

    return orderRepo.findAll(spec, pageable);
    // SQL built dynamically — only adds WHERE clauses for non-null filters
}
```

---

## Trap 1: Offset Pagination at Scale

### The Problem
```java
// Works fine for page 1-10. Devastatingly slow for page 10,000.
Page<Order> page = orderRepo.findAll(PageRequest.of(10000, 20));

// Generated SQL:
// SELECT * FROM orders ORDER BY created_at LIMIT 20 OFFSET 200000
// DB must read AND DISCARD 200,000 rows before returning 20
// On a table with 10M rows → full table scan effectively
```

### Fix: Keyset Pagination (Cursor-Based)
```java
// Instead of page number, use the last-seen value as cursor
@Query("""
    SELECT o FROM Order o
    WHERE o.createdAt < :lastSeen
    ORDER BY o.createdAt DESC
    """)
List<Order> findNextPage(@Param("lastSeen") LocalDateTime lastSeen,
                         Pageable pageable);   // LIMIT only, no OFFSET

// Client sends the last item's createdAt as the cursor for next page
// → DB uses index seek instead of offset scan → O(1) per page
```

### Fix: Countless Pagination (Skip the COUNT(*) query)
```java
// Spring Data Page<T> always runs a COUNT(*) for total pages
// On large tables this is expensive!

// Use Slice<T> instead — no count query, just "hasNext"
Slice<Order> findByUserId(Long userId, Pageable pageable);
// → Only one query (no COUNT)
// → Client knows if there's a next page (hasNext()), not total count
```

---

## Trap 2: @EntityGraph vs JOIN FETCH — Duplicate Results

### The Bug
```java
// JPQL JOIN FETCH with collections + pagination = WRONG result count
@Query("SELECT o FROM Order o JOIN FETCH o.items WHERE o.userId = :userId")
Page<Order> findWithItems(@Param("userId") Long userId, Pageable pageable);

// Generated SQL: SELECT ... FROM orders o JOIN order_items i ON ...
// If one order has 5 items → that order appears 5 times in result set
// Spring Data deduplicates in memory, but COUNT and LIMIT apply to raw rows
// → Page shows wrong total count, fewer results than expected
```

### Fix: @EntityGraph (No JOIN in Pagination Query)
```java
// Option 1: @EntityGraph — Hibernate uses separate SELECT for collection
@EntityGraph(attributePaths = {"items"})
Page<Order> findByUserId(Long userId, Pageable pageable);
// → First query: SELECT orders WHERE user_id=? LIMIT 20 (correct pagination)
// → Second query: SELECT items WHERE order_id IN (1,2,3...) (batch load)
// → No duplicate rows, correct total count

// Option 2: Two separate queries (explicit control)
// Step 1: Get paginated order IDs (fast, no JOIN)
@Query("SELECT o.id FROM Order o WHERE o.userId = :userId")
Page<Long> findIdsByUserId(@Param("userId") Long userId, Pageable pageable);

// Step 2: Load orders with items using the IDs
@Query("SELECT o FROM Order o JOIN FETCH o.items WHERE o.id IN :ids")
List<Order> findWithItemsByIds(@Param("ids") List<Long> ids);
```

---

## Trap 3: @Lock — Pessimistic Locking Deadlock

### Scenario
```java
@Repository
public interface InventoryRepository extends JpaRepository<Inventory, Long> {

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("SELECT i FROM Inventory i WHERE i.productId = :productId")
    Optional<Inventory> findByProductIdForUpdate(@Param("productId") Long productId);
}

// Service — acquires row-level lock (SELECT ... FOR UPDATE)
@Transactional
public void reserveInventory(Long productId, int quantity) {
    Inventory inv = inventoryRepo.findByProductIdForUpdate(productId)
                                 .orElseThrow();
    if (inv.getQuantity() < quantity) throw new InsufficientStockException();
    inv.setQuantity(inv.getQuantity() - quantity);
    // Lock released on transaction commit
}
```

### Deadlock Trap
```
Thread A: locks Product 1, then tries to lock Product 2 (waiting)
Thread B: locks Product 2, then tries to lock Product 1 (waiting)
→ Deadlock → DB kills one transaction → exception thrown

Fix: ALWAYS acquire locks in consistent order
     Sort product IDs before acquiring locks
     Use PESSIMISTIC_WRITE only when contention is expected
     Consider OPTIMISTIC locking (version field) for lower-contention scenarios
```

---

## Interview Cheat Sheet

> "For bulk @Modifying queries: always add clearAutomatically=true or you'll read stale data from Hibernate's session cache in the same transaction. For projections: use DTO records with JPQL constructor expressions for type-safety; interface projections are convenient but SpEL fields defeat the optimisation. Specification API solves the combinatorial method explosion for dynamic filter queries. For pagination at scale: offset pagination is O(n) — switch to keyset (cursor) pagination for deep pages, and use Slice instead of Page to skip the expensive COUNT query. JOIN FETCH + pagination = wrong counts — use @EntityGraph which fires a separate batch load instead of a JOIN."
