Chat Server (Messenger/WhatsApp)

"WebSocket for real-time messaging → Redis Streams for message queuing → Cassandra for message persistence → Last seen tracking with heartbeat"

1. Functional Requirements

Feature 1: Users should be able to register/login with phone number or email
Feature 2: One-to-one messaging - send text, images, videos, files
Feature 3: Group messaging - create groups, add/remove members, group admin controls
Feature 4: Send and receive media messages (images, videos up to 100MB)
Feature 5: Message history - retrieve past messages with pagination
Feature 6: Delivery and read receipts - single tick (sent), double tick (delivered), blue tick (read)
Feature 7: Last seen status - show when user was last active
Feature 8: Online/offline status - real-time presence indicator
2. Non-Functional Requirements

Scale
Users — 1 Billion users globally, 100M daily active users
Messages — >100B messages/day (1M+ msg/sec), 100TB+ messages/day
Concurrent Connections — 10M-100M concurrent WebSocket connections
Performance
CAP Theorem — Availability >> Consistency (eventual consistency acceptable)
Message Latency — < 100ms delivery for messages, highly reliable with no message loss
Delivery Guarantee — At-least-once delivery (may have duplicates, handle with message_id deduplication)
3. Core Entities

Entity 1: User - Profile with user_id, phone/email, username, profile_pic, last_seen, status
Entity 2: Message/Chat - Message data with message_id, sender_id, receiver_id, content, type (text/image/video), timestamp
Entity 3: Group - Group chat with group_id, name, members[], admin_ids[], created_at
4. API Designing

User Operations
POST /v1/user/register — Register with phone/OTP or email/password
POST /v1/user/login — Login and receive JWT token
Messaging
WS /v1/messages/send — Send message via WebSocket {receiver_id, content, type}
GET /v1/messages/{userId} — Retrieve message history with pagination
WS /v1/user/{userId}/isOnline — Subscribe to user's online status via WebSocket
POST /v1/messages/{messageId}/read — Mark message as read, update read receipt
Group Operations
POST /v1/groups/create — Create group with members list
GET /v1/groups/{groupId}/messages — Lazy load group messages with pagination
5. High Level Design

Users/Clients → LB + API Gateway: Authentication, WebSocket upgrade, rate limiting
User Service → User DB (PostgreSQL): Stores user profiles, contacts, settings
Chat Service (WS) → WebSocket Gateway: Maintains persistent connections, routes messages
Group Service → Group DB (PostgreSQL): Manages group metadata, members
Media Upload Service → S3 (Blob): Stores images, videos, files with CDN delivery
Message Service → Chat DB (Cassandra): Persistent message storage with wide-column model
Redis Streams: Message queue for offline users, ensures delivery when they come online
Redis Cache: WebSocket registry (user_id → connection_id), online status, last seen
Notification Service → FCM/APNS: Push notifications for offline users
Elasticsearch: Message search service for searching chat history
6. Deep Dive Design (Low Level)

