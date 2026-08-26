# Q19: Spring Boot Testing — Scenario, Advanced & Trap Questions (15-Yr Architect)

**Study Time:** 20-25 minutes | **Frequency:** 85% in architect rounds 🔥🔥🔥 | **Difficulty:** ⭐⭐⭐⭐⭐

> "Our test suite went from 30 seconds to 8 minutes after someone added @MockBean everywhere. We had 200 tests, each destroying and recreating the full Spring context." — The @MockBean context cache trap.

---

## The Testing Pyramid (What to Use When)

```
                    ╱╲
                   ╱  ╲  E2E Tests (few, slow, real stack)
                  ╱────╲
                 ╱ Integ ╲  Integration Tests (some, moderate)
                ╱──────────╲
               ╱  Unit Tests ╲  Unit Tests (many, fast, isolated)
              ╱────────────────╲

Spring Boot test annotations map to:
  Unit:        @ExtendWith(MockitoExtension) — no Spring context
  Slice:       @WebMvcTest, @DataJpaTest, @JsonTest — partial context
  Integration: @SpringBootTest — full context
```

---

## Scenario 1: @SpringBootTest vs @WebMvcTest vs @DataJpaTest

### The Decision Tree
```
Testing a Controller (HTTP layer)?
  → @WebMvcTest (loads ONLY web layer: controller, filters, security)
  → No DB, no services (mock them with @MockBean)
  → Uses MockMvc — no real HTTP port needed
  → Starts in < 2 seconds

Testing a Repository (DB layer)?
  → @DataJpaTest (loads ONLY JPA: entities, repositories, DataSource)
  → Uses H2 in-memory DB by default (or Testcontainers for real DB)
  → No web layer, no services
  → Auto-rolls back after each test (transactional by default)

Testing full integration (whole system)?
  → @SpringBootTest (loads everything)
  → Optionally starts real HTTP with webEnvironment=RANDOM_PORT
  → Use sparingly — slowest, but tests real wiring
```

```java
// ✅ CORRECT — testing controller in isolation
@WebMvcTest(OrderController.class)
class OrderControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean  // replaces real service in the sliced context
    private OrderService orderService;

    @Test
    void placeOrder_returns201() throws Exception {
        when(orderService.placeOrder(any())).thenReturn(
            new Order(1L, OrderStatus.CREATED)
        );

        mockMvc.perform(post("/api/orders")
                .contentType(APPLICATION_JSON)
                .content("""{"productId": 1, "quantity": 2}"""))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.id").value(1))
            .andExpect(jsonPath("$.status").value("CREATED"));
    }

    @Test
    void placeOrder_returns400_whenPayloadInvalid() throws Exception {
        mockMvc.perform(post("/api/orders")
                .contentType(APPLICATION_JSON)
                .content("""{"quantity": -1}"""))   // missing productId, invalid qty
            .andExpect(status().isBadRequest());
    }
}
```

```java
// ✅ CORRECT — testing JPA repository with real SQL
@DataJpaTest
class OrderRepositoryTest {

    @Autowired
    private OrderRepository orderRepo;

    @Test
    void findByUserId_returnsOnlyUserOrders() {
        orderRepo.save(new Order(null, 1L, OrderStatus.CREATED));
        orderRepo.save(new Order(null, 1L, OrderStatus.DELIVERED));
        orderRepo.save(new Order(null, 2L, OrderStatus.CREATED)); // different user

        List<Order> result = orderRepo.findByUserId(1L);

        assertThat(result).hasSize(2)
                          .allMatch(o -> o.getUserId().equals(1L));
    }
}
// @DataJpaTest auto-wraps each test in @Transactional + rollback
// No need for cleanup in @AfterEach — DB reset is automatic
```

---

## Trap 1: @MockBean Destroys the Spring Context Cache

### The Problem
```
Spring Test caches the ApplicationContext between tests.
If two tests use the same context config, they SHARE the context.
Context starts ONCE, tests reuse it → test suite is fast.

@MockBean INVALIDATES the cache. Each unique set of @MockBean annotations
creates a DIFFERENT context. Spring cannot safely reuse a context
that has mocked beans — the mock state may be different.

Result:
  Test class A: @MockBean OrderService → context 1 (30s to start)
  Test class B: @MockBean PaymentService → context 2 (30s to start)
  Test class C: @MockBean OrderService, @MockBean PaymentService → context 3
  50 test classes with various @MockBean combinations → 50 contexts!
  50 × 30s = 25 minutes of Spring Boot startup time
```

