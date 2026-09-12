# Graceful Degradation
### Recommendations Service Is Down → Show Popular Items Instead of Crashing

---

## PART 1 — THE STUDENT CONVERSATION

**The question is not "will things go wrong?" — they will. The question is "how wrong does it get?"**

Your e-commerce platform depends on 20 microservices to render a product page. If any one of them going down causes the entire page to crash, you have a fragile system. A single service failure = zero revenue.

**Graceful degradation means: when a non-critical feature fails, degrade its output instead of failing the entire response.**

The user experience is degraded (worse than normal) but functional (not completely broken).

Think about a car. If the air conditioning stops working, the car still drives. If the radio fails, you still get to work. If the power steering fails, you can still steer (with more effort). Only engine failure stops the car. Graceful degradation = only critical failures stop the application.

**Critical vs non-critical features:** Checkout and payment are critical — failure = complete failure. Product recommendations, personalized banners, related items, review summaries — non-critical. If they fail, return a placeholder or fallback. The page still loads. Revenue still flows.

---

## PART 2 — WHAT TO DO WHEN EACH SERVICE FAILS

```
E-Commerce product page dependencies:
──────────────────────────────────────────────────────────────────

  ┌─────────────────────────────────────────────────────────────┐
  │  Product Page = 8 services                                  │
  │                                                             │
  │  CRITICAL (page fails without these):                       │
  │  ✓ Product Service    → product name, price, description    │
  │  ✓ Inventory Service  → "in stock" / "out of stock"         │
  │                                                             │
  │  NON-CRITICAL (degrade gracefully if these fail):           │
  │  ∘ Recommendation Svc → "Customers also bought..."         │
  │  ∘ Review Svc         → star ratings, review text           │
  │  ∘ Pricing Svc        → dynamic discounts, promo prices      │
  │  ∘ Ad Service         → sponsored products                   │
  │  ∘ Wishlist Svc       → "Add to wishlist" button state       │
  │  ∘ Personalization    → user-specific content                │
  └─────────────────────────────────────────────────────────────┘

Service failure → fallback:
  Recommendation Svc down → show "Bestsellers in this category" (static list from Redis)
  Review Svc down          → hide reviews section entirely, or show "Reviews unavailable"
  Pricing Svc down         → show base price from Product Service (no discount)
  Ad Service down          → show blank or placeholder (no revenue lost, just no ad)
  Wishlist Svc down        → show heart icon as un-filled (state unknown, non-destructive)
  Personalization down     → show generic content instead of personalized
```

---

## PART 3 — IMPLEMENTATION PATTERNS

### Pattern 1: Static Fallback Cache

```java
@Service
public class RecommendationService {

    @Autowired private RecommendationClient client;
    @Autowired private RedisTemplate<String, List<Product>> redis;

    public List<Product> getRecommendations(String productId, String userId) {

        // Try the real service with a tight timeout
        try {
            return client.getRecommendations(productId, userId);
        } catch (Exception e) {
            log.warn("Recommendation service failed for product {}: {}", productId, e.getMessage());
            return getFallback(productId);
        }
    }

    private List<Product> getFallback(String productId) {
        // Fallback 1: category bestsellers from Redis (refreshed every 5 minutes)
        String category = productCatalog.getCategory(productId);
        List<Product> cached = redis.opsForValue().get("bestsellers:" + category);
        if (cached != null) return cached;

        // Fallback 2: global bestsellers (always in Redis)
        List<Product> globalBest = redis.opsForValue().get("bestsellers:global");
        if (globalBest != null) return globalBest;

        // Fallback 3: empty list (show nothing, not an error)
        return Collections.emptyList();
    }
}
```

### Pattern 2: Parallel Calls with Timeout + CompletableFuture

```java
// Fetch product page data in parallel, fail gracefully per component
@GetMapping("/products/{id}")
public ProductPageResponse getProductPage(@PathVariable String id) {

    // Start all calls in parallel with individual timeouts
    CompletableFuture<Product> productFuture =
        CompletableFuture.supplyAsync(() -> productService.get(id))
            .orTimeout(2, TimeUnit.SECONDS);  // CRITICAL — no fallback

    CompletableFuture<List<Product>> recsFuture =
        CompletableFuture.supplyAsync(() -> recommendationService.get(id))
            .orTimeout(1, TimeUnit.SECONDS)
            .exceptionally(ex -> getFallbackRecommendations(id));  // fallback

    CompletableFuture<ReviewSummary> reviewsFuture =
        CompletableFuture.supplyAsync(() -> reviewService.getSummary(id))
            .orTimeout(1, TimeUnit.SECONDS)
            .exceptionally(ex -> null);  // null = hide reviews section

    // Wait for all (critical ones throw, non-critical have fallbacks)
    CompletableFuture.allOf(productFuture, recsFuture, reviewsFuture).join();

    return ProductPageResponse.builder()
        .product(productFuture.join())                    // throws if null
        .recommendations(recsFuture.join())               // empty list fallback
        .reviewSummary(reviewsFuture.join())              // null = hide section
        .build();
}
```

### Pattern 3: Feature Flags for Emergency Degradation

