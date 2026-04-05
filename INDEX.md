# 📚 Comprehensive Java Interview Questions Index

> **All interview questions** organized by topic and sorted by senior-level importance and frequency.
> 
> **Study time:** 2-5 minutes per question | **Coverage:** Core Java + Spring + System Design + API + Algorithms

---

## 📂 Organized Subdirectories

- [**Core_Java/String_Immutability/**](Core_Java/String_Immutability/README.md)
- [**Core_Java/Stream_API/**](Core_Java/Stream_API/)
- [**Core_Java/Exception_Handling/**](Core_Java/Exception_Handling/)
- [**Core_Java/Database_SQL/**](Core_Java/Database_SQL/)
- [**Core_Java/Design_Patterns/**](Core_Java/Design_Patterns/)
- [**Core_Java/Garbage_Collection/**](Core_Java/Garbage_Collection/README.md) ⭐ NEW
- [**Core_Java/Performance_JVM/**](Core_Java/Performance_JVM/)
- [**Core_Java/Testing/**](Core_Java/Testing/)
- [**Core_Java/Security/**](Core_Java/Security/)
- [**Core_Java/Observability/**](Core_Java/Observability/)
- [**Core_Java/Multithreading_Concurrency/**](Core_Java/Multithreading_Concurrency/README.md)
- [**Core_Java/OOP/**](Core_Java/OOP/README.md)
- [**Core_Java/Async_Reactive/**](Core_Java/Async_Reactive/README.md)
- [**System_Design/**](System_Design/)
- [**API_Design/**](API_Design/)
- [**Spring/**](Spring/)
- [**Java8to21/**](Java8to21/)
- [**Algorithms_LeetCode/**](Algorithms_LeetCode/)
- [**react_javascript/**](react_javascript/) - Frontend (TypeScript/React compilation)

---

## ✅ Senior Priority by Topic (Sorted by Frequency)

### Core Java: String & Immutability

| Priority | Q | Question | Frequency | File |
|----------|---|----------|-----------|------|
| 🔥 CRITICAL | Q1 | String Pool | 75% | [string-pool-vs-heap.md](Core_Java/String_Immutability/string-pool-vs-heap.md) |
| 🔥 CRITICAL | Q2 | String concatenation equality | 70% | [string-concatenation.md](Core_Java/String_Immutability/string-concatenation.md) |
| 🔥 CRITICAL | Q5 | Immutable class requirements | 65% | [immutable-class-requirements.md](Core_Java/String_Immutability/immutable-class-requirements.md) |
| ✅ IMPORTANT | Q3 | `intern()` usage | 50% | [string-intern-method.md](Core_Java/String_Immutability/string-intern-method.md) |
| ✅ IMPORTANT | Q7 | Return mutable collections safely | 50% | [return-mutable-collections.md](Core_Java/String_Immutability/return-mutable-collections.md) |
| ✅ IMPORTANT | Q6 | Defensive copying vs clone | 45% | [defensive-copying-vs-clone.md](Core_Java/String_Immutability/defensive-copying-vs-clone.md) |
| 👍 GOOD TO KNOW | Q4 | String pool GC | 35% | [string-garbage-collection.md](Core_Java/String_Immutability/string-garbage-collection.md) |

#### Additional String & Immutability Topics

| Priority | Topic | Frequency | File |
|----------|-------|-----------|------|
| ✅ IMPORTANT | StringBuilder vs StringBuffer | 60% | [stringbuilder-vs-stringbuffer.md](Core_Java/String_Immutability/stringbuilder-vs-stringbuffer.md) |
| 👍 GOOD TO KNOW | Multiple variable declaration pitfall | 45% | [multiple-variable-declaration.md](Core_Java/String_Immutability/multiple-variable-declaration.md) |
| 👍 GOOD TO KNOW | String concatenation + assignment | 40% | [string-concatenation-assignment.md](Core_Java/String_Immutability/string-concatenation-assignment.md) |
| 👍 GOOD TO KNOW | Concat + assignment + substring | 38% | [string-concat-assignment-substring.md](Core_Java/String_Immutability/string-concat-assignment-substring.md) |

---

### Core Java: Stream API

| Priority | Q | Question | Frequency | File |
|----------|---|----------|-----------|------|
| 🔥 CRITICAL | Q8 | `.map()` vs `.flatMap()` | 92% | [Q8_map_vs_flatmap.md](Core_Java/Stream_API/Q8_map_vs_flatmap.md) |
| 🔥 CRITICAL | Q9 | Lazy evaluation | 88% | [Q9_lazy_evaluation.md](Core_Java/Stream_API/Q9_lazy_evaluation.md) |
| ✅ IMPORTANT | Q10 | Optional usage | 75% | [Q10_optional_usage.md](Core_Java/Stream_API/Q10_optional_usage.md) |
| ✅ IMPORTANT | Q11 | Custom collectors | 72% | [Q11_collectors_custom.md](Core_Java/Stream_API/Q11_collectors_custom.md) |
| ✅ IMPORTANT | Q12 | Parallel streams | 68% | [Q12_parallel_streams.md](Core_Java/Stream_API/Q12_parallel_streams.md) |
| ✅ IMPORTANT | Q13 | Third highest salary (distinct) | 62% | [Q13_third_highest_salary_optional.md](Core_Java/Stream_API/Q13_third_highest_salary_optional.md) |
| 👍 GOOD TO KNOW | Q14 | Employee stream operations | 58% | [Q14_employee_stream_operations.md](Core_Java/Stream_API/Q14_employee_stream_operations.md) |
| 👍 GOOD TO KNOW | Q15 | Generate hashtag from sentence | 55% | [Q15_generate_hashtags.md](Core_Java/Stream_API/Q15_generate_hashtags.md) |

---

### Core Java: Exception Handling

| Priority | Q | Question | Frequency | File |
|----------|---|----------|-----------|------|
| 🔥 CRITICAL | Q13 | Checked vs unchecked exceptions | 85% | [checked-vs-unchecked-exceptions.md](Core_Java/Exception_Handling/checked-vs-unchecked-exceptions.md) |
| 🔥 CRITICAL | Q14 | Custom exceptions | 82% | [custom-exceptions.md](Core_Java/Exception_Handling/custom-exceptions.md) |
| ✅ IMPORTANT | Q15 | Try-with-resources vs try-catch-finally | 70% | [try-with-resources.md](Core_Java/Exception_Handling/try-with-resources.md) |
| ✅ IMPORTANT | Q16 | Exception handling in async code | 65% | [exception-handling-async.md](Core_Java/Exception_Handling/exception-handling-async.md) |

#### Additional Exception Handling Topics

| Priority | Topic | Frequency | File |
|----------|-------|-----------|------|
| ✅ IMPORTANT | Try-catch-finally execution order | 62% | [try-catch-finally-execution-order.md](Core_Java/Exception_Handling/try-catch-finally-execution-order.md) |
| 👍 GOOD TO KNOW | Exception propagation in method overriding | 50% | [exception-propagation-method-overriding.md](Core_Java/Exception_Handling/exception-propagation-method-overriding.md) |

---

### System Design

| Priority | Q | Question | Frequency | File |
|----------|---|----------|-----------|------|
| 🔥 CRITICAL | Q17 | Database scaling | 80% | [database-scaling.md](System_Design/database-scaling.md) |
| 🔥 CRITICAL | Q18 | Caching strategies | 78% | [caching-strategies.md](System_Design/caching-strategies.md) |
| 🔥 CRITICAL | Q19 | Load balancing | 76% | [load-balancing-algorithms.md](System_Design/load-balancing-algorithms.md) |
| ✅ IMPORTANT | Q20 | Microservices vs monolith | 72% | [microservices-vs-monolith.md](System_Design/microservices-vs-monolith.md) |
| ✅ IMPORTANT | Q23 | Saga pattern: Distributed transactions | 72% | [distributed-transactions-saga-vs-2pc.md](System_Design/distributed-transactions-saga-vs-2pc.md) |
| 👍 GOOD TO KNOW | Q21 | CAP theorem | 55% | [cap-theorem-trade-offs.md](System_Design/cap-theorem-trade-offs.md) |
| 👍 GOOD TO KNOW | Q22 | Message queues | 52% | [message-queues.md](System_Design/message-queues.md) |
| 🔥 CRITICAL | — | Cache invalidation patterns | 80% | [cache-invalidation-patterns.md](System_Design/cache-invalidation-patterns.md) |
| ✅ IMPORTANT | — | Database sharding strategies | 70% | [database-sharding-strategies.md](System_Design/database-sharding-strategies.md) |
| ✅ IMPORTANT | — | Multi-region geo distribution | 65% | [multi-region-geo-distribution.md](System_Design/multi-region-geo-distribution.md) |

---

### Database & SQL

| Priority | Q | Question | Frequency | File |
|----------|---|----------|-----------|------|
| ✅ IMPORTANT | Q23 | ACID properties | 75% | [acid-properties.md](Core_Java/Database_SQL/acid-properties.md) |
| ✅ IMPORTANT | Q24 | N+1 query problem | 73% | [n-plus-one-problem.md](Core_Java/Database_SQL/n-plus-one-problem.md) |
| ✅ IMPORTANT | Q25 | Isolation levels | 68% | [isolation-levels.md](Core_Java/Database_SQL/isolation-levels.md) |
| 👍 GOOD TO KNOW | Q26 | Deadlock handling | 58% | [deadlock-handling.md](Core_Java/Database_SQL/deadlock-handling.md) |
| 👍 GOOD TO KNOW | Q27 | Optimistic vs pessimistic locking | 55% | [optimistic-locking.md](Core_Java/Database_SQL/optimistic-locking.md) |
| 👍 GOOD TO KNOW | Q28 | Connection pooling | 48% | [connection-pooling.md](Core_Java/Database_SQL/connection-pooling.md) |

#### Additional Database & SQL Topics

| Priority | Topic | Frequency | File |
|----------|-------|-----------|------|
| 👍 GOOD TO KNOW | SQL query: Top 3 best-selling categories | 55% | [top-3-best-selling-categories.md](Core_Java/Database_SQL/top-3-best-selling-categories.md) |

---

### Design Patterns

| Priority | Q | Question | Frequency | File |
|----------|---|----------|-----------|------|
| ✅ IMPORTANT | Q29 | Singleton patterns | 70% | [Q29_singleton_patterns.md](Core_Java/Design_Patterns/Q29_singleton_patterns.md) |
| 👍 GOOD TO KNOW | Q31 | Builder pattern | 62% | [Q31_builder_pattern.md](Core_Java/Design_Patterns/Q31_builder_pattern.md) |
| 👍 GOOD TO KNOW | Q30 | Factory vs Abstract Factory | 55% | [Q30_factory_pattern.md](Core_Java/Design_Patterns/Q30_factory_pattern.md) |
| 👍 GOOD TO KNOW | Q32 | Decorator pattern | 52% | [Q32_decorator_pattern.md](Core_Java/Design_Patterns/Q32_decorator_pattern.md) |
| 👍 GOOD TO KNOW | Q33 | Strategy pattern | 50% | [Q33_strategy_pattern.md](Core_Java/Design_Patterns/Q33_strategy_pattern.md) |
| 👍 GOOD TO KNOW | Q34 | Observer pattern | 48% | [Q34_observer_pattern.md](Core_Java/Design_Patterns/Q34_observer_pattern.md) |

---

### API Design

| Priority | Q | Question | Frequency | File |
|----------|---|----------|-----------|------|
| ✅ IMPORTANT | Q35 | HTTP methods and idempotency | 65% | [Q35_rest_http_methods.md](API_Design/Q35_rest_http_methods.md) |
| ✅ IMPORTANT | Q36 | HTTP status codes | 62% | [Q36_http_status_codes.md](API_Design/Q36_http_status_codes.md) |
| 👍 GOOD TO KNOW | Q37 | API versioning | 58% | [Q37_api_versioning.md](API_Design/Q37_api_versioning.md) |
| 👍 GOOD TO KNOW | Q38 | Error responses | 55% | [Q38_error_responses.md](API_Design/Q38_error_responses.md) |
| 👍 GOOD TO KNOW | Q39 | Pagination and filtering | 52% | [Q39_pagination_filtering.md](API_Design/Q39_pagination_filtering.md) |
| 👍 GOOD TO KNOW | Q40 | API security | 50% | [Q40_api_security.md](API_Design/Q40_api_security.md) |

---

### Performance & JVM

| Priority | Q | Question | Frequency | File |
|----------|---|----------|-----------|------|
| 🔵 ADVANCED | Q42 | Heap vs stack | 48% | [Q42_heap_vs_stack.md](Core_Java/Performance_JVM/Q42_heap_vs_stack.md) |
| 🔵 ADVANCED | Q41 | GC types (G1, ZGC) | 45% | [Q41_garbage_collection_types.md](Core_Java/Performance_JVM/Q41_garbage_collection_types.md) |
| 🔵 ADVANCED | Q44 | JVM tuning | 45% | [Q44_jvm_tuning.md](Core_Java/Performance_JVM/Q44_jvm_tuning.md) |
| 🔵 ADVANCED | Q43 | Memory leak detection | 42% | [Q43_memory_leak_detection.md](Core_Java/Performance_JVM/Q43_memory_leak_detection.md) |
| 🔵 ADVANCED | Q45 | Profiling tools | 40% | [Q45_profiling_tools.md](Core_Java/Performance_JVM/Q45_profiling_tools.md) |

#### Additional Performance & JVM Topics

| Priority | Topic | Frequency | File |
|----------|-------|-----------|------|
| 🔵 ADVANCED | Q46 | Production debugging OOM | 48% | [Q46_production_debugging_oom.md](Core_Java/Performance_JVM/Q46_production_debugging_oom.md) |
| 🔵 ADVANCED | Q47 | Memory leak vs load diagnosis | 45% | [Q47_memory_leak_vs_load_diagnosis.md](Core_Java/Performance_JVM/Q47_memory_leak_vs_load_diagnosis.md) |
| 🔵 ADVANCED | Q48 | Native exceptions JNI | 35% | [Q48_native_exceptions_jni.md](Core_Java/Performance_JVM/Q48_native_exceptions_jni.md) |

---

### Testing

| Priority | Q | Question | Frequency | File |
|----------|---|----------|-----------|------|
| 🔵 ADVANCED | Q46 | Test types | 55% | [Q46_test_types.md](Core_Java/Testing/Q46_test_types.md) |
| 🔵 ADVANCED | Q47 | Mockito best practices | 50% | [Q47_mockito_mocking.md](Core_Java/Testing/Q47_mockito_mocking.md) |
| 🔵 ADVANCED | Q49 | Testing async code | 48% | [Q49_testing_async.md](Core_Java/Testing/Q49_testing_async.md) |
| 🔵 ADVANCED | Q48 | Test coverage | 45% | [Q48_test_coverage.md](Core_Java/Testing/Q48_test_coverage.md) |
| 🔵 ADVANCED | Q50 | Spring Boot test slices | 45% | [Q50_spring_test_slices.md](Core_Java/Testing/Q50_spring_test_slices.md) |
| 🔵 ADVANCED | Q51 | TestContainers | 42% | [Q51_testcontainers.md](Core_Java/Testing/Q51_testcontainers.md) |
| 🔵 ADVANCED | Q52 | Contract testing | 40% | [Q52_contract_testing.md](Core_Java/Testing/Q52_contract_testing.md) |

---

### Security

| Priority | Q | Question | Frequency | File |
|----------|---|----------|-----------|------|
| 🔵 ADVANCED | Q57 | Password hashing | 72% | [Q57_bcrypt_hashing.md](Core_Java/Security/Q57_bcrypt_hashing.md) |
| 🔵 ADVANCED | Q54 | JWT implementation | 68% | [Q54_jwt_implementation.md](Core_Java/Security/Q54_jwt_implementation.md) |
| 🔵 ADVANCED | Q53 | Auth vs authorization | 50% | [Q53_auth_basics.md](Core_Java/Security/Q53_auth_basics.md) |
| 🔵 ADVANCED | Q58 | Injection prevention | 50% | [Q58_injection_prevention.md](Core_Java/Security/Q58_injection_prevention.md) |
| 🔵 ADVANCED | Q56 | Spring Security | 48% | [Q56_spring_security.md](Core_Java/Security/Q56_spring_security.md) |
| 🔵 ADVANCED | Q55 | OAuth2 | 45% | [Q55_oauth2.md](Core_Java/Security/Q55_oauth2.md) |

---

### Observability

| Priority | Q | Question | Frequency | File |
|----------|---|----------|-----------|------|
| 🔵 ADVANCED | Q59 | Logging frameworks | 42% | [Q59_logging_frameworks.md](Core_Java/Observability/Q59_logging_frameworks.md) |
| 🔵 ADVANCED | Q60 | Metrics collection | 40% | [Q60_metrics_collection.md](Core_Java/Observability/Q60_metrics_collection.md) |
| 🔵 ADVANCED | Q62 | Health checks | 40% | [Q62_health_checks.md](Core_Java/Observability/Q62_health_checks.md) |
| 🔵 ADVANCED | Q61 | Distributed tracing | 38% | [Q61_distributed_tracing.md](Core_Java/Observability/Q61_distributed_tracing.md) |
| 🔵 ADVANCED | Q63 | Structured logging | 38% | [Q63_structured_logging.md](Core_Java/Observability/Q63_structured_logging.md) |
| 🔵 ADVANCED | Q64 | Log aggregation | 35% | [Q64_log_aggregation.md](Core_Java/Observability/Q64_log_aggregation.md) |

---

### Object-Oriented Programming (OOP)

| Priority | Q | Question | Frequency | File |
|----------|---|----------|-----------|------|
| 🔥 CRITICAL | Q11 | Runtime polymorphism: Reference vs object type | 78% | [runtime-polymorphism-reference-vs-object.md](Core_Java/OOP/runtime-polymorphism-reference-vs-object.md) |

#### Additional OOP Topics

| Priority | Topic | Frequency | File |
|----------|-------|-----------|------|
| 👍 GOOD TO KNOW | Abstract private method compilation error | 50% | [abstract-private-method-illegal.md](Core_Java/OOP/abstract-private-method-illegal.md) |

---

### Multithreading & Concurrency (Guides)

| Priority | Topic | Frequency | File |
|----------|-------|-----------|------|
| 🔥 CRITICAL | Full concurrency guide | 60% | [_Guides/java-multithreading-concurrency-guide.md](Core_Java/Multithreading_Concurrency/_Guides/java-multithreading-concurrency-guide.md) |
| ✅ IMPORTANT | Race conditions and visibility | 55% | [race-conditions-thread-problems.md](Core_Java/Multithreading_Concurrency/race-conditions-thread-problems.md) |
| ✅ IMPORTANT | Volatile vs atomic | 50% | [_Guides/java-volatile-atomic-interview.md](Core_Java/Multithreading_Concurrency/_Guides/java-volatile-atomic-interview.md) |

### Multithreading & Concurrency (Focused Notes)

| Priority | Topic | Frequency | File |
|----------|-------|-----------|------|
| 🔥 CRITICAL | Virtual threads | 80% | [virtual-threads-basics.md](Core_Java/Multithreading_Concurrency/virtual-threads-basics.md) |
| 🔥 CRITICAL | Executors and thread pools | 80% | [executors-thread-pools.md](Core_Java/Multithreading_Concurrency/executors-thread-pools.md) |
| 🔥 CRITICAL | CompletableFuture basics | 75% | [asynchronous-programming-futures.md](Core_Java/Multithreading_Concurrency/asynchronous-programming-futures.md) |
| ✅ IMPORTANT | Fork/Join and work stealing | 70% | [fork-join-framework.md](Core_Java/Multithreading_Concurrency/fork-join-framework.md) |
| ✅ IMPORTANT | Concurrent collections | 65% | [concurrent-collections.md](Core_Java/Multithreading_Concurrency/concurrent-collections.md) |
| ✅ IMPORTANT | Race conditions and visibility | 65% | [race-conditions-thread-problems.md](Core_Java/Multithreading_Concurrency/race-conditions-thread-problems.md) |
| ✅ IMPORTANT | Synchronization | 65% | [thread-synchronization.md](Core_Java/Multithreading_Concurrency/thread-synchronization.md) |
| 👍 GOOD TO KNOW | Producer-consumer pattern | 60% | [producer-consumer-pattern.md](Core_Java/Multithreading_Concurrency/producer-consumer-pattern.md) |
| 👍 GOOD TO KNOW | Deadlock scenarios and prevention | 58% | [deadlock-scenarios-prevention.md](Core_Java/Multithreading_Concurrency/deadlock-scenarios-prevention.md) |
| 👍 GOOD TO KNOW | ThreadLocal usage patterns | 55% | [threadlocal-usage-patterns.md](Core_Java/Multithreading_Concurrency/threadlocal-usage-patterns.md) |
| 👍 GOOD TO KNOW | Synchronized methods thread blocking | 52% | [synchronized-methods-thread-blocking.md](Core_Java/Multithreading_Concurrency/synchronized-methods-thread-blocking.md) |
| 🔵 ADVANCED | Project Loom overview | 70% | [project-loom-overview.md](Core_Java/Multithreading_Concurrency/project-loom-overview.md) |

---

### Spring (Interview Topics)

| Priority | Topic | Frequency | File |
|----------|-------|-----------|------|
| 🔥 CRITICAL | @Transactional proxy flow | 75% | [Q3_transactional_proxy_flow.md](Spring/Q3_transactional_proxy_flow.md) |
| 🔥 CRITICAL | Auto-configuration | 72% | [Q2_springboot_autoconfiguration.md](Spring/Q2_springboot_autoconfiguration.md) |
| ✅ IMPORTANT | Interceptor implementation | 70% | [Q1_interceptor_implementation.md](Spring/Q1_interceptor_implementation.md) |
| ✅ IMPORTANT | AOP execution time logging | 65% | [Q4_aop_log_execution_time.md](Spring/Q4_aop_log_execution_time.md) |

#### Additional Spring Topics

| Priority | Topic | Frequency | File |
|----------|-------|-----------|------|
| 🔵 ADVANCED | WebFlux senior interview questions | 65% | [webflux-senior-interview-questions.md](Spring/webflux-senior-interview-questions.md) |

---

### Algorithms (LeetCode)

| Priority | Question | Frequency | File |
|----------|----------|-----------|------|
| ✅ IMPORTANT | Max repeated subarray (718) | — | [Q1_max_repeated_subarray.md](Algorithms_LeetCode/Q1_max_repeated_subarray.md) |
| ✅ IMPORTANT | Count subarrays with K odd (1248) | — | [Q2_count_subarrays_k_odd.md](Algorithms_LeetCode/Q2_count_subarrays_k_odd.md) |
| ✅ IMPORTANT | Move zeroes (283) | — | [Q3_move_zeroes.md](Algorithms_LeetCode/Q3_move_zeroes.md) |
| ✅ IMPORTANT | Max vowels in substring (sliding window) | 65% | [Q4_max_vowels_in_substring_k.md](Algorithms_LeetCode/Q4_max_vowels_in_substring_k.md) |
| ✅ IMPORTANT | Subset sum (1D DP) | 70% | [Q14_subset_sum_dp.md](Algorithms_LeetCode/Q14_subset_sum_dp.md) |
| ✅ IMPORTANT | Partition equal subset sum (416) | 75% | [Q15_partition_equal_subset_sum.md](Algorithms_LeetCode/Q15_partition_equal_subset_sum.md) |

---

### Modern Java 8-21 (Bonus)

| Priority | Question | Frequency | File |
|----------|----------|-----------|------|
| ✅ IMPORTANT | Interface evolution (Q1-Q5) | — | [JAVA8TO21_QA_REFERENCE.md](Java8to21/JAVA8TO21_QA_REFERENCE.md) |
| ✅ IMPORTANT | Records | — | [Q6_records_introduced.md](Java8to21/Q6_records_introduced.md) |
| ✅ IMPORTANT | Sealed classes | — | [Q7_sealed_classes.md](Java8to21/Q7_sealed_classes.md) |
| ✅ IMPORTANT | Pattern matching | — | [Q8_pattern_matching.md](Java8to21/Q8_pattern_matching.md) |
| ✅ IMPORTANT | Text blocks | — | [Q9_text_blocks.md](Java8to21/Q9_text_blocks.md) |
| ✅ IMPORTANT | CompletableFuture (Q10-Q12) | — | [JAVA8TO21_QA_REFERENCE.md](Java8to21/JAVA8TO21_QA_REFERENCE.md) |
| ✅ IMPORTANT | Stream interview problem | 60% | [Q65_find_non_repeated_character.md](Java8to21/Q65_find_non_repeated_character.md) |

---

### Frontend Integration (React/TypeScript)

| Priority | Topic | Frequency | File |
|----------|-------|-----------|------|
| 👍 GOOD TO KNOW | TypeScript JSX compilation | 65% | [Q1_typescript_jsx_compilation.md](react_javascript/Q1_typescript_jsx_compilation.md) |
| 👍 GOOD TO KNOW | TSX compilation pipeline | 55% | [Q2_tsx_compilation_pipeline.md](react_javascript/Q2_tsx_compilation_pipeline.md) |

---

**Last Updated:** March 5, 2026  
**Interview Readiness:** Senior/Staff Engineer Level