### Fix: Centralise Mocks in a Shared Base Test Config
```java
// Option 1: Shared base class — same set of @MockBean across all tests
@SpringBootTest
@ActiveProfiles("test")
abstract class BaseIntegrationTest {

    @MockBean protected OrderService orderService;
    @MockBean protected PaymentService paymentService;
    @MockBean protected NotificationService notificationService;
    // All tests that extend this → share ONE context
}

class OrderControllerIntTest extends BaseIntegrationTest {
    @Test
    void testSomething() {
        when(orderService.getOrder(1L)).thenReturn(...);
    }
}

// Option 2: @TestConfiguration — real beans, test profiles
// (Even better — avoid @MockBean for integration tests, use test doubles)
```

```java
// Option 3: @WebMvcTest with explicit mock setup — fastest controller tests
// No @SpringBootTest → no context caching problem at all
@WebMvcTest(OrderController.class)
class OrderControllerTest {
    @MockBean OrderService orderService;  // OK here — WebMvcTest is already a slice
    // Context starts fast (< 2s) and is small
}
```

---

## Scenario 2: Testcontainers — Real Database in Tests

### Why H2 Is Not Enough
```
H2 (in-memory DB used by @DataJpaTest default):
  ✅ Fast, no setup
  ❌ Different SQL dialect (PostgreSQL-specific features fail: JSONB, sequences, etc.)
  ❌ Window functions, CTEs, RETURNING clause — may behave differently
  ❌ Connection pooling behaviour differs

Testcontainers — real PostgreSQL in Docker:
  ✅ Identical to production DB
  ✅ Tests all DB-specific features
  ✅ Starts once per test run (~3s), shared across tests
```

```java
@DataJpaTest
@AutoConfigureTestDatabase(replace = Replace.NONE)  // don't replace with H2
@Testcontainers
class OrderRepositoryIntTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:15")
        .withDatabaseName("testdb")
        .withUsername("test")
        .withPassword("test");

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }

    @Autowired
    private OrderRepository orderRepo;

    @Test
    void findTopOrdersByAmount_usesWindowFunction() {
        // Test PostgreSQL-specific window function query
        List<OrderRank> ranks = orderRepo.findTopOrdersWithRank(1L);
        assertThat(ranks.get(0).getRank()).isEqualTo(1);
    }
}
```

```java
// PRODUCTION PATTERN: Shared Testcontainer (start once for all tests)
@SpringBootTest
class BaseContainerTest {

    @ClassRule  // or use @Container with static field
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:15")
        .withReuse(true);  // TC reuses container between runs (if .testcontainers.properties set)
}
```

---

## Scenario 3: WireMock — Testing External API Calls

### The Problem
```
Your service calls Stripe payment API.
In tests, you can't call real Stripe:
  - Costs money, slow
  - Can't test error scenarios (timeout, 500, network failure)
  - Tests become flaky (Stripe up/down)
```

```java
@SpringBootTest(webEnvironment = RANDOM_PORT)
@AutoConfigureWireMock(port = 0)  // random port, URL injected automatically
class PaymentServiceTest {

    @Autowired
    private PaymentService paymentService;

    @Test
    void charge_returnsSuccess_whenStripeResponds200() {
        stubFor(post(urlEqualTo("/v1/charges"))
            .withHeader("Authorization", containing("Bearer sk_test"))
            .withRequestBody(matchingJsonPath("$.amount", equalTo("9999")))
            .willReturn(aResponse()
                .withStatus(200)
                .withHeader("Content-Type", "application/json")
                .withBody("""
                    {"id": "ch_123", "status": "succeeded", "amount": 9999}
                    """)));

        PaymentResult result = paymentService.charge(new PaymentRequest(99.99, "USD"));

        assertThat(result.getStatus()).isEqualTo("succeeded");
        assertThat(result.getChargeId()).isEqualTo("ch_123");
    }

    @Test
    void charge_throwsPaymentException_whenStripeReturns500() {
        stubFor(post(urlEqualTo("/v1/charges"))
            .willReturn(aResponse()
                .withStatus(500)
                .withBody("""{"error": {"type": "api_error"}}""")));

        assertThatThrownBy(() -> paymentService.charge(new PaymentRequest(99.99, "USD")))
            .isInstanceOf(PaymentException.class)
            .hasMessageContaining("Payment provider error");
    }

    @Test
    void charge_triggersCircuitBreaker_onTimeout() {
        stubFor(post(urlEqualTo("/v1/charges"))
            .willReturn(aResponse()
                .withFixedDelay(5000)  // 5s delay → triggers timeout
                .withStatus(200)));

        // Circuit breaker opens after configured timeout
        assertThatThrownBy(() -> paymentService.charge(new PaymentRequest(99.99, "USD")))
            .isInstanceOf(PaymentTimeoutException.class);
    }
}
```

