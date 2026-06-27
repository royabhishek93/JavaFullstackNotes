# BookMyShow System Design - Interview Questions Index

## For 15+ Years Experienced Developer

---

## 📚 Question Categories

### 🔐 Concurrency & Data Consistency (Critical)
1. ✅ **HIGH_Q01_prevent_double_booking.md** - How do you prevent double-booking when two users click the same seat simultaneously?
2. ✅ **HIGH_Q02_payment_atomicity.md** - Design the payment flow ensuring atomicity (seat reserved OR payment fails, never both)
3. **MED_Q03_isolation_levels.md** - Why SERIALIZABLE vs READ_COMMITTED for booking transactions?
4. **MED_Q04_distributed_locks.md** - How would you handle seat booking across multiple data centers?
5. **MED_Q05_deadlock_handling.md** - User A books seats [1,2,3], User B books [3,2,1]. How to prevent deadlock?

### 💳 Payment & Financial Transactions
6. **MED_Q06_payment_gateway_timeout_how_to_determine_if_user_was_charged.md** - Payment gateway times out. How do you determine if user was charged?
7. **MED_Q07_refund_logic_user_cancels_2_hours_before_show.md** - User cancels 2 hours before show. Design the refund flow.
8. **MED_Q08_idempotency_patterns_prevent_duplicate_operations.md** - User's network glitches, payment request sent 3 times. Prevent triple charging.
9. **MED_Q09_payment_webhook_handling_stripe_razorpay_callbacks.md** - Design webhook handling for payment confirmations with retry logic.
10. **MED_Q10_partial_refund_user_booked_5_seats_cancels_2.md** - User booked 5 seats, cancels 2. Handle partial refunds.

### 🔍 Search & Performance
11. **MED_Q11_search_optimization_avengers_in_mumbai_returning_10m_results_in_200ms.md** - Search "Avengers in Mumbai" returning 10 million results. Optimize to <200ms.
12. **HIGH_Q12_elasticsearch_vs_sql_why_not_postgresql_like_query.md** - Why Elasticsearch for search instead of PostgreSQL?
13. **MED_Q13_faceted_search_multiple_filters_simultaneously.md** - Implement filters: genre, language, theater, rating, distance simultaneously.
14. **MED_Q14_autocomplete_search_suggestions_with_100k_concurrent_users.md** - Design autocomplete for movie search with 100k concurrent users.
15. **MED_Q15_geo_spatial_search_find_theaters_within_5km_sorted_by_distance.md** - Find theaters within 5km radius, sorted by distance.

### 💾 Caching Strategy
16. **HIGH_Q16_cache_invalidation_seat_5_booked_update_all_viewing_users.md** - Seat 5 booked. How do you update cache for all users viewing that show?
17. **MED_Q17_cache_stampede_10k_requests_hit_cache_miss_simultaneously.md** - 10k users hit cache miss simultaneously for popular show. Prevent cache stampede.
18. **MED_Q18_cache_aside_vs_write_through_for_seat_availability.md** - Write-through vs Cache-aside for seat availability. Which one and why?
19. **MED_Q19_redis_vs_memcached_for_bookmyshow.md** - Why Redis over Memcached for BookMyShow?
20. **MED_Q20_cache_warming_pre_warm_before_avengers_premiere.md** - New Avengers movie announced. How do you pre-warm cache before ticket sales open?

### ⚡ Real-time Updates
21. **HIGH_Q21_websocket_architecture_push_seat_updates_to_100k_concurrent_users.md** - 50k users watching seat map. Design WebSocket infrastructure.
22. **MED_Q22_redis_pub_sub_vs_message_queue_when_to_use_which.md** - How does Redis Pub/Sub enable real-time seat updates?
23. **MED_Q23_sse_vs_websocket_trade_offs_for_real_time_seat_updates.md** - WebSocket server crashes. How do connected users reconnect?
24. **MED_Q24_optimistic_ui_updates_show_seat_as_booked_immediately_revert_if_fails.md** - WebSocket vs Server-Sent Events vs Long Polling for seat updates. Compare.
25. **MED_Q25_real_time_seat_status_synchronization_handle_10k_users_viewing_same_show.md** - User clicks seat, show it as "selected" before server confirms. Handle race conditions.

