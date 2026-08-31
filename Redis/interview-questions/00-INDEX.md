# Redis Interview Questions — Master Index (Ranked by Importance, 15-YOE Interview)

All 54 questions live flat in this folder. The **numeric prefix is the priority order** for a 15+ years-of-experience developer interview — start at `01` and work down. Lower numbers are asked more often, probe more fundamental correctness/architecture skills, or are the classic "sounds simple but reveals real experience" gotchas senior interviewers reach for first.

Each file contains: a direct answer, an easy-to-understand explanation with an analogy, an ASCII diagram, a production-style code/command example, and a note on why interviewers ask it.

## Tier 1 — Concurrency & Correctness Fundamentals (almost always asked first)
- [01 — How do you stop two app servers from both thinking they hold the same lock?](01-how-do-you-stop-two-app-servers-from-both-thinking-they-hold-the-same-lock.md)
- [02 — How do you build a safe distributed lock that survives a crashed lock holder?](02-how-do-you-build-a-safe-distributed-lock-that-survives-a-crashed-lock-holder.md)
- [03 — Why does SET NX silently do nothing when you expect it to overwrite a stale lock? *(trap)*](03-why-does-set-nx-silently-do-nothing-when-you-expect-it-to-overwrite-a-stale-lock.md)
- [04 — Why does a manual get-then-increment-then-set lose page view counts under load? *(trap)*](04-why-does-a-manual-get-then-increment-then-set-lose-page-view-counts-under-load.md)
- [05 — Why is running the KEYS command in production to find matching cache keys dangerous? *(trap)*](05-why-is-running-the-keys-command-in-production-to-find-matching-cache-keys-dangerous.md)

## Tier 2 — Redis Streams: Reliability & Consumer Groups (staff-level system design)
- [06 — How do you guarantee a voucher is not verified twice when a worker crashes after calling the partner API?](06-how-do-you-guarantee-a-voucher-is-not-verified-twice-when-a-worker-crashes-after-calling-the-partner-api.md)
- [07 — How do you redesign order processing so a crashed consumer never causes a double charge?](07-how-do-you-redesign-order-processing-so-a-crashed-consumer-never-causes-a-double-charge.md)
- [08 — Does calling XACK delete the entry from the Redis stream? *(trap)*](08-does-calling-xack-delete-the-entry-from-the-redis-stream.md)
- [09 — Why is worker A processing everything while worker B sits idle in the same consumer group?](09-why-is-worker-a-processing-everything-while-worker-b-sits-idle-in-the-same-consumer-group.md)
- [10 — How do you recover messages from a worker that crashed and never called XACK?](10-how-do-you-recover-messages-from-a-worker-that-crashed-and-never-called-xack.md)
- [11 — Why does setting XAUTOCLAIM idle time to 5 seconds cause orders to be processed twice? *(trap)*](11-why-does-setting-xautoclaim-idle-time-to-5-seconds-cause-orders-to-be-processed-twice.md)
- [12 — Can XTRIM delete a stream entry that a consumer group has not processed yet? *(trap)*](12-can-xtrim-delete-a-stream-entry-that-a-consumer-group-has-not-processed-yet.md)
- [13 — Should you use Redis Streams or Redis Pub/Sub for a notification service that cannot lose messages?](13-should-you-use-redis-streams-or-redis-pub-sub-for-a-notification-service-that-cannot-lose-messages.md)
- [14 — When should you choose Kafka over Redis Streams for a 90-day replayable event log?](14-when-should-you-choose-kafka-over-redis-streams-for-a-90-day-replayable-event-log.md)