```java
// Toggle non-critical features off instantly without code deploy
@Service
public class FeatureToggleService {
    @Autowired private FeatureFlagClient flags;  // LaunchDarkly, GrowthBook, etc.

    public boolean isRecommendationsEnabled(String userId) {
        // Can turn off recommendations for all users or a % of users
        return flags.isEnabled("recommendations-service", userId);
    }
}

// In product page controller:
if (featureToggle.isRecommendationsEnabled(userId)) {
    recs = recommendationService.get(productId);
} else {
    recs = fallbackRecommendations(productId);  // skip the call entirely
}

// Ops team can turn off recommendations in 1 second during an incident
// without waiting for a code deploy or restart
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your social feed is partially down — the recommendation algorithm is failing but feed posts load fine. What do you do?"

**You (architect answer):**

> "First, I want to make sure the recommendation failure doesn't cascade into feed post failure.
> These should be on completely separate code paths. Feed posts come from Cassandra via the
> Feed Service. Recommendations come from a separate ML Recommendation Service. If I'm calling
> both in parallel — which I should be — a recommendation failure should only degrade that
> specific section.
>
> The graceful degradation strategy for recommendations:
>
> First fallback: serve from a pre-computed Redis cache. Every 5 minutes, a background job
> runs the recommendation algorithm for all active users and caches results. When the live
> service fails, serve from this cache — recommendations are 5 minutes stale but present.
>
> Second fallback: serve trending content. The trending algorithm is simpler, runs independently,
> and is already in Redis (it powers the Trending page). Stale is fine here — trending changes
> slowly.
>
> Third fallback: hide the section entirely. If Redis is also unavailable, just don't render
> the recommendation carousel. The feed still loads, the user can scroll posts.
>
> The code path is: try live service (500ms timeout) → catch → try Redis cache → catch →
> try trending → catch → return empty list.
>
> I'd also fire an alert when falling back, and expose a metric: recommendation_fallback_count.
> If it spikes, on-call investigates. But during the incident, users are unaffected — they just
> see 'Trending' instead of 'Recommended For You.'"

---

## PART 5 — WHICH FEATURES CAN DEGRADE

```
Framework for deciding critical vs non-critical:
────────────────────────────────────────────────────────────────────

ASK: "If this feature fails, can the user complete their core task?"

Core task for e-commerce: Browse → Add to cart → Checkout → Pay → Confirm
Core task for social feed: View posts → Post → Comment → Like
Core task for ride-hailing: Request ride → Match driver → Pay

CRITICAL (failure = core task fails):
  E-Commerce:    Product Service, Cart Service, Payment Service, Inventory Service
  Social Feed:   Feed Post Service, Auth Service
  Ride-Hailing:  Driver Matching, Payment, Map/GPS

NON-CRITICAL (degrade gracefully):
  E-Commerce:    Recommendations, Reviews, Ad Service, Price History, Wishlists
  Social Feed:   Recommendations, Trending, Ads, Analytics
  Ride-Hailing:  ETA prediction, Surge pricing display, Driver ratings display

Fallback strategies by feature type:
  Personalized content   → generic/trending content (same format, different data)
  Dynamic pricing        → base price (never show "no price")
  Review scores          → hide section (never show "0 stars" — misleading)
  Ads                    → blank space or default promotion (never error)
  User preferences       → default preferences (non-destructive)
  Notifications          → queue for async delivery (don't drop, just delay)
```

---

## QUICK REFERENCE CARD

```
Graceful degradation: non-critical feature fails → fallback, not crash

Implementation layers:
  1. Circuit breaker    → detect failure fast, stop calling broken service
  2. Static cache       → pre-computed data in Redis as fallback
  3. Default/empty      → safe value when all fallbacks exhausted
  4. Feature flags      → operator can disable feature in real-time during incident

Fallback priority (try in order):
  Live service → Redis cache → trending/popular data → empty/hide

Design principles:
  ✓ Isolate non-critical calls (async, parallel, separate thread pool)
  ✓ Set tight timeouts on non-critical services (fail fast)
  ✓ Never fail the critical path due to a non-critical service
  ✓ Always have a fallback for every non-critical service call
  ✓ Fallback must be pre-populated (populated proactively, not lazily)
  ✗ Never show stale data as current (label it "Trending" not "For You")
  ✗ Never show zeros/nulls as real data (hide the section instead)

Monitoring:
  fallback_invocations_total{service="recommendations"} → alert if sustained
  feature_flag_state{flag="recommendations"} → track when features are disabled

Interview one-liner:
"Graceful degradation separates the critical path from the nice-to-have.
When recommendations fail, show bestsellers from Redis. When reviews fail,
hide the section. The user completes checkout — that's what matters."
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Graceful degradation is how you show an interviewer you understand that availability and perfect functionality are different things — a degraded experience is always better than a crash.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **05 — Social Media** | Recommendation service is down → show "Most Popular Posts" (cached static list from 5 minutes ago) instead of personalized feed. User sees content; recommendation failure is invisible. |
| **09 — E-Commerce** | Product review service is down → show product page without reviews section. Product details, price, add-to-cart still work. Users can still buy; they just don't see reviews. |
| **17 — OTT Platform** | Recommendation engine is down → show "Top 10 Trending" (cached, refreshed every 10 minutes). User lands on home screen with content immediately. Recommendation failure never surfaces to the user. |

**Architect's one-liner for the interview:**
*"Separate the critical path (checkout, playback, booking) from the nice-to-haves (recommendations, reviews, banners) — when non-critical features fail, return a cached fallback and keep revenue flowing."*
