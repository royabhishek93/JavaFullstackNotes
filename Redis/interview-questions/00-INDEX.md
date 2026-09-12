# Redis Interview Questions — Master Index (Ranked by Importance, 15-YOE Interview)

51 questions live flat in this folder (deduplicated from an earlier 54 — see note at the bottom). The **numeric prefix is the priority order** for a 15+ years-of-experience developer interview — start at `01` and work down.

**Every file follows the same fixed template**, so all four things you asked for are answered in every single question:
- **Why do we need it?** → the *Direct Answer* + *Why Interviewers Ask This* sections
- **How does it overcome the problem?** → the *Direct Answer* + *Diagram*
- **Real production issue example** → the *Production Example* section (a concrete app: voucher/payment service, chat app, delivery tracking, e-commerce cache, etc., often with real code/commands)
- **Easy English explanation** → the *Easy Explanation* section, always built around a plain, non-technical analogy (a bathroom key, a whiteboard vs filing cabinet, a radio broadcast, a librarian, etc.)

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
- [17 — What happens to chat messages published while a subscriber is disconnected for two minutes? *(includes the "deployment restart" production variant)*](17-what-happens-to-chat-messages-published-while-a-subscriber-is-disconnected-for-two-minutes.md)
- [18 — How do you redesign a notification system so offline users do not lose messages?](18-how-do-you-redesign-a-notification-system-so-offline-users-do-not-lose-messages.md)
- [19 — Why does fire-and-forget mean Redis never tells the publisher if anyone actually got the message? *(trap)*](19-why-does-fire-and-forget-mean-redis-never-tells-the-publisher-if-anyone-actually-got-the-message.md)
- [20 — Why does publishing to a channel with zero subscribers silently lose the message? *(trap, includes the Kafka-migration mental-model mistake)*](20-why-does-publishing-to-a-channel-with-zero-subscribers-silently-lose-the-message.md)

## Tier 4 — Real-Time Delivery vs Durable History (chat/notification architecture)
- [21 — Should chat history be stored using the same mechanism that delivers real-time messages?](21-should-chat-history-be-stored-using-the-same-mechanism-that-delivers-real-time-messages.md)
- [22 — How do you design a chat backend that uses Redis for live delivery and a database for history?](22-how-do-you-design-a-chat-backend-that-uses-redis-for-live-delivery-and-a-database-for-history.md)
- [23 — Why does mixing the real-time delivery problem with the chat-history problem cause confusion? *(trap)*](23-why-does-mixing-the-real-time-delivery-problem-with-the-chat-history-problem-cause-confusion.md)

## Tier 5 — Redis vs Kafka Decision-Making
- [24 — Why does Redis respond faster than Kafka for a low-latency chat feature?](24-why-does-redis-respond-faster-than-kafka-for-a-low-latency-chat-feature.md)
- [25 — Why would a fintech order book still choose Kafka despite Redis being faster?](25-why-would-a-fintech-order-book-still-choose-kafka-despite-redis-being-faster.md)
- [26 — Why is creating a Kafka topic per conversation more expensive than using a Redis channel?](26-why-is-creating-a-kafka-topic-per-conversation-more-expensive-than-using-a-redis-channel.md)
- [27 — Why is deleting a Kafka topic after a chat ends not as simple as it sounds?](27-why-is-deleting-a-kafka-topic-after-a-chat-ends-not-as-simple-as-it-sounds.md)
- [28 — Why does a junior engineer assume a Redis channel needs to be deleted like a Kafka topic? *(trap)*](28-why-does-a-junior-engineer-assume-a-redis-channel-needs-to-be-deleted-like-a-kafka-topic.md)

## Tier 6 — Caching Patterns & Production Safety (everyday practical Redis)
- [29 — How do you speed up a slow third-party API call without changing the third-party service?](29-how-do-you-speed-up-a-slow-third-party-api-call-without-changing-the-third-party-service.md)
- [30 — How do you decide the right TTL so users never see stale pricing data?](30-how-do-you-decide-the-right-ttl-so-users-never-see-stale-pricing-data.md)
- [31 — Why does forgetting to set an expiry on a cached response eventually break the feature? *(trap)*](31-why-does-forgetting-to-set-an-expiry-on-a-cached-response-eventually-break-the-feature.md)
- [32 — Why does a cached unread-message count go out of sync with the real database? *(trap)*](32-why-does-a-cached-unread-message-count-go-out-of-sync-with-the-real-database.md)
- [33 — Why does writing every GPS update straight to Postgres slow down a live delivery-tracking app?](33-why-does-writing-every-gps-update-straight-to-postgres-slow-down-a-live-delivery-tracking-app.md)
- [34 — How do you design a system where Redis holds live location and Postgres holds the final route?](34-how-do-you-design-a-system-where-redis-holds-live-location-and-postgres-holds-the-final-route.md)
- [35 — Why does a Redis node crash wipe out your cache even though you thought it was durable? *(trap)*](35-why-does-a-redis-node-crash-wipe-out-your-cache-even-though-you-thought-it-was-durable.md)