## Tier 3 — Choosing the Right Messaging Tool (Pub/Sub fit-for-purpose)
- [15 — Is Redis Pub/Sub a good fit for an order-processing pipeline that must not lose orders?](15-is-redis-pub-sub-a-good-fit-for-an-order-processing-pipeline-that-must-not-lose-orders.md)
- [16 — Is Redis Pub/Sub a good fit for a "user is typing…" indicator in a chat app?](16-is-redis-pub-sub-a-good-fit-for-a-user-is-typing-indicator-in-a-chat-app.md)
- [17 — What happens to chat messages published while a subscriber is disconnected for two minutes?](17-what-happens-to-chat-messages-published-while-a-subscriber-is-disconnected-for-two-minutes.md)
- [18 — How do you redesign a notification system so offline users do not lose messages?](18-how-do-you-redesign-a-notification-system-so-offline-users-do-not-lose-messages.md)
- [19 — Why does fire-and-forget mean Redis never tells the publisher if anyone actually got the message? *(trap)*](19-why-does-fire-and-forget-mean-redis-never-tells-the-publisher-if-anyone-actually-got-the-message.md)
- [20 — Why does a message published to an empty Redis channel not appear later like a Kafka consumer would expect? *(trap)*](20-why-does-a-message-published-to-an-empty-redis-channel-not-appear-later-like-a-kafka-consumer-would-expect.md)
- [21 — Why does publishing to a channel with zero subscribers silently lose the message? *(trap)*](21-why-does-publishing-to-a-channel-with-zero-subscribers-silently-lose-the-message.md)

## Tier 4 — Real-Time Delivery vs Durable History (chat/notification architecture)
- [22 — Should chat history be stored using the same mechanism that delivers real-time messages?](22-should-chat-history-be-stored-using-the-same-mechanism-that-delivers-real-time-messages.md)
- [23 — How do you design a chat backend that uses Redis for live delivery and a database for history?](23-how-do-you-design-a-chat-backend-that-uses-redis-for-live-delivery-and-a-database-for-history.md)
- [24 — Why does mixing the real-time delivery problem with the chat-history problem cause confusion? *(trap)*](24-why-does-mixing-the-real-time-delivery-problem-with-the-chat-history-problem-cause-confusion.md)

## Tier 5 — Redis vs Kafka Decision-Making
- [25 — Why does Redis respond faster than Kafka for a low-latency chat feature?](25-why-does-redis-respond-faster-than-kafka-for-a-low-latency-chat-feature.md)
- [26 — Why would a fintech order book still choose Kafka despite Redis being faster?](26-why-would-a-fintech-order-book-still-choose-kafka-despite-redis-being-faster.md)
- [27 — Why is creating a Kafka topic per conversation more expensive than using a Redis channel?](27-why-is-creating-a-kafka-topic-per-conversation-more-expensive-than-using-a-redis-channel.md)
- [28 — Why is deleting a Kafka topic after a chat ends not as simple as it sounds?](28-why-is-deleting-a-kafka-topic-after-a-chat-ends-not-as-simple-as-it-sounds.md)
- [29 — Why does a junior engineer assume a Redis channel needs to be deleted like a Kafka topic? *(trap)*](29-why-does-a-junior-engineer-assume-a-redis-channel-needs-to-be-deleted-like-a-kafka-topic.md)

## Tier 6 — Caching Patterns & Production Safety (everyday practical Redis)
- [30 — How do you speed up a slow third-party API call without changing the third-party service?](30-how-do-you-speed-up-a-slow-third-party-api-call-without-changing-the-third-party-service.md)
- [31 — How do you decide the right TTL so users never see stale pricing data?](31-how-do-you-decide-the-right-ttl-so-users-never-see-stale-pricing-data.md)
- [32 — Why does forgetting to set an expiry on a cached response eventually break the feature? *(trap)*](32-why-does-forgetting-to-set-an-expiry-on-a-cached-response-eventually-break-the-feature.md)
- [33 — Why does a cached unread-message count go out of sync with the real database? *(trap)*](33-why-does-a-cached-unread-message-count-go-out-of-sync-with-the-real-database.md)
- [34 — Why does writing every GPS update straight to Postgres slow down a live delivery-tracking app?](34-why-does-writing-every-gps-update-straight-to-postgres-slow-down-a-live-delivery-tracking-app.md)
- [35 — How do you design a system where Redis holds live location and Postgres holds the final route?](35-how-do-you-design-a-system-where-redis-holds-live-location-and-postgres-holds-the-final-route.md)
- [36 — Why does a Redis node crash wipe out your cache even though you thought it was durable? *(trap)*](36-why-does-a-redis-node-crash-wipe-out-your-cache-even-though-you-thought-it-was-durable.md)