---

## Trap 2: @Transactional on Test Class — False Green Tests

### The Bug
```java
@SpringBootTest
@Transactional  // ← TRAP on integration tests!
class OrderIntegrationTest {

    @Autowired
    private OrderService orderService;

    @Autowired
    private OrderRepository orderRepo;

    @Test
    void placeOrder_persists_toDatabase() {
        orderService.placeOrder(new OrderRequest(1L, 2));

        // This assertion PASSES — same transaction sees uncommitted data
        assertThat(orderRepo.findAll()).hasSize(1);
    }
}
// @Transactional on test class: Spring wraps each test in a TX and ROLLS BACK after.
// Your assertion reads from the rolled-back transaction.
// If placeOrder uses REQUIRES_NEW internally, that TX commits, but the test TX rolls back.
// Result: false green — test passes but the actual production code path isn't tested!

// Also hides problems:
// If your actual service method doesn't work without a surrounding transaction,
// the test's @Transactional may mask that bug.
```

### Fix: Use @Sql for cleanup, not @Transactional
```java
@SpringBootTest
@Sql(scripts = "/cleanup.sql", executionPhase = AFTER_TEST_METHOD)
class OrderIntegrationTest {

    @Test
    void placeOrder_persists_toDatabase() {
        orderService.placeOrder(new OrderRequest(1L, 2));
        // No @Transactional — test runs as production would
        // Commits happen, you verify committed state
        assertThat(orderRepo.findAll()).hasSize(1);
    }
    // @Sql cleanup runs after test — DELETE FROM orders; etc.
}
```

---

## Trap 3: Testing @Async Methods

### The Problem
```java
@SpringBootTest
class NotificationServiceTest {

    @Autowired
    private OrderService orderService;

    @Autowired
    private NotificationRepository notificationRepo;

    @Test
    void placeOrder_sendsNotification() {
        orderService.placeOrder(new OrderRequest(1L));

        // Notification sent asynchronously via @Async
        // Test thread continues BEFORE async thread finishes
        // Assertion runs immediately — notification not saved yet!
        assertThat(notificationRepo.count()).isEqualTo(1);  // FAILS: 0
    }
}
```

### Fix: Await with Awaitility
```java
@Test
void placeOrder_sendsNotification() {
    orderService.placeOrder(new OrderRequest(1L));

    await()
        .atMost(5, SECONDS)           // wait up to 5 seconds
        .pollInterval(100, MILLISECONDS)  // check every 100ms
        .untilAsserted(() ->
            assertThat(notificationRepo.count()).isEqualTo(1)
        );
}
```

---

## Quick Reference: Test Annotations

| Annotation | What Loads | Speed | Use For |
|---|---|---|---|
| `@ExtendWith(Mockito...)` | Nothing (pure Mockito) | Instant | Service unit tests |
| `@WebMvcTest` | Web layer only | ~2s | Controller tests |
| `@DataJpaTest` | JPA + DB only | ~3s | Repository tests |
| `@DataJpaTest` + Testcontainers | JPA + real PG | ~5s | Repository with PG features |
| `@SpringBootTest` | Everything | ~10-30s | Integration / wiring tests |
| `@SpringBootTest` + WireMock | Everything + mock HTTP | ~10-30s | External API tests |

---

## Interview Cheat Sheet

> "@MockBean is a double-edged sword — it replaces beans cleanly but invalidates Spring's context cache, so each unique combination of @MockBeans starts a new context. Centralise @MockBeans in a shared base class to keep the suite fast. For controller tests: @WebMvcTest is fast and complete — no need for @SpringBootTest. For DB tests: Testcontainers over H2 when you use any database-specific features. Don't put @Transactional on integration test classes — it hides bugs by rolling back what production code would commit, and can cause false-green tests. For @Async tests, use Awaitility to poll assertions rather than Thread.sleep()."