## Tier 7 — Scaling Real-Time Systems (WebSockets across instances)
- [36 — How do two Node.js instances deliver a message to each other's connected users?](36-how-do-two-node-js-instances-deliver-a-message-to-each-others-connected-users.md)
- [37 — How do you scale WebSocket connections across ten Node.js instances behind a load balancer?](37-how-do-you-scale-websocket-connections-across-ten-node-js-instances-behind-a-load-balancer.md)

## Tier 8 — Data Structure Selection (Sorted Sets, Hash, Set, HyperLogLog, Geo)
- [38 — How do you build a live leaderboard that re-ranks players automatically?](38-how-do-you-build-a-live-leaderboard-that-re-ranks-players-automatically.md)
- [39 — How do you page through a leaderboard of ten million players without loading it all into memory?](39-how-do-you-page-through-a-leaderboard-of-ten-million-players-without-loading-it-all-into-memory.md)
- [40 — Why do two players with the same score not appear in insertion order on the leaderboard? *(trap)*](40-why-do-two-players-with-the-same-score-not-appear-in-insertion-order-on-the-leaderboard.md)
- [41 — How do you store a user profile in Redis without creating a key per field?](41-how-do-you-store-a-user-profile-in-redis-without-creating-a-key-per-field.md)
- [42 — How do you prevent a coupon code from ever being redeemed twice across multiple users?](42-how-do-you-prevent-a-coupon-code-from-ever-being-redeemed-twice-across-multiple-users.md)
- [43 — Which Redis data type should you use to count millions of unique daily visitors with very low memory?](43-which-redis-data-type-should-you-use-to-count-millions-of-unique-daily-visitors-with-very-low-memory.md)
- [44 — How do you find restaurants within 5 km of a customer without writing distance math yourself? *(includes both bash and Node.js examples)*](44-how-do-you-find-restaurants-within-5-km-of-a-customer-without-writing-distance-math-yourself.md)
- [45 — Why should cache keys follow an entity:id naming convention in a growing codebase?](45-why-should-cache-keys-follow-an-entity-colon-id-naming-convention-in-a-growing-codebase.md)

## Tier 9 — Pub/Sub Mechanics & Niche Gotchas
- [46 — How do you subscribe to every channel ending in _chat without hardcoding each channel name?](46-how-do-you-subscribe-to-every-channel-ending-in-chat-without-hardcoding-each-channel-name.md)
- [47 — Why do both a logging service and a notification service receive a message neither fully needs?](47-why-do-both-a-logging-service-and-a-notification-service-receive-a-message-neither-fully-needs.md)
- [48 — Why doesn't Redis require you to explicitly create a channel before publishing to it? *(trap)*](48-why-doesnt-redis-require-you-to-explicitly-create-a-channel-before-publishing-to-it.md)

## Tier 10 — Architecture & Ops Fundamentals (client-server, replication, install)
- [49 — What role does a Spring Boot application play in the Redis client-server architecture?](49-what-role-does-a-spring-boot-application-play-in-the-redis-client-server-architecture.md)
- [50 — How does replica failover prevent total data loss when the Redis master crashes?](50-how-does-replica-failover-prevent-total-data-loss-when-the-redis-master-crashes.md)
- [51 — Why doesn't a snap-installed Redis give you full control over redis.conf? *(trap)*](51-why-doesnt-a-snap-installed-redis-give-you-full-control-over-redis-conf.md)

---

## How to use this for interview prep
1. Work through **01 → 51 in order** — the numbering *is* a study plan, front-loaded with what a 15-YOE interviewer asks first (correctness under concurrency, then Streams reliability, then messaging-tool selection, then everyday caching/production-safety, then data-structure fluency, then ops fundamentals).
2. Within each question, read the direct answer first, then the diagram, then try to explain the production example out loud — that's the format most system-design interviews actually use.
3. Files marked *(trap)* are the classic "sounds obvious but isn't" gotchas — treat these as a final review pass the night before an interview.
4. Every diagram is plain ASCII, so it renders correctly in any editor, terminal, or plain-text viewer — no special Markdown plugin required.

## Deduplication note
This set was originally 54 files. Three were near-duplicates of an existing question and were folded into the canonical file instead of kept as separate entries, then the whole set was renumbered 01–51 with no gaps:
- *"Why does a message published to an empty Redis channel not appear later like a Kafka consumer would expect?"* → merged into **20** (its Kafka-migration example is now a paragraph inside file 20).
- *"Why does a notification published while a service instance is restarting never arrive?"* → merged into **17** (its deployment-restart example and Streams-migration code snippet are now inside file 17).
- *"How do you find all restaurants within 5 km of a customer's current location?"* → merged into **44** (its Node.js code example is now inside file 44, alongside the original bash example).