## Tier 7 — Scaling Real-Time Systems (WebSockets across instances)
- [37 — How do two Node.js instances deliver a message to each other's connected users?](37-how-do-two-node-js-instances-deliver-a-message-to-each-others-connected-users.md)
- [38 — How do you scale WebSocket connections across ten Node.js instances behind a load balancer?](38-how-do-you-scale-websocket-connections-across-ten-node-js-instances-behind-a-load-balancer.md)
- [39 — Why does a notification published while a service instance is restarting never arrive? *(trap)*](39-why-does-a-notification-published-while-a-service-instance-is-restarting-never-arrive.md)

## Tier 8 — Data Structure Selection (Sorted Sets, Hash, Set, HyperLogLog, Geo)
- [40 — How do you build a live leaderboard that re-ranks players automatically?](40-how-do-you-build-a-live-leaderboard-that-re-ranks-players-automatically.md)
- [41 — How do you page through a leaderboard of ten million players without loading it all into memory?](41-how-do-you-page-through-a-leaderboard-of-ten-million-players-without-loading-it-all-into-memory.md)
- [42 — Why do two players with the same score not appear in insertion order on the leaderboard? *(trap)*](42-why-do-two-players-with-the-same-score-not-appear-in-insertion-order-on-the-leaderboard.md)
- [43 — How do you store a user profile in Redis without creating a key per field?](43-how-do-you-store-a-user-profile-in-redis-without-creating-a-key-per-field.md)
- [44 — How do you prevent a coupon code from ever being redeemed twice across multiple users?](44-how-do-you-prevent-a-coupon-code-from-ever-being-redeemed-twice-across-multiple-users.md)
- [45 — Which Redis data type should you use to count millions of unique daily visitors with very low memory?](45-which-redis-data-type-should-you-use-to-count-millions-of-unique-daily-visitors-with-very-low-memory.md)
- [46 — How do you find restaurants within 5 km of a customer without writing distance math yourself?](46-how-do-you-find-restaurants-within-5-km-of-a-customer-without-writing-distance-math-yourself.md)
- [47 — How do you find all restaurants within 5 km of a customer's current location?](47-how-do-you-find-all-restaurants-within-5-km-of-a-customers-current-location.md)
- [48 — Why should cache keys follow an entity:id naming convention in a growing codebase?](48-why-should-cache-keys-follow-an-entity-colon-id-naming-convention-in-a-growing-codebase.md)

## Tier 9 — Pub/Sub Mechanics & Niche Gotchas
- [49 — How do you subscribe to every channel ending in _chat without hardcoding each channel name?](49-how-do-you-subscribe-to-every-channel-ending-in-chat-without-hardcoding-each-channel-name.md)
- [50 — Why do both a logging service and a notification service receive a message neither fully needs?](50-why-do-both-a-logging-service-and-a-notification-service-receive-a-message-neither-fully-needs.md)
- [51 — Why doesn't Redis require you to explicitly create a channel before publishing to it? *(trap)*](51-why-doesnt-redis-require-you-to-explicitly-create-a-channel-before-publishing-to-it.md)

## Tier 10 — Architecture & Ops Fundamentals (client-server, replication, install)
- [52 — What role does a Spring Boot application play in the Redis client-server architecture?](52-what-role-does-a-spring-boot-application-play-in-the-redis-client-server-architecture.md)
- [53 — How does replica failover prevent total data loss when the Redis master crashes?](53-how-does-replica-failover-prevent-total-data-loss-when-the-redis-master-crashes.md)
- [54 — Why doesn't a snap-installed Redis give you full control over redis.conf? *(trap)*](54-why-doesnt-a-snap-installed-redis-give-you-full-control-over-redis-conf.md)

---

## How to use this for interview prep
1. Work through **01 → 54 in order** — the numbering *is* a study plan, front-loaded with what a 15-YOE interviewer asks first (correctness under concurrency, then Streams reliability, then messaging-tool selection, then everyday caching/production-safety, then data-structure fluency, then ops fundamentals).
2. Within each question, read the direct answer first, then the diagram, then try to explain the production example out loud — that's the format most system-design interviews actually use.
3. Files marked *(trap)* in this index are the classic "sounds obvious but isn't" gotchas — treat these as a final review pass the night before an interview.
4. Every diagram is plain ASCII, so it renders correctly in any editor, terminal, or plain-text viewer — no special Markdown plugin required.