### 🗄️ Database Design & Scaling
26. **HIGH_Q26_database_schema_design_complete_production_ready_schema.md** - Design complete database schema with all entities and relationships.
27. **HIGH_Q27_database_sharding_strategy_scale_to_50k_bookings_sec.md** - Database has 100M bookings. How do you shard?
28. **MED_Q28_read_replicas_scale_show_search_to_1m_queries_sec.md** - Search queries overloading master. Design read replica strategy.
29. **MED_Q29_denormalization_when_to_denormalize_for_performance.md** - Should you store `available_seats` count in `shows` table (denormalized)?
30. **MED_Q30_soft_delete_vs_hard_delete_trade_offs_for_production.md** - User deletes account. Design soft delete with GDPR compliance.

### 📊 High Availability & Scalability
31. **HIGH_Q31_peak_traffic.md** - Avengers premiere: 1M users at 10 AM. Design for 100x traffic spike.
32. **MED_Q32_rate_limiting_prevent_user_from_hammering_booking_api.md** - Implement rate limiting: 10 bookings per user per day, 100 requests/min.
33. **MED_Q33_load_balancer_configuration_health_checks_sticky_sessions.md** - 10 booking service instances. How does load balancer route requests?
34. **MED_Q34_circuit_breaker_payment_gateway_failures.md** - Payment gateway down. Implement circuit breaker pattern.
35. **MED_Q35_bulkhead_pattern_isolate_thread_pools_for_different_operations.md** - Search queries should not affect booking service. Design isolation.

### 🔄 Message Queues & Async Processing
36. **MED_Q36_kafka_architecture_event_streaming_for_bookings.md** - Why Kafka over RabbitMQ for BookMyShow?
37. **MED_Q37_event_sourcing_reconstruct_booking_state_from_events.md** - Should you use event sourcing for booking state changes?
38. **HIGH_Q38_saga_pattern_distributed_transaction_across_services.md** - Implement Saga pattern for: Reserve → Pay → Notify → Generate Ticket.
39. **MED_Q39_dead_letter_queue_dlq_handle_failed_messages.md** - Email notification fails 5 times. Design DLQ and retry logic.
40. **MED_Q40_exactly_once_semantics_prevent_duplicate_processing.md** - Ensure booking confirmation email sent exactly once (not 0, not 2).

### 🎫 Business Logic & Edge Cases
41. **MED_Q41_seat_expiry_release_reserved_seats_after_15_minutes.md** - User reserves seat at 10:00, expires at 10:15. Design expiry job.
42. **MED_Q42_overbooking_strategy_allow_5_overbooking_to_compensate_no_shows.md** - Theater wants to overbook by 5% (airline model). Design overbooking logic.
43. **MED_Q43_group_booking_book_20_seats_together_in_same_row.md** - User wants 10 adjacent seats. How do you lock them atomically?
44. **MED_Q44_discount_codes_apply_percentage_flat_discount_with_validation.md** - 100k users apply "AVENGERS50" code at 10 AM. Limit to first 1000 users.
45. **MED_Q45_dynamic_pricing_increase_price_based_on_demand.md** - Implement surge pricing: Friday night = 1.5x, Tuesday matinee = 0.8x.

### 🔐 Security & Compliance
46. **MED_Q46_pci_compliance_handle_credit_card_data_securely.md** - Store payment card details? How to be PCI-DSS compliant?
47. **MED_Q47_scalping_prevention_prevent_bots_from_bulk_buying_tickets.md** - Bots booking all seats for resale. Detect and prevent.
48. **MED_Q48_gdpr_compliance_right_to_deletion_data_export.md** - European user requests data export/deletion. Implement GDPR.
49. **MED_Q49_authentication_and_authorization_jwt_tokens_session_management.md** - Design JWT-based auth with refresh tokens for mobile app.
50. **MED_Q50_sql_injection_prevention_secure_database_queries.md** - User enters `' OR '1'='1` in movie search. Prevent SQL injection.

### 📈 Monitoring & Observability
51. **MED_Q51_metrics_and_monitoring_what_metrics_to_track_for_bookmyshow.md** - What metrics would you monitor in production?
52. **MED_Q52_distributed_tracing_track_request_across_microservices.md** - Request spans: API Gateway → Booking → Payment → Notification. Implement tracing.
53. **MED_Q53_centralized_logging_elk_stack_for_log_aggregation.md** - What should you log for booking failures?
54. **MED_Q54_alerting_when_to_alert_ops_team.md** - Set up alerts for: booking latency >1s, payment failures >5%, cache miss rate >20%.
55. **MED_Q55_chaos_engineering_test_system_resilience.md** - How would you test system resilience (kill database, kill cache, etc.)?

