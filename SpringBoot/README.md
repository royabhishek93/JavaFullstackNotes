# SpringBoot Notes

This folder is the canonical home for Spring framework behavior and implementation details.

## Scope
- Spring Boot internals
- AOP, proxies, auto-configuration, interceptors
- Spring-specific runtime behavior

## Files

| File | Topic | Difficulty |
|---|---|---|
| Q1_interceptor_implementation.md | Interceptors — HandlerInterceptor, filter chain | ⭐⭐⭐⭐ |
| Q2_springboot_autoconfiguration.md | Auto-configuration, @Conditional, starters | ⭐⭐⭐⭐ |
| Q3_transactional_proxy_flow.md | @Transactional proxy mechanics | ⭐⭐⭐⭐⭐ |
| Q4_aop_log_execution_time.md | AOP, @Around, pointcut expressions | ⭐⭐⭐⭐ |
| Q5_transactional_propagation_deep_dive.md | REQUIRES_NEW vs NESTED vs MANDATORY | ⭐⭐⭐⭐⭐ |
| Q6_async_pitfalls.md | @Async — self-invocation, thread pool, exception handling | ⭐⭐⭐⭐⭐ |
| Q7_blocking_in_reactive_pipeline.md | WebFlux — blocking in reactive pipeline | ⭐⭐⭐⭐⭐ |
| Q8_bean_lifecycle.md | Bean lifecycle, BeanPostProcessor, scopes | ⭐⭐⭐⭐⭐ |
| Q9_global_exception_handling.md | @ControllerAdvice, @ExceptionHandler, ProblemDetail | ⭐⭐⭐⭐ |
| Q10_graceful_shutdown_k8s_probes.md | Graceful shutdown, liveness/readiness probes | ⭐⭐⭐⭐ |
| Q11_production_traps.md | OSIV, HikariCP exhaustion, LazyInitException, N+1 | ⭐⭐⭐⭐⭐ |
| Q12_circuit_breaker_resilience4j.md | Resilience4j — circuit breaker, bulkhead, rate limiter, retry | ⭐⭐⭐⭐⭐ |
| Q13_caching_traps.md | @Cacheable — self-invocation, stampede, null cache, evict traps | ⭐⭐⭐⭐⭐ |
| Q14_spring_security_jwt_traps.md | JWT, token blacklist, ROLE_ prefix, async SecurityContext, CSRF | ⭐⭐⭐⭐⭐ |
| Q15_kafka_event_driven_traps.md | Kafka — poison pill, idempotent consumer, outbox pattern, rebalance | ⭐⭐⭐⭐⭐ |
| Q16_microservices_distributed_traps.md | Saga, idempotency keys, CQRS, distributed tracing, split-brain | ⭐⭐⭐⭐⭐ |
| Q17_configuration_profiles_traps.md | @ConfigurationProperties, actuator security, Vault, @RefreshScope | ⭐⭐⭐⭐ |
| Q18_spring_data_jpa_advanced.md | @Modifying clearAutomatically, Projection, Specification API, keyset pagination, @EntityGraph, @Lock | ⭐⭐⭐⭐⭐ |
| Q19_spring_boot_testing.md | @WebMvcTest vs @DataJpaTest vs @SpringBootTest, @MockBean cache trap, Testcontainers, WireMock, Awaitility | ⭐⭐⭐⭐⭐ |
| Q20_actuator_observability.md | Custom HealthIndicator, Micrometer Counter/Timer/Gauge, Actuator secret exposure trap, distributed tracing | ⭐⭐⭐⭐⭐ |
| Q21_spring_events_transactional.md | @EventListener, @TransactionalEventListener AFTER_COMMIT, @Async events, exception propagation trap | ⭐⭐⭐⭐⭐ |
| Q22_spring_boot_performance.md | JVM container memory (-Xmx OOMKill trap), ZGC vs G1GC, virtual threads (Loom), lazy init, layered JAR | ⭐⭐⭐⭐⭐ |
| webflux-senior-interview-questions.md | WebFlux full reference — Mono, Flux, backpressure | ⭐⭐⭐⭐⭐ |
| SPRINGBOOT_ARCHITECT_PRINT_GUIDE.md | Print-ready architect cheat sheet | — |

## Notes
- If the primary question is Spring runtime behavior, keep the file here.
- See ../OWNERSHIP_RULES.md and ../MIGRATION_MAP.md.
- Q12–Q17 added 2026-08-21: scenario + advanced + trap format for 15-yr architect rounds.
- Q18–Q22 added 2026-08-21: JPA advanced, testing, observability, events, performance tuning.