Step 1: User Registration & Login
User sends: POST /v1/user/register with {phone: '+1234567890'}
User Service validates: Phone number format, sends OTP via SMS (Twilio)
User submits: OTP for verification, service creates user record in PostgreSQL {user_id: UUID, phone, username, created_at}
Login flow: POST /v1/user/login with {phone, otp} → validates OTP → generates JWT token with {user_id, exp: 7 days}
Service returns: {user_id, token, profile_data}
Step 2: WebSocket Connection Establishment
Client initiates: WebSocket handshake to WS /v1/connect with Authorization: Bearer {JWT}
WebSocket Gateway validates: JWT token, extracts user_id
Gateway registers: Connection in Redis - HSET websocket_registry user_{user_id} {connection_id, server_instance, connected_at} with TTL=None (persistent until disconnect)
Gateway updates: User status - SET user:{user_id}:status 'online', publish to Redis Pub/Sub channel user:{user_id}:presence
Client subscribes: To personal message channel messages:{user_id} and presence updates
Heartbeat: Client sends ping every 30s, server responds pong, updates last_seen in Redis
Step 3: Sending One-to-One Message (Online Recipient)
User1 sends: Message via WebSocket {type: 'text', receiver_id: user2, content: 'Hello', client_message_id: UUID}
Chat Service validates: User1 authenticated, receiver exists, content not empty (<10KB text)
Service generates: Server message_id (UUID), timestamp
Service checks: Redis HGET websocket_registry user_{user2} → finds connection_id (user2 is online)
Service delivers: Message to user2's WebSocket connection immediately via WebSocket Gateway
Service persists: Message to Cassandra messages table {message_id, sender_id: user1, receiver_id: user2, content, type: 'text', timestamp, status: 'delivered'}
Service sends: Delivery receipt to user1 (double tick) via WebSocket
User2 sends: Read receipt when message displayed → POST /v1/messages/{message_id}/read → update status='read', send read receipt to user1 (blue tick)
Step 4: Sending Message (Offline Recipient)
User1 sends: Message to user2 who is offline
Service checks: Redis HGET websocket_registry user_{user2} → returns null (offline)
Service writes: Message to Redis Stream XADD stream:user:{user2}:messages * message_id {msg_id} sender_id {user1} content {text} timestamp {ts}
Service persists: To Cassandra (same as online case)
Service sends: Single tick to user1 (sent, not delivered yet)
Service triggers: Push notification via Notification Service → FCM/APNS 'New message from User1: Hello'
When user2 comes online: WebSocket connect → service pulls unread messages from Redis Stream XREAD stream:user:{user2}:messages → delivers via WebSocket → acknowledges and deletes from stream → updates status to 'delivered'
Step 5: Group Messaging
User sends: Message to group {group_id: 'group_123', content: 'Hello group'}
Group Service fetches: Group members from Group DB - SELECT members FROM groups WHERE group_id = 'group_123' → returns [user2, user3, user4, user5]
Service iterates: Through members list, for each member check online status
For online members: Deliver immediately via WebSocket to their respective connections
For offline members: Write to Redis Stream stream:user:{member_id}:messages
Service stores: Single message copy in Cassandra group_messages table {message_id, group_id, sender_id, content, timestamp}
Optimization: Don't create N copies for N members, store once with group_id, retrieve using (group_id, timestamp) index
Step 6: Media Upload (Image/Video)
Client requests: POST /v1/media/upload/url with {file_type: 'image/jpeg', file_size: 2MB}
Media Upload Service validates: File size <= 100MB, type in [image/*, video/*, application/pdf]
Service generates: Presigned S3 PUT URL valid for 15 min - s3://media-bucket/{user_id}/{message_id}/{filename}.jpg
Service returns: {upload_url, media_id}
Client uploads: File directly to S3 using presigned URL (parallel upload for large files)
Client sends: Message via WebSocket {type: 'image', receiver_id, media_id, thumbnail_url, metadata: {width, height, size}}
Chat Service: Stores message with media_url pointing to S3, receiver downloads from CDN url: https://cdn.example.com/media/{media_id}
Step 7: Message History Retrieval
Client requests: GET /v1/messages/{user_id}?limit=50&before={timestamp} (pagination)
Chat Service queries: Cassandra - SELECT * FROM messages WHERE (sender_id = {current_user} AND receiver_id = {user_id}) OR (sender_id = {user_id} AND receiver_id = {current_user}) AND timestamp < {before} ORDER BY timestamp DESC LIMIT 50
Cassandra model: Partition key = (user1_id, user2_id) sorted pair to ensure both users query same partition, clustering key = timestamp DESC
Service returns: {messages: [{message_id, sender_id, content, timestamp, status}], has_more: true, next_before: {oldest_timestamp}}
Client renders: Messages in reverse order (newest at bottom), lazy loads more on scroll to top
Step 8: Last Seen & Online Status
Heartbeat mechanism: Client sends ping via WebSocket every 30s
Chat Service updates: Redis - SET user:{user_id}:last_seen {current_timestamp} EX 60 (60s expiry)
Online status: If last_seen exists and age < 60s → user is 'online', else 'offline'
Last seen display: When user2 queries user1's status → GET user:{user1}:last_seen → if exists, calculate 'Last seen 5 min ago', if expired 'Last seen today at 10:30 AM'
Presence broadcasting: When user1 goes offline (WebSocket disconnect) → publish to Redis Pub/Sub channel user:{user1}:presence with {status: 'offline', last_seen: timestamp}
Subscribers: User1's contacts who are online receive presence update via their WebSocket connections → UI updates to show 'offline'
Step 9: Read Receipts & Delivery Status
Message states: sent (single tick) → delivered (double tick) → read (blue tick)
Sent: When message persisted to Cassandra, sender receives sent receipt
Delivered: When message delivered to recipient's WebSocket or added to Redis Stream, update message status='delivered' in Cassandra, send double tick to sender
Read: When recipient's app displays message (onVisible event), client sends POST /v1/messages/{message_id}/read → update status='read' → send blue tick to sender via WebSocket
Group read receipts: Track per-member read status {message_id → {user2: read, user3: delivered, user4: read}}, show 'Read by 2 of 3' in UI
Step 10: Message Search
User searches: GET /v1/messages/search?q='hello world'&chat_id={user_id}
Message Consumer: Async consumer reads from Cassandra, indexes messages in Elasticsearch
Elasticsearch index: messages-{date} with fields {message_id, sender_id, receiver_id, content (text analyzed), timestamp}
Search query: Uses Elasticsearch match query on content field, filters by chat_id (sender OR receiver), sorted by timestamp DESC
Service returns: Matching messages with highlights, client displays with 'Jump to message' action
Optimization: Only index last 6 months of messages, older messages require direct Cassandra scan (slower)
Step 11: WebSocket Reconnection & Message Sync
Client disconnects: Due to network failure, WebSocket connection drops
Client reconnects: Sends last_received_message_id or last_sync_timestamp in handshake
Service fetches: Missed messages from Redis Stream + Cassandra WHERE timestamp > last_sync_timestamp ORDER BY timestamp
Service delivers: Batch of missed messages in chronological order
Client deduplicates: Using message_id (server-generated UUID) to prevent showing duplicates if message was already received
Stream cleanup: After delivery acknowledged, delete messages from Redis Stream - XDEL stream:user:{user_id}:messages {message_id}
7. Client-Side Components

Component 1: Chat UI - Message list with infinite scroll, input box, typing indicators
Component 2: WebSocket Manager - Maintains connection, auto-reconnect with exponential backoff, handles ping/pong
Component 3: Message Queue - Local queue for outgoing messages when offline, syncs when online
Component 4: Media Handler - Uploads media to S3, shows progress, handles retry on failure
Component 5: Presence Tracker - Subscribes to contacts' online status, updates UI indicators
Component 6: Notification Handler - Receives push notifications via FCM/APNS, shows alerts
Component 7: Local Storage - SQLite DB for message cache, offline access, search
8. Database Schema Details

Users (PostgreSQL)
user_id — uuid PRIMARY KEY
phone — varchar(15) UNIQUE
email — varchar(255) UNIQUE
username — varchar(50)
profile_pic_url — varchar(500)
status_message — varchar(255) (custom status like 'Available')
created_at — timestamp
updated_at — timestamp
Messages (Cassandra - optimized for writes)
partition_key — (sender_id, receiver_id) or conversation_id (deterministic: min(user1, user2) + max(user1, user2))
clustering_key — timestamp DESC (sorts messages newest first within partition)
message_id — uuid (unique identifier)
sender_id — uuid
receiver_id — uuid (null for group messages)
content — text (message text, max 10KB)
type — text (text, image, video, file, audio)
media_url — text (S3 URL for media messages)
metadata — map<text, text> (file size, dimensions, duration)
status — text (sent, delivered, read)
timestamp — timestamp
TTL — Optional - auto-delete after N days (ephemeral messages)
Group_Messages (Cassandra)
partition_key — group_id
clustering_key — timestamp DESC
message_id — uuid
sender_id — uuid
content — text
type — text
media_url — text
read_by — set<uuid> (user_ids who read the message)
timestamp — timestamp
Groups (PostgreSQL)
group_id — uuid PRIMARY KEY
group_name — varchar(255)
group_pic_url — varchar(500)
created_by — uuid FK → Users
admin_ids — uuid[] (array of admin user_ids)
member_ids — uuid[] (array of member user_ids)
created_at — timestamp
updated_at — timestamp
Redis - WebSocket Registry & Presence
websocket_registry — HASH user_{user_id} → {connection_id, server_instance, connected_at}
user:{user_id}:status — STRING 'online' or 'offline'
user:{user_id}:last_seen — STRING timestamp with EX 60 (60s expiry, indicates online if present)
stream:user:{user_id}:messages — REDIS STREAM - offline message queue, XADD for push, XREAD for pull
Elasticsearch - Message Search
index — messages-{yyyy-MM-dd}
message_id — keyword
sender_id — keyword
receiver_id — keyword
group_id — keyword (if group message)
content — text (analyzed for full-text search)
type — keyword
timestamp — date
9. Message Delivery Guarantee

At-Least-Once Delivery Strategy
Trigger: User sends message, system ensures it's delivered at least once (may duplicate)
Acknowledgment chain: Client → WebSocket Gateway (ack1) → Cassandra write (ack2) → Recipient delivery/stream write (ack3)
Client retry: If no ack1 within 5s, client resends with same client_message_id
Server deduplication: Check if message_id exists in Cassandra before inserting, if exists return ack (idempotent)
Recipient deduplication: Client maintains set of received message_ids (last 1000), ignores duplicates
Redis Streams for Offline Messages
Purpose: Queue messages for offline users without losing them
Write: XADD stream:user:{user_id}:messages * message_id {id} sender {user1} content {text} timestamp {ts}
Read: On user connect, XREAD COUNT 100 STREAMS stream:user:{user_id}:messages 0 (get all unread from beginning)
Acknowledge: After successful delivery to WebSocket, XDEL stream:user:{user_id}:messages {message_id}
Expiry: Messages in stream expire after 7 days (older than 7 days retrieved from Cassandra on demand)
10. Scaling & Optimization

Technique 1: WebSocket Sharding - Distribute users across WebSocket Gateway instances using consistent hashing on user_id
Technique 2: Cassandra Partitioning - Partition messages by conversation_id (pair of user_ids), prevents hotspots, enables parallel queries
Technique 3: Redis Cluster - Shard websocket_registry and presence data across Redis cluster (16K slots), handle 10M+ connections
Technique 4: Message Batching - Batch multiple messages in single WebSocket frame (group sends), reduces network overhead by 80%
Technique 5: CDN for Media - Images/videos served via CloudFront, reduces origin load by 95%, faster delivery globally
Technique 6: Read Replicas - PostgreSQL read replicas for user profile queries, writes to primary only
Technique 7: Connection Pooling - WebSocket Gateway maintains 100K connections per instance, 100 instances = 10M concurrent users
Technique 8: Pub/Sub for Presence - Redis Pub/Sub channels for broadcasting online/offline status to subscribed contacts, scales to millions
Technique 9: Lazy Loading - Load last 50 messages on chat open, fetch older messages on scroll (infinite scroll pagination)
Technique 10: Compression - Compress WebSocket messages with zlib (3:1 ratio), saves bandwidth for mobile users
Technique 11: Local Cache - Client caches last 1000 messages in SQLite, instant load on app open, background sync
Technique 12: TTL for Old Messages - Cassandra TTL deletes messages >2 years old automatically, saves storage
11. Common Interview Questions

Q
How do you ensure messages are delivered even when the recipient is offline?
A
Multi-layer offline message handling:

(1) Detection - when sending message, check Redis websocket_registry for recipient's connection_id, if null recipient is offline,

(2) Redis Stream queueing - write message to Redis Stream XADD stream:user:{recipient_id}:messages with message data, stream persists until user comes online,

(3) Cassandra persistence - simultaneously write message to Cassandra for durability (Redis Stream is cache, Cassandra is source of truth),

(4) Push notification - trigger FCM/APNS notification 'New message from {sender}',

(5) On reconnect - when recipient connects WebSocket, service executes XREAD stream:user:{recipient_id}:messages 0 to fetch all queued messages, delivers via WebSocket, client acknowledges, service deletes from stream XDEL,

(6) Fallback - if messages in stream >7 days old (expired), retrieve from Cassandra. Example: User A sends to offline User B → message stored in Cassandra + Redis Stream + push sent → B comes online after 1 hour → B receives 15 queued messages → stream cleared → B now receives new messages in real-time.

Q
How do you implement read receipts and delivery status at scale?
A
Event-driven status tracking:

(1) Sent status - when message written to Cassandra, update status='sent', send single tick to sender via WebSocket,

(2) Delivered status - when message delivered to recipient (either via WebSocket if online, or written to Redis Stream if offline), update message status='delivered' in Cassandra, send double tick to sender via WebSocket event {message_id, status: 'delivered', delivered_at},

(3) Read status - when recipient's app displays message (onVisible/onScroll event), client sends POST /v1/messages/{message_id}/read → service updates status='read' → sends blue tick to sender,

(4) Group read receipts - for groups, maintain map in Cassandra read_status: {message_id → {user2: {status: 'read', read_at}, user3: {status: 'delivered'}}}, query to show 'Read by 5 of 10 members',

(5) Optimization - batch read receipts: instead of sending API call for each message, batch 10 message_ids in single request. Scaling: 1B messages/day × 3 status updates (sent, delivered, read) = 3B writes/day. Cassandra handles with partition by message_id, lightweight transactions for idempotency.

Q
What happens if a WebSocket connection drops in the middle of sending a message?
A
Client-side retry with idempotency:

(1) Client generates - client_message_id (UUID) before sending message,

(2) Send attempt - client sends via WebSocket {type: 'message', client_message_id, receiver_id, content},

(3) Acknowledgment wait - client waits for server ACK {client_message_id, server_message_id, status: 'sent'},

(4) Connection drops - if no ACK within 5s, client assumes failure,

(5) Reconnection - WebSocket reconnects with exponential backoff (1s, 2s, 4s, 8s),

(6) Retry logic - client resends message with same client_message_id,

(7) Server deduplication - server checks if message with client_message_id already exists in Cassandra (lightweight transaction or SELECT before INSERT), if exists returns existing server_message_id without re-inserting,

(8) Client reconciliation - client updates local DB mapping client_message_id → server_message_id. Edge case: message sent but ACK lost due to network → client retries → server detects duplicate → returns success → client updates UI with server_message_id. Result: at-least-once delivery, no lost messages, handled client-side deduplication using client_message_id + server_message_id mapping.

Q
How do you handle last seen and online status efficiently?
A
Heartbeat-based presence system:

(1) Online detection - when user connects WebSocket, set Redis key user:{user_id}:status='online', also set user:{user_id}:last_seen with current timestamp EX 60 (60s expiry),

(2) Heartbeat - client sends ping every 30s via WebSocket, server updates last_seen timestamp, resets TTL to 60s,

(3) Offline detection - if client misses 2 consecutive pings (60s), last_seen key expires in Redis, user status switches to 'offline',

(4) Last seen calculation - when querying user's status, GET user:{user_id}:last_seen, if key exists → 'online', if key missing → user offline, check PostgreSQL for last_seen_timestamp stored on disconnect, display 'Last seen 2 hours ago',

(5) Presence broadcasting - when user goes offline, publish to Redis Pub/Sub channel user:{user_id}:presence with {status: 'offline', last_seen: timestamp}, all subscribers (user's contacts) receive update via their WebSocket connections,

(6) Privacy - user can disable last seen in settings, service returns 'Last seen recently' instead of exact timestamp. Optimization: don't broadcast every heartbeat (every 30s), only broadcast status changes (online ↔ offline transitions). Scaling: 100M active users × 1 heartbeat/30s = 3.3M updates/sec, Redis handles with SET (O

(1)) and Pub/Sub (100K msg/sec per instance).

Q
How do you design the message schema in Cassandra for efficient queries?
A
Wide-column model optimized for conversations:

(1) Partition key - conversation_id (deterministic from pair of user_ids: sorted to ensure both users query same partition), e.g., conversation between user_A and user_B → conversation_id = sha256(min(user_A, user_B) + max(user_A, user_B)),

(2) Clustering key - timestamp DESC (sorts messages newest first within partition), allows efficient range queries for pagination,

(3) Query pattern - SELECT * FROM messages WHERE conversation_id = {id} AND timestamp < {before} ORDER BY timestamp DESC LIMIT 50, hits single partition, retrieves messages in O(log N + 50) time,

(4) Denormalization - store both sender_id and receiver_id in each row for bidirectional queries,

(5) Write optimization - Cassandra optimized for writes (append-only, no read-before-write), handles 100K writes/sec per node,

(6) TTL - set TTL for old messages, auto-delete after 2 years to save storage. Group messages: separate table group_messages with partition_key=group_id, clustering_key=timestamp DESC, allows querying all messages in group efficiently. Index strategy: no secondary indexes needed, primary key design handles all query patterns. Example: Conversation between Alice and Bob, 10K messages over 1 year → stored in single partition, latest 50 messages retrieved in <10ms, pagination efficient with timestamp cursor.

Q
How do you implement group messaging efficiently?
A
Fanout-on-write with optimization:

(1) Message ingestion - user sends message to group {group_id: 'group_123', content: 'Hello'},

(2) Member retrieval - query PostgreSQL SELECT member_ids FROM groups WHERE group_id = 'group_123' → returns [user2, user3, user4, user5] (4 members),

(3) Storage - write single message copy to Cassandra group_messages table with partition_key=group_id, clustering_key=timestamp DESC,

(4) Fanout - iterate through member_ids, for each member:

(a) check if online via Redis websocket_registry,

(b) if online, deliver via WebSocket immediately,

(c) if offline, write to Redis Stream stream:user:{member_id}:messages with pointer to group message_id,

(5) Read receipts - track per-member read status in read_by set<uuid> in Cassandra, update when member reads, display 'Read by 3 of 4' in UI. Optimization: don't create 4 copies of message for 4 members, store once indexed by group_id, members retrieve via SELECT * FROM group_messages WHERE group_id = 'group_123' ORDER BY timestamp DESC. Large groups (>100 members): paginate fanout delivery, use Kafka for async processing to avoid blocking sender, send to 100 members in parallel batches. Example: 1000-member group, single message → stored once in Cassandra (1 write) → fanout to 1000 members (1000 WebSocket sends or stream writes) → processed in <1s via parallel workers.

Q
What's your media upload and delivery strategy?
A
Direct S3 upload with presigned URLs:

(1) Client request - POST /v1/media/upload/url with {file_type: 'image/jpeg', file_size: 5MB},

(2) Validation - Media Service checks file_size <= 100MB, type in whitelist [image/*, video/*, application/pdf, audio/*],

(3) Presigned URL generation - generate S3 presigned PUT URL with key media/{user_id}/{message_id}/{uuid}.jpg, valid for 15 min,

(4) Client upload - client uploads file directly to S3 bypassing backend servers (reduces load), shows progress bar,

(5) Upload completion - S3 triggers Lambda on object creation, Lambda generates thumbnail (for images) and stores in media/{user_id}/{message_id}/thumb.jpg,

(6) Message send - client sends chat message {type: 'image', media_id, media_url, thumbnail_url, metadata: {width: 1920, height: 1080, size: 5MB}},

(7) Delivery - recipient receives message with thumbnail_url (small, loads fast), clicks to view full image fetched from CDN https://cdn.example.com/media/{media_id},

(8) CDN - CloudFront caches media at edge locations, 95% cache hit rate, reduces S3 reads and latency. Optimization: adaptive bitrate for videos (transcoding via MediaConvert), progressive JPEG for images. Security: presigned URLs with expiry prevent unauthorized access. Example: User sends 20MB video → generates presigned URL in 50ms → uploads to S3 in 30s → Lambda transcodes to 720p, 480p, 360p (takes 2 min) → recipient loads thumbnail instantly, streams video from CDN with adaptive quality.

Q
How do you implement typing indicators in real-time?
A
Ephemeral event broadcasting via WebSocket:

(1) Typing start - when user starts typing, client sends {type: 'typing_start', chat_id: {receiver_id}} via WebSocket,

(2) Throttling - client throttles typing events (send at most once per 3 seconds) to reduce traffic,

(3) Server broadcast - WebSocket Gateway checks if receiver online, if yes broadcasts to receiver's connection {type: 'typing', user_id: {sender_id}},

(4) Client display - receiver's UI shows '{Sender Name} is typing...' indicator,

(5) Typing stop - after 3s of no typing or when message sent, client sends {type: 'typing_stop'}, server broadcasts, receiver hides indicator,

(6) No persistence - typing events are NOT stored in database or Redis, completely ephemeral (reduces load). Group typing: similar flow but broadcast to all online group members except sender. Scaling: 100M concurrent users, 10% typing at any moment = 10M typing events, but throttled to 1 event per 3s = 3.3M events/sec, handled by WebSocket Gateway with direct forwarding (no DB writes). Alternative: use Redis Pub/Sub - publish to channel typing:{chat_id}, subscribers receive updates, but WebSocket direct routing is simpler and faster for 1-to-1 chats.

Q
How do you handle message ordering and prevent race conditions?
A
Server-assigned timestamps with Lamport clocks:

(1) Client-side timestamp - client includes local_timestamp when sending message (for optimistic UI update),

(2) Server timestamp - server assigns authoritative server_timestamp (millisecond precision) when message received, this is used for ordering,

(3) Cassandra clustering - messages stored with clustering_key=server_timestamp DESC, ensures consistent ordering,

(4) Race condition scenario - two messages sent simultaneously from different clients (A sends M1, B sends M2 to same chat),

(5) Server serialization - WebSocket Gateway processes messages sequentially per chat (maintains order using queue or single-threaded event loop per chat), assigns timestamps T1, T2 where T1 < T2 based on arrival order,

(6) Client reconciliation - clients may show messages in different order temporarily (optimistic UI), but when they fetch from Cassandra, all see same order (by server_timestamp),

(7) Logical clocks - for distributed servers, use Lamport timestamps or vector clocks to maintain causal ordering across servers. Edge case: Client A's clock is 5 minutes ahead, sends message with future timestamp → server ignores client timestamp, uses server_timestamp → prevents ordering issues. Example: User A sends M1 at 10:00:00.100 (client time), User B sends M2 at 10:00:00.050 (client time) → server receives M1 first (assigns T=1000), M2 second (assigns T=1001) → all clients display M1 before M2 regardless of client timestamps.

Q
What's your disaster recovery strategy for chat data?
A
Multi-region replication with backup:

(1) Cassandra replication - multi-datacenter replication with RF=3 (replication factor) in primary region (us-east-1), async replication to secondary region (us-west-2),

(2) Write consistency - use QUORUM for writes (2 of 3 replicas acknowledge), balances durability with latency,

(3) Read consistency - use ONE for reads (fastest response), eventual consistency acceptable for chat,

(4) Failure scenarios - if 1 node fails, other 2 replicas serve requests, writes still succeed with QUORUM,

(5) Region failover - if primary region down, DNS failover to secondary region (us-west-2) in <5 min (RTO), secondary has replica of all data (RPO=1 min, async replication lag),

(6) Redis persistence - use Redis AOF (Append-Only File) + RDB snapshots, if Redis crashes rebuild from snapshots + Cassandra (offline messages),

(7) S3 replication - enable cross-region replication for media bucket, media available in both regions,

(8) Backup strategy - daily snapshots of Cassandra to S3, retention 30 days, allows point-in-time recovery. Testing: monthly DR drills, simulate region failure, validate failover automation. Example: Primary region experiences outage → DNS switches to secondary in 3 min → users reconnect WebSockets to secondary region → message history loaded from replicated Cassandra → service continues with <5 min disruption.

12. Key Numbers to Remember

Scale & Volume
Total Users — 1 Billion globally, 100M daily active users (DAU)
Messages/Day — >100 Billion messages per day (1M+ msg/sec average)
Concurrent Connections — 10M-100M concurrent WebSocket connections
Data Volume — 100TB+ of messages per day (text + media)
Latency & Performance
Message Delivery — < 100ms end-to-end latency for online users
WebSocket Ping/Pong — 30s interval for heartbeat, 60s timeout
Typing Indicator — Throttled to 1 event per 3s
Message Acknowledgment — < 50ms for sent receipt, < 100ms for delivered
Storage & Caching
Redis TTL — Last seen: 60s, WebSocket registry: no expiry (until disconnect)
Redis Stream — Offline messages retained 7 days, then Cassandra fallback
Cassandra TTL — Messages auto-delete after 2 years (optional)
Message Cache — Client caches last 1000 messages in SQLite
CDN Cache — Media cached 30 days, 95% hit rate
Messaging Limits
Text Message — Max 10KB per message
Media Upload — Max 100MB per file (image/video/document)
Group Size — Max 256 members per group (WhatsApp limit)
Presigned URL — Valid for 15 minutes for S3 upload
Reliability Metrics
Uptime SLA — 99.99% availability (52 minutes/year downtime)
Message Delivery — At-least-once guarantee (may duplicate)
RTO (Recovery Time) — < 5 minutes for region failover
RPO (Recovery Point) — < 1 minute (async replication lag)
Cassandra Replication — RF=3, QUORUM writes (2 of 3 must acknowledge)
WebSocket Scaling
Connections/Server — 100K WebSocket connections per gateway instance
Total Gateway Servers — 100-1000 instances for 10M-100M connections
Message Rate — 10K messages/sec per gateway instance
Reconnect Backoff — Exponential: 1s, 2s, 4s, 8s, max 16s
Example Calculation - Message Flow
Step 1: WebSocket Send — 10ms (client to gateway, validate)
Step 2: Cassandra Write — 30ms (insert message, replication)
Step 3: Recipient Lookup — 5ms (Redis check if online)
Step 4: WebSocket Deliver — 10ms (gateway to recipient)
Total Latency — 55ms (well under 100ms target)
Cost Optimization
Direct S3 Upload — Saves server bandwidth, 100TB/day uploaded directly
CDN Cache Hit — 95% hit rate = 95% fewer S3 reads
Message Compression — 3:1 ratio with zlib, saves 66% bandwidth
TTL for Old Messages — Auto-delete after 2 years = 50% storage savings
Key Interview Tips

⚠️
NEVER use HTTP polling for real-time messaging. WebSocket is mandatory for persistent bidirectional communication. Polling every 1s for 10M users = 10M req/sec unnecessary load. WebSocket: single connection, server pushes updates.

⭐
Interviewers ALWAYS ask: 'How to handle offline messages?'. Answer: Redis Streams for queueing (fast, 7-day retention) + Cassandra for persistence (durable, long-term). On reconnect, pull from Stream first, fallback to Cassandra for older messages. Push notifications via FCM/APNS.

💡
Key optimization: Direct S3 upload with presigned URLs. Client uploads media directly to S3, bypassing backend. Saves bandwidth, reduces latency from 5s (via backend) to 2s (direct), handles 100MB files efficiently.

⭐
Must mention: Cassandra partition key design. Use conversation_id (pair of user_ids) as partition key, timestamp as clustering key. Ensures single partition for conversation, efficient queries, sorted by timestamp for pagination.

⚠️
NEVER store typing indicators in database. They're ephemeral events, broadcast via WebSocket/Pub/Sub only. Storing creates 1B+ unnecessary writes/day. Typing events should be fire-and-forget with throttling (1 per 3s).

💡
At-least-once delivery with client deduplication. Server may deliver message multiple times (retry logic). Client uses message_id to dedupe. Trade-off: simpler than exactly-once (no complex distributed transactions), acceptable for chat.

⭐
Interviewers love asking: 'How to implement read receipts at scale?'. Answer: Event-driven updates - when message displayed, client sends read event → update Cassandra status → broadcast to sender via WebSocket. Batch read receipts (10 messages) to reduce API calls.

⚠️
NEVER synchronously wait for all group members to receive message. Use fanout-on-write with async delivery. Sender gets immediate ACK after Cassandra write, member delivery happens async (parallel workers). Prevents timeout for large groups.

💡
Heartbeat-based presence with Redis TTL. Client pings every 30s → server updates last_seen with EX 60. If client dies, TTL expires in 60s → automatic offline status. No manual cleanup needed, Redis handles it.

⭐
Must explain: WebSocket sharding with consistent hashing. Distribute users across gateway instances using hash(user_id) % num_instances. Enables horizontal scaling from 100K to 100M connections. User always connects to same instance for session continuity.