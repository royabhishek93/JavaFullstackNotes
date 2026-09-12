> **Sequence 15/19 (Tier 4 ⚙️)** — See [README.md](README.md) for the full ranked index.

# The `map()` operator and its blocking-call trap

**Interview framing:** "Production issue: you need to convert every element in a stream (e.g., mask a field, convert to a DTO) without breaking the reactive chain. What operator, and what's the catch?"

**Use `map()`** — transforms each element into **another value of the same "shape"** (one input → one output), synchronously, and re-emits it into a new `Flux`/`Mono` of that type.

```java
public Flux<UserDto> getMaskedUsers() {
    return userRepository.findAll()
        .map(user -> new UserDto(user.getId(), maskEmail(user.getEmail())));
}
```

**The catch (the actual interview trap):** `map()`'s transformation function **must be synchronous and non-blocking**. If you accidentally put a blocking call inside `map()` (a JDBC query, a `Thread.sleep`, a blocking HTTP client call), you block the reactive event-loop thread that's supposed to stay free — silently defeating the entire point of using a reactive stack. This is one of the most common production bugs in early-stage WebFlux codebases (see [02-blocking-call-poisons-event-loop.md](02-blocking-call-poisons-event-loop.md) for why blocking a Netty thread is worse than blocking a Tomcat thread).

**Testing it (don't manually `subscribe()` and eyeball console output — use `StepVerifier`, see [12-stepverifier-testing.md](12-stepverifier-testing.md)):**

```java
@Test
void mapTest() {
    StepVerifier.create(userService.getMaskedUsers())
        .expectNextCount(4)
        .verifyComplete();
}
```

> **One-line takeaway:** `map()` = synchronous 1-to-1 transform. Never put a blocking call inside it — that's the #1 way to accidentally un-reactive your reactive pipeline.

---
**Next:** [16-filter-operator.md](16-filter-operator.md)
