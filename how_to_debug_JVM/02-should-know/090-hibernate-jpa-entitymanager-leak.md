# #90 — Hibernate/JPA EntityManager Leak

> **Category:** Memory Leaks End-to-End | **Type:** Scenario Q&A | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"Describe how an EntityManager can leak and what the heap dump would show."

## 😊 Explain It Simply (for anyone)
An `EntityManager` (Hibernate/JPA's session object for talking to the database) keeps a personal notebook of everything it has looked up (a "first-level cache" — a per-session memory of every record it has touched). If you never "close the notebook" (call `close()`), every record it ever looked at stays remembered forever, even after you're done with them. In a busy application doing thousands of lookups a minute, that notebook becomes an entire library, and the room (your heap memory) runs out of shelf space.

## 📊 Visualize It
```
 EntityManager (never closed)
   |
   +-- persistence context (1st-level cache)
          |
          +--> Product(id=1)
          +--> Product(id=2)
          +--> Product(id=3)
          ... grows with every findById() call, never released

 Fix: try (EntityManager em = ...) { ... }
      -> em.close() always runs -> persistence context released
```

## 🏭 The Real Production Answer (15-YOE Level)

Buggy code:
```java
@Service
public class ProductRepository {
    @PersistenceUnit
    private EntityManagerFactory emf;

    public Product findById(Long id) {
        EntityManager em = emf.createEntityManager(); // LEAK: never closed
        return em.find(Product.class, id);
        // em.close() missing — first-level cache (persistence context) stays live
    }
}
```

Why it leaks: Each EntityManager has a first-level cache (persistence context) that holds all loaded entities. If the EM is never closed, all those entity objects remain reachable. In a long-running service or batch job, this can balloon.

Secondary leak — L2 cache misconfiguration: if EhCache or Infinispan L2 cache is configured without a TTL or max entries, every loaded entity accumulates.

Fix:
```java
public Product findById(Long id) {
    try (EntityManager em = emf.createEntityManager()) { // Java 7+, EM is AutoCloseable
        return em.find(Product.class, id);
    }
}
```

In Spring: use `@Transactional` with `@PersistenceContext` (Spring manages EM lifecycle) or a `JpaRepository` — never create EntityManagers manually unless you close them.

L2 cache fix (persistence.xml / application.properties):
```properties
spring.jpa.properties.hibernate.cache.use_second_level_cache=true
spring.jpa.properties.hibernate.cache.region.factory_class=jcache
# In ehcache.xml: add maxEntriesLocalHeap and timeToLiveSeconds to all regions
```

## 🔑 Key Takeaway
An unclosed `EntityManager`'s first-level cache holds every loaded entity forever — always close it (or let Spring manage it via `@Transactional`).