### 🏗️ Architecture & Design Patterns
56. **MED_Q56_monolith_to_microservices_migration_strategy_for_bookmyshow.md** - Should BookMyShow be microservices or monolith?
57. **MED_Q57_service_boundaries_how_to_split_services_correctly.md** - How do you decide boundaries: Search, Booking, Payment, User, Notification services?
58. **MED_Q58_api_gateway_single_entry_point_for_microservices.md** - Design API Gateway: rate limiting, auth, routing, circuit breaking.
59. **MED_Q59_cqrs_pattern_separate_read_and_write_models.md** - Should you separate read/write models for bookings?
60. **MED_Q60_strangler_fig_pattern_gradual_migration_from_legacy.md** - Migrate legacy monolith to microservices. Design migration strategy.

### 🌍 Multi-Region & Geo-Distribution
61. **HIGH_Q61_multi_region_architecture_deploy_bookmyshow_globally.md** - Deploy in US-East, EU-West, APAC-Singapore. Design data sync.
62. **MED_Q62_active_active_vs_active_passive_which_for_bookmyshow.md** - Active-active vs Active-passive for disaster recovery. Which one?
63. **MED_Q63_cross_region_latency_minimize_data_transfer.md** - User in India searching movies in India. Optimize to <50ms.
64. **MED_Q64_cdn_strategy_cloudfront_for_global_delivery.md** - What assets should go to CDN? (posters, videos, seat maps?)
65. **MED_Q65_database_replication_cross_region_data_sync.md** - Master in Mumbai, replica in Delhi. Handle replication lag.

### 🧪 Testing Strategy
66. **MED_Q66_integration_tests_test_booking_flow_end_to_end.md** - Test double-booking scenario with 2 concurrent threads.
67. **MED_Q67_load_testing_jmeter_gatling_for_100k_concurrent_users.md** - Simulate 1M concurrent users for Avengers premiere. Tools and strategy.
68. **LOW_Q68_chaos_testing.md** - Kill random service instance during peak. System should recover.
69. **LOW_Q69_contract_testing.md** - Payment service API changes. How do you ensure compatibility?
70. **LOW_Q70_canary_deployment.md** - Deploy new booking service version to 5% traffic first. How?

### 💡 Advanced Topics
71. **LOW_Q71_capacity_planning.md** - Estimate servers needed for 10M daily bookings.
72. **LOW_Q72_cost_optimization.md** - Monthly AWS bill is $500k. Optimize without affecting UX.
73. **LOW_Q73_zero_downtime_migration.md** - Migrate 100M bookings from MySQL to PostgreSQL with zero downtime.
74. **LOW_Q74_blue_green_deployment.md** - Deploy new version without downtime. Rollback in 30 seconds.
75. **LOW_Q75_feature_flags.md** - Release "seat selection" feature to 10% users first. Design feature flags.

---

## 🎯 How to Use This Guide

### For Candidates:
1. **Start with Critical Questions** (Q01-Q05, Q26-Q30)
2. **Practice drawing diagrams** for architecture questions
3. **Write actual code** for implementation questions
4. **Time yourself**: 5-10 minutes per question
5. **Practice explaining trade-offs** (not just one solution)

### For Interviewers:
- **Junior (0-3 years)**: Q01, Q11, Q26, Q31, Q51
- **Mid (3-7 years)**: Q02, Q06, Q12, Q16, Q32, Q36, Q56
- **Senior (7-12 years)**: Q03, Q07, Q17, Q21, Q33, Q37, Q57, Q61
- **Staff/Principal (12+ years)**: Q04, Q08, Q22, Q34, Q38, Q58, Q62, Q71

---

## 📊 Question Difficulty Distribution

```
┌─────────────────┬───────┬──────────────────────────────────┐
│     Level       │ Count │          Question Numbers         │
├─────────────────┼───────┼──────────────────────────────────┤
│ ⭐ Easy         │   5   │ Q11, Q26, Q51, Q56, Q66          │
├─────────────────┼───────┼──────────────────────────────────┤
│ ⭐⭐ Medium     │  30   │ Q01, Q06, Q12-Q15, Q16, Q27-Q30, │
│                 │       │ Q31, Q32, Q41-Q45, Q46-Q50, Q67  │
├─────────────────┼───────┼──────────────────────────────────┤
│ ⭐⭐⭐ Hard     │  25   │ Q02, Q03, Q07-Q10, Q17-Q20,      │
│                 │       │ Q21-Q25, Q33-Q40, Q52-Q55, Q68   │
├─────────────────┼───────┼──────────────────────────────────┤
│ ⭐⭐⭐⭐ Expert │  15   │ Q04, Q05, Q22, Q34, Q38, Q57-Q65,│
│                 │       │ Q69-Q75                          │
└─────────────────┴───────┴──────────────────────────────────┘
```

---

## 🔥 Top 10 Most Asked Questions in FAANG Interviews

1. **Q01** - Prevent double-booking (race conditions)
2. **Q02** - Payment atomicity (distributed transactions)
3. **Q31** - Handle peak traffic (scalability)
4. **Q16** - Cache invalidation (caching strategy)
5. **Q26** - Database schema design (fundamentals)
6. **Q27** - Sharding strategy (scaling databases)
7. **Q21** - WebSocket architecture (real-time updates)
8. **Q12** - Elasticsearch vs SQL (technology choices)
9. **Q38** - Saga pattern (distributed systems)
10. **Q61** - Multi-region deployment (global scale)

---

## 💼 Question-to-Company Mapping

| Company | Typical Questions |
|---------|------------------|
| **Netflix** | Q31 (peak traffic), Q61 (multi-region), Q34 (circuit breaker), Q52 (distributed tracing) |
| **Uber** | Q15 (geospatial), Q45 (dynamic pricing), Q32 (rate limiting), Q71 (capacity planning) |
| **Amazon** | Q01 (concurrency), Q27 (sharding), Q56 (architecture), Q72 (cost optimization) |
| **Meta** | Q21 (real-time), Q22 (Pub/Sub), Q31 (scale), Q68 (chaos testing) |
| **Google** | Q04 (distributed locks), Q38 (saga), Q62 (multi-DC), Q73 (migrations) |
| **BookMyShow** | All questions relevant! 😄 |

---

## 📝 Answer Format Template

Each question file follows this structure:

```markdown
# Question X: [Question Title]

## Difficulty Level: ⭐⭐⭐ (Senior)
## Expected Answer Duration: 5-7 minutes

---

## ❌ Poor Answer (Junior Level):
[What NOT to say]

## ✅ Good Answer (Senior Level):
[Expected answer with code, diagrams]

## 🚀 Advanced Follow-up Points:
[Deep dive topics for staff/principal level]

## 🔥 Common Mistakes:
[Red flags to avoid]

## 💡 Key Takeaway:
[Summary for interview]
```

---

## 🎓 Study Plan (2 Weeks)

### Week 1: Fundamentals
- **Day 1-2**: Q01-Q05 (Concurrency)
- **Day 3-4**: Q26-Q30 (Database design)
- **Day 5-6**: Q11-Q15 (Search & performance)
- **Day 7**: Review and practice explaining

### Week 2: Advanced Topics
- **Day 8-9**: Q21-Q25 (Real-time), Q31-Q35 (Scale)
- **Day 10-11**: Q36-Q40 (Async), Q06-Q10 (Payment)
- **Day 12-13**: Q56-Q60 (Architecture), Q61-Q65 (Multi-region)
- **Day 14**: Mock interviews with all categories

---

## 🎯 Success Criteria

After completing this guide, you should be able to:

✅ Design a production-ready booking system from scratch  
✅ Handle 1M concurrent users with <1s latency  
✅ Prevent race conditions and double-bookings  
✅ Design payment flows with atomicity guarantees  
✅ Scale databases with sharding and replication  
✅ Implement real-time updates with WebSockets  
✅ Optimize search to <200ms with caching  
✅ Handle multi-region deployments  
✅ Debug production issues with monitoring  
✅ Pass staff/principal engineer interviews at FAANG  

---

**Good luck! 🚀**

_Last Updated: 2024-04-05_
